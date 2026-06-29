"""
Backfill api_football_id for WC2026 fixtures using a sliding date window.

API-Football free tier restricts bulk league/season queries for 2026, but allows
fetching fixtures by specific date within the last ~3 days. This script queries
the accessible date window and maps API-Football IDs to our DB fixture IDs.

Run daily (or from main.py scheduler) to pick up new fixture IDs as they become
accessible:
    python scripts/backfill_api_football_ids.py
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_connection
from app.services.api_football import _get

AF_TO_DB = {
    "usa": "united states",
    "ir iran": "iran",
    "korea republic": "south korea",
    "dr congo": "congo dr",
    "cape verde": "cape verde islands",
    "czech republic": "czechia",
    "bosnia & herzegovina": "bosnia-herzegovina",
    "bosnia-herzegovina": "bosnia-herzegovina",
    "cote d'ivoire": "ivory coast",
    "ivory coast": "ivory coast",
    "trinidad & tobago": "trinidad and tobago",
}


def normalize(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()
    return AF_TO_DB.get(n, n)


async def _fetch_wc_for_date(date_str: str):
    """Fetch all fixtures for a date, return only World Cup (league_id=1) ones."""
    data = await _get("fixtures", {"date": date_str})
    if not data:
        return []
    return [f for f in data.get("response", []) if f.get("league", {}).get("id") == 1]


async def sync_api_football_ids(days_back: int = 3, days_ahead: int = 1) -> int:
    """
    Query API-Football for WC fixtures in a window around today and store
    the api_football_id mapping. Returns count of IDs stored/updated.

    Free plan allows roughly: today minus 3 days to today plus 1 day.
    """
    today = datetime.now(timezone.utc).date()
    dates = [
        (today + timedelta(days=d)).isoformat()
        for d in range(-days_back, days_ahead + 1)
    ]

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.id, f.date_utc,
               COALESCE(ht.name, 'TBD') as home,
               COALESCE(at.name, 'TBD') as away
        FROM fixtures f
        LEFT JOIN teams ht ON f.home_team_id = ht.id
        LEFT JOIN teams at ON f.away_team_id = at.id
    """)
    db_fixtures = cur.fetchall()
    conn.close()

    db_index: dict = {}
    for row in db_fixtures:
        if not row["date_utc"]:
            continue
        dt = datetime.fromtimestamp(row["date_utc"], tz=timezone.utc)
        date_str = dt.strftime("%Y-%m-%d")
        key = (date_str, normalize(row["home"]), normalize(row["away"]))
        db_index[key] = row["id"]

    updated = 0
    unmatched = []

    for date_str in dates:
        af_fixtures = await _fetch_wc_for_date(date_str)
        if not af_fixtures:
            continue

        for f in af_fixtures:
            fix = f["fixture"]
            teams = f["teams"]
            af_id = fix["id"]
            ts = fix.get("timestamp")
            if not ts:
                continue

            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            match_date = dt.strftime("%Y-%m-%d")
            home_norm = normalize(teams["home"]["name"])
            away_norm = normalize(teams["away"]["name"])

            db_id = (
                db_index.get((match_date, home_norm, away_norm))
                or db_index.get((match_date, away_norm, home_norm))
            )

            if not db_id:
                for delta in (-1, 1):
                    alt = (
                        datetime.strptime(match_date, "%Y-%m-%d") + timedelta(days=delta)
                    ).strftime("%Y-%m-%d")
                    db_id = (
                        db_index.get((alt, home_norm, away_norm))
                        or db_index.get((alt, away_norm, home_norm))
                    )
                    if db_id:
                        break

            if not db_id:
                unmatched.append(
                    f"{match_date} {teams['home']['name']} vs {teams['away']['name']} (AF={af_id})"
                )
                continue

            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE fixtures SET api_football_id = ? WHERE id = ? AND (api_football_id IS NULL OR api_football_id != ?)",
                (af_id, db_id, af_id),
            )
            if cur.rowcount:
                updated += 1
            conn.commit()
            conn.close()

    if unmatched:
        print(f"  AF backfill unmatched ({len(unmatched)}): {unmatched}")

    return updated


async def main():
    today = datetime.now(timezone.utc).date()
    dates_start = today - timedelta(days=3)
    dates_end = today + timedelta(days=1)
    print(f"Syncing API-Football IDs for {dates_start} to {dates_end} ...")
    updated = await sync_api_football_ids()
    print(f"Done. Updated: {updated} fixture ID mappings.")


if __name__ == "__main__":
    asyncio.run(main())
