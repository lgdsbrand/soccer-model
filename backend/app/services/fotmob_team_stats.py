"""
Team season stats (corners/shots on target/fouls per game) for WC2026,
sourced from FotMob's public deep-stats API.

Unlike FIFA's own stats page (blocked by bot detection in headless/automated
contexts — see the abandoned backend/scripts/scrape_team_stats.py) and unlike
a Tavily+Groq search-and-extract approach (unreliable, sparse coverage),
FotMob's API is a plain, unauthenticated JSON endpoint that returns every
team in one call — no browser automation, no LLM guessing, no per-team
rate limiting to worry about.

Three calls total cover all 48 teams:
  - corner_taken_team:        season TOTAL corners (divided by games played below)
  - ontarget_scoring_att_team: shots on target PER GAME already
  - fk_foul_lost_team:         fouls committed PER GAME already

FotMob doesn't expose a plain "total shots" per-game category for this
competition — only shots ON TARGET. We use that as-is rather than
substituting a different, mismatched number.
"""
import time
import httpx
from typing import Dict
from app.database import get_connection

FOTMOB_BASE = "https://www.fotmob.com/api/data/leagueseasondeepstats"
LEAGUE_ID = 77
SEASON_ID = "24254"
# The ?teamId= param doesn't filter results (every call still returns all
# teams) — it's just "which team's page this is," so any valid id works.
_ANY_TEAM_ID = 8256

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# FotMob spells a handful of teams differently than football-data.org (our
# DB's naming convention).
FOTMOB_NAME_TO_DB_NAME = {
    "Turkiye": "Turkey",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cape Verde": "Cape Verde Islands",
    "DR Congo": "Congo DR",
    "USA": "United States",
    "Curacao": "Curaçao",
}


async def _fetch_stat(stat_key: str) -> Dict[str, float]:
    """{team_name: value} for one FotMob deep-stat category, across all teams."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            FOTMOB_BASE,
            params={
                "id": LEAGUE_ID, "season": SEASON_ID, "type": "teams",
                "stat": stat_key, "teamId": _ANY_TEAM_ID,
            },
            headers=_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()

    result = {}
    for row in data.get("statsData", []):
        name = row.get("name")
        value = row.get("statValue", {}).get("value")
        if name and value is not None:
            db_name = FOTMOB_NAME_TO_DB_NAME.get(name, name)
            result[db_name] = value
    return result


def _load_games_played() -> Dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.name, s.played
        FROM standings s
        JOIN teams t ON s.team_id = t.id
    """)
    result = {row["name"]: row["played"] for row in cur.fetchall()}
    conn.close()
    return result


async def refresh_all_team_stats() -> int:
    """
    Fetch corners/shots-on-target/fouls per game for every WC2026 team and
    upsert into team_season_stats. Three HTTP calls total, regardless of how
    many teams — cheap enough to just refresh everyone each time rather than
    computing which specific teams changed.
    """
    corners_total = await _fetch_stat("corner_taken_team")
    shots_on_target = await _fetch_stat("ontarget_scoring_att_team")
    fouls = await _fetch_stat("fk_foul_lost_team")

    played = _load_games_played()
    all_teams = set(corners_total) | set(shots_on_target) | set(fouls)
    if not all_teams:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    now = time.time()

    for team_name in all_teams:
        games = played.get(team_name)
        corners_pg = (
            round(corners_total[team_name] / games, 1)
            if team_name in corners_total and games
            else None
        )

        cur.execute("""
            INSERT INTO team_season_stats (team_name, corners, shots, fouls, source, updated_at)
            VALUES (?, ?, ?, ?, 'fotmob', ?)
            ON CONFLICT(team_name) DO UPDATE SET
                corners = excluded.corners,
                shots = excluded.shots,
                fouls = excluded.fouls,
                source = excluded.source,
                updated_at = excluded.updated_at
        """, (
            team_name,
            corners_pg,
            shots_on_target.get(team_name),
            fouls.get(team_name),
            now,
        ))

    conn.commit()
    conn.close()
    return len(all_teams)
