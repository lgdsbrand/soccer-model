"""
MLS team season stats (corners/shots on target/fouls per game), sourced from
FotMob's public deep-stats API — same source and endpoint shape as
app/services/fotmob_team_stats.py, just pointed at MLS's league/season IDs
instead of the World Cup's.

LEAGUE_ID/SEASON_ID confirmed live (2026-07-19) via a real FotMob page load:
the MLS team-statistics page's `leagues?id=130` response embeds each stat
category's `fetchAllUrl` as
"https://data.fotmob.com/stats/130/season/29580/corner_taken_team.json" —
130 = MLS, 29580 = the 2026 MLS season. Re-verified against the same
query-param endpoint the WC integration already uses (leagueseasondeepstats),
which still works for these IDs too.
"""
import time
from typing import Dict
from app.mls.database import get_connection

FOTMOB_BASE = "https://www.fotmob.com/api/data/leagueseasondeepstats"
LEAGUE_ID = 130
SEASON_ID = "29580"
# The ?teamId= param doesn't filter results (every call still returns all
# teams) — it's just "which team's page this is," so any valid id works.
_ANY_TEAM_ID = 6603

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# FotMob vs ESPN (mls_teams.name) naming mismatches — same pattern as
# app/services/fotmob_team_stats.py's FOTMOB_NAME_TO_DB_NAME. Confirmed
# live against a real refresh_all_team_stats() run (2026-07-19) — all 7
# mismatches the run logged, resolved by comparing against mls_teams.name.
FOTMOB_NAME_TO_MLS_NAME: Dict[str, str] = {
    "DC United": "D.C. United",
    "Los Angeles FC": "LAFC",
    "Minnesota United": "Minnesota United FC",
    "Orlando City": "Orlando City SC",
    "Atlanta United": "Atlanta United FC",
    "CF Montreal": "CF Montréal",
    "St. Louis City": "St. Louis CITY SC",
    # FotMob still uses the old sponsor-led name; mls_teams.name was corrected
    # to "New York Red Bulls" via ESPN_TEAM_NAME_OVERRIDES in mls_source.py.
    "Red Bull New York": "New York Red Bulls",
}


async def _fetch_stat(stat_key: str) -> Dict[str, float]:
    """{team_name: value} for one FotMob deep-stat category, across all MLS teams."""
    import httpx
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
            mls_name = FOTMOB_NAME_TO_MLS_NAME.get(name, name)
            result[mls_name] = value
    return result


def _load_games_played() -> Dict[str, int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.name, s.played
        FROM mls_standings s
        JOIN mls_teams t ON s.team_id = t.id
    """)
    result = {row["name"]: row["played"] for row in cur.fetchall()}
    conn.close()
    return result


async def refresh_all_team_stats() -> int:
    """
    Fetch corners/shots-on-target/fouls per game for every MLS team and
    upsert into mls_team_season_stats. Three HTTP calls total.
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
    unmatched = []

    for team_name in all_teams:
        games = played.get(team_name)
        if games is None:
            unmatched.append(team_name)
        corners_pg = (
            round(corners_total[team_name] / games, 1)
            if team_name in corners_total and games
            else None
        )

        cur.execute("""
            INSERT INTO mls_team_season_stats (team_name, corners, shots, fouls, source, updated_at)
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

    if unmatched:
        print(f"MLS team stats: {len(unmatched)} team name(s) not found in mls_standings — extend FOTMOB_NAME_TO_MLS_NAME: {unmatched}")

    return len(all_teams)
