"""
Backfill prior MLS seasons into mls_fixtures/mls_teams, using the same ESPN
scoreboard endpoint already used for the current season (see
app/mls/services/mls_source.py) — just called with an older `season` value.

Needed for the head-to-head feature: mls_fixtures only had the current
(2026) season stored, which gives most team pairs just 1-2 meetings all
year (some pairs zero). Pulling a few prior seasons gives head-to-head
queries enough real matches to be meaningful.

Safe to re-run: ESPN event IDs are globally unique across years, so each
season's fixtures insert/update independently — this can't clobber the
current season's data.

Usage:
    python scripts/backfill_mls_history.py                # backfills the 3 seasons before the current one
    python scripts/backfill_mls_history.py 2023 2024 2025  # backfills specific seasons
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.mls.services.mls_source import fetch_and_store_teams_and_fixtures

settings = get_settings()


async def backfill_seasons(seasons: list[int]) -> dict[int, int]:
    """Fetch+store each season in turn. Returns {season: fixtures_stored}."""
    results: dict[int, int] = {}
    for season in seasons:
        print(f"Fetching MLS {season} season from ESPN...")
        count = await fetch_and_store_teams_and_fixtures(season=season)
        results[season] = count
        if count == 0:
            print(f"  {season}: 0 fixtures returned — ESPN may not serve this season "
                  f"via this endpoint, or the date range had no MLS matches.")
        else:
            print(f"  {season}: {count} fixtures stored.")
        # Small gap between requests — courtesy to ESPN's public (unauthenticated,
        # rate-limit-unknown) endpoint, not a documented requirement.
        await asyncio.sleep(1)
    return results


async def main():
    if len(sys.argv) > 1:
        seasons = [int(s) for s in sys.argv[1:]]
    else:
        current = settings.mls_season
        seasons = [current - 3, current - 2, current - 1]

    print(f"Backfilling MLS seasons: {seasons}")
    results = await backfill_seasons(seasons)

    total = sum(results.values())
    empty = [s for s, c in results.items() if c == 0]
    print(f"\nDone. Total fixtures stored/updated: {total}")
    if empty:
        print(f"Seasons with no data: {empty} — check these manually if head-to-head "
              f"still looks thin for pairs that should have met in those years.")


if __name__ == "__main__":
    asyncio.run(main())
