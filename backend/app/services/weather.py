import httpx
import json
import time
from typing import Optional, Dict
from app.config import get_settings
from app.database import get_connection

settings = get_settings()

# WC2026 venue coordinates — keyed by city name from API-Football
VENUE_COORDS: Dict[str, tuple] = {
    "East Rutherford": (40.8135, -74.0745),
    "Arlington": (32.7479, -97.0931),
    "Inglewood": (33.9534, -118.3386),
    "Santa Clara": (37.4032, -121.9697),
    "Kansas City": (39.0489, -94.4839),
    "Miami Gardens": (25.9580, -80.2389),
    "Miami": (25.9580, -80.2389),
    "Atlanta": (33.7554, -84.4013),
    "Seattle": (47.5952, -122.3316),
    "Houston": (29.6847, -95.4107),
    "Philadelphia": (39.9008, -75.1675),
    "Foxborough": (42.0909, -71.2643),
    "Boston": (42.3601, -71.0589),
    "Vancouver": (49.2767, -123.1116),
    "Toronto": (43.6333, -79.4189),
    "Edmonton": (53.5644, -113.4998),
    "Mexico City": (19.3029, -99.1505),
    "Monterrey": (25.6866, -100.3161),
    "Guadalajara": (20.6597, -103.3496),
}

# MLS venue coordinates — keyed by the exact "City, State"/"City" string ESPN
# returns in venue.address.city, so these hit the dict.get() exact match
# above rather than relying on the WC dict's substring fallback (which is
# fine for overlapping names like "Seattle" but wrong for e.g. the two
# different "Kansas City, {Kansas,Missouri}" venues).
MLS_VENUE_COORDS: Dict[str, tuple] = {
    "Atlanta, Georgia": (33.7554, -84.4013),
    "Austin, Texas": (30.2672, -97.7431),
    "Baltimore, Maryland": (39.2904, -76.6122),
    "Bridgeview, Illinois": (41.7486, -87.8017),
    "Carson, California": (33.8358, -118.2620),
    "Charlotte, North Carolina": (35.2271, -80.8431),
    "Chester, Pennsylvania": (39.8496, -75.3557),
    "Chicago, Illinois": (41.8781, -87.6298),
    "Cincinnati, Ohio": (39.1031, -84.5120),
    "Cleveland, Ohio": (41.4993, -81.6944),
    "Columbus, Ohio": (39.9612, -82.9988),
    "Commerce City, Colorado": (39.8083, -104.9342),
    "Denver, Colorado": (39.7392, -104.9903),
    "Fort Lauderdale, Florida": (26.1224, -80.1373),
    "Foxborough, Massachusetts": (42.0909, -71.2643),
    "Harrison, New Jersey": (40.7398, -74.1552),
    "Houston, Texas": (29.6847, -95.4107),
    "Kansas City, Kansas": (39.1155, -94.8233),
    "Kansas City, Missouri": (39.0489, -94.4839),
    "Los Angeles, California": (34.0522, -118.2437),
    "Miami, Florida": (25.7617, -80.1918),
    "Montreal": (45.5017, -73.5673),
    "Nashville, Tennessee": (36.1627, -86.7816),
    "New York City": (40.8296, -73.9262),
    "New York, New York": (40.7498, -73.8458),
    "Orlando, Florida": (28.5421, -81.3790),
    "Pasadena, California": (34.1478, -118.1445),
    "Portland, Oregon": (45.5152, -122.6784),
    "Saint Paul, Minnesota": (44.9537, -93.0900),
    "San Diego, California": (32.7157, -117.1611),
    "San Jose, California": (37.3382, -121.8863),
    "Sandy, Utah": (40.5649, -111.8389),
    "Santa Clara, California": (37.4032, -121.9697),
    "Seattle, Washington": (47.5952, -122.3316),
    "St. Louis, Missouri": (38.6270, -90.1994),
    "Stanford, California": (37.4275, -122.1697),
    "Toronto": (43.6333, -79.4189),
    # ESPN's venue.address.city for FC Dallas's stadium comes back as the
    # venue name itself ("Toyota Stadium"), not an actual city — the venue
    # is in Frisco, TX; coords below are Frisco's, not a literal city match.
    "Toyota Stadium": (33.1538, -96.8464),
    "Vancouver": (49.2767, -123.1116),
    "Washington, District of Columbia": (38.9072, -77.0369),
}
VENUE_COORDS.update(MLS_VENUE_COORDS)

# OpenWeatherMap icon code -> emoji, grouped by the "day/night" suffix
# families OWM uses (d/n): https://openweathermap.org/weather-conditions
_ICON_EMOJI: Dict[str, str] = {
    "01d": "☀️", "01n": "🌙",
    "02d": "⛅", "02n": "☁️",
    "03d": "☁️", "03n": "☁️",
    "04d": "☁️", "04n": "☁️",
    "09d": "🌧️", "09n": "🌧️",
    "10d": "🌦️", "10n": "🌧️",
    "11d": "⛈️", "11n": "⛈️",
    "13d": "❄️", "13n": "❄️",
    "50d": "🌫️", "50n": "🌫️",
}


def get_weather_emoji(icon: Optional[str]) -> str:
    return _ICON_EMOJI.get(icon or "", "🌡️")


async def get_weather(venue_city: str, lat: Optional[float] = None, lon: Optional[float] = None) -> Optional[Dict]:
    """Get weather for a venue city with caching."""
    if not settings.openweathermap_key:
        return None

    cache_key = venue_city.lower().replace(" ", "_")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT data, fetched_at FROM weather_cache WHERE venue_key = ?", (cache_key,))
    row = cur.fetchone()
    conn.close()

    if row and (time.time() - row["fetched_at"]) < settings.cache_weather_ttl:
        return json.loads(row["data"])

    # Resolve coordinates
    if lat is None or lon is None:
        coords = VENUE_COORDS.get(venue_city)
        if coords:
            lat, lon = coords
        else:
            # Try partial match
            for city_key, coords in VENUE_COORDS.items():
                if city_key.lower() in venue_city.lower():
                    lat, lon = coords
                    break

    if lat is None or lon is None:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat, "lon": lon,
                    "appid": settings.openweathermap_key,
                    "units": "metric"
                }
            )
            resp.raise_for_status()
            raw = resp.json()

        weather = {
            "venue_city": venue_city,
            "temperature_c": raw["main"]["temp"],
            "feels_like_c": raw["main"]["feels_like"],
            "description": raw["weather"][0]["description"].title(),
            "humidity": raw["main"]["humidity"],
            "wind_speed_ms": raw["wind"]["speed"],
            "icon": raw["weather"][0]["icon"],
            "emoji": get_weather_emoji(raw["weather"][0]["icon"]),
            "lat": lat,
            "lon": lon,
        }

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO weather_cache (venue_key, data, fetched_at)
            VALUES (?, ?, ?)
        """, (cache_key, json.dumps(weather), time.time()))
        conn.commit()
        conn.close()

        return weather

    except Exception as e:
        print(f"Weather fetch failed for {venue_city}: {e}")
        return None
