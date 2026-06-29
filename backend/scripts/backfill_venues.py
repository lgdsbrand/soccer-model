"""
Backfill venue_city + venue_name for all WC2026 fixtures using
openfootball/worldcup.json, which carries a "ground" field per match.

Run from backend/:
    python scripts/backfill_venues.py
"""
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from app.database import get_connection

URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# openfootball "ground" string → VENUE_COORDS key used by weather.py
GROUND_TO_CITY = {
    "Atlanta": "Atlanta",
    "Boston (Foxborough)": "Foxborough",
    "Dallas (Arlington)": "Arlington",
    "Guadalajara (Zapopan)": "Guadalajara",
    "Houston": "Houston",
    "Kansas City": "Kansas City",
    "Los Angeles (Inglewood)": "Inglewood",
    "Mexico City": "Mexico City",
    "Miami (Miami Gardens)": "Miami Gardens",
    "Monterrey (Guadalupe)": "Monterrey",
    "New York/New Jersey (East Rutherford)": "East Rutherford",
    "Philadelphia": "Philadelphia",
    "San Francisco Bay Area (Santa Clara)": "Santa Clara",
    "Seattle": "Seattle",
    "Toronto": "Toronto",
    "Vancouver": "Vancouver",
    "Edmonton": "Edmonton",
}

# openfootball team name → our DB team name
TEAM_MAP = {
    "Bosnia & Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "Czech Republic": "Czechia",
    "DR Congo": "Congo DR",
    "USA": "United States",
}


def normalize(name: str) -> str:
    return TEAM_MAP.get(name, name).lower().strip()


def _parse_utc_ts(date_str: str, time_str: str) -> float | None:
    """Parse openfootball date + time ('HH:MM UTC±X') to a UTC Unix timestamp."""
    import re
    m = re.match(r"(\d{1,2}):(\d{2})\s+UTC([+-]\d+)", time_str or "")
    if not m:
        return None
    h, mn, offset = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        base = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (base + timedelta(hours=h, minutes=mn) - timedelta(hours=offset)).timestamp()


def _match_by_time(match: dict, db_fixtures) -> int | None:
    """Match a TBD-team fixture by UTC kickoff timestamp (±30 min tolerance)."""
    ts = _parse_utc_ts(match.get("date", ""), match.get("time", ""))
    if ts is None:
        return None
    for row in db_fixtures:
        if row["date_utc"] and abs(row["date_utc"] - ts) <= 1800:
            return row["id"]
    return None


async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(URL)
        resp.raise_for_status()
        data = resp.json()

    matches = data.get("matches", [])

    print(f"Fetched {len(matches)} matches from openfootball")

    conn = get_connection()
    cur = conn.cursor()

    # Build a lookup: (date_str, home_norm, away_norm) → fixture_id
    cur.execute("""
        SELECT f.id, f.date_utc,
               COALESCE(ht.name, 'TBD') as home,
               COALESCE(at.name, 'TBD') as away
        FROM fixtures f
        LEFT JOIN teams ht ON f.home_team_id = ht.id
        LEFT JOIN teams at ON f.away_team_id = at.id
    """)
    db_fixtures = cur.fetchall()

    # Index DB fixtures by date string + team names (try both home/away orderings)
    db_index: dict = {}
    for row in db_fixtures:
        if not row["date_utc"]:
            continue
        dt = datetime.fromtimestamp(row["date_utc"], tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        key = (date_str, row["home"].lower().strip(), row["away"].lower().strip())
        db_index[key] = row["id"]

    updated = 0
    unmatched = []

    for m in matches:
        ground = m.get("ground", "")
        if not ground:
            continue

        city = GROUND_TO_CITY.get(ground)
        if not city:
            print(f"  WARNING: unknown ground '{ground}' — skipping")
            continue

        date_str = m.get("date", "")
        t1 = normalize(m.get("team1", ""))
        t2 = normalize(m.get("team2", ""))

        # Try exact date match, then ±1 day for UTC offset differences
        fixture_id = None
        for delta in (0, -1, 1):
            try:
                d = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=delta)).strftime("%Y-%m-%d")
            except ValueError:
                continue
            fixture_id = db_index.get((d, t1, t2)) or db_index.get((d, t2, t1))
            if fixture_id:
                break

        # For TBD-team knockout matches, fall back to matching by UTC kickoff time
        if not fixture_id and (t1.startswith("w") or t1.startswith("l")):
            fixture_id = _match_by_time(m, db_fixtures)

        if not fixture_id:
            unmatched.append(f"{date_str} {m.get('team1')} vs {m.get('team2')}")
            continue

        cur.execute(
            "UPDATE fixtures SET venue_city = ?, venue_name = ? WHERE id = ?",
            (city, ground, fixture_id),
        )
        updated += 1

    conn.commit()
    conn.close()

    print(f"\nUpdated {updated} fixtures with venue data.")
    if unmatched:
        print(f"Unmatched ({len(unmatched)}):")
        for u in unmatched:
            print(f"  {u}")


if __name__ == "__main__":
    asyncio.run(main())
