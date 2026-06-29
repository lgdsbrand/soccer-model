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
