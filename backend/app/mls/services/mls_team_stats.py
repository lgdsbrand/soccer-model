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

Also fetches `expected_goals_team`/`expected_goals_conceded_team` (confirmed
live, 30/30 teams) and derives an opponent-adjusted Attack/Defense Rating +
1-30 rank per team, per a methodology the client (Tyler) sent over — see
`_compute_ratings()` below for the adaptation notes (FotMob only exposes
*season-total* xG/xGA per team, not per-match, so the "opponent adjustment"
uses each team's real schedule from `mls_fixtures` against opponents'
season averages, rather than iterating true per-match xG).
"""
import time
from typing import Dict, Optional
from app.config import get_settings
from app.mls.database import get_connection

settings = get_settings()

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


def _load_current_season_opponents(season: int) -> Dict[str, list]:
    """{team_name: [opponent_name, ...]} across every finished match this
    season, one entry per meeting (so a conference rival played 3 times
    contributes 3 entries) — this is what makes the rating "schedule
    adjusted" rather than just "adjusted for the league average"."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ht.name as home_name, at.name as away_name
        FROM mls_fixtures f
        JOIN mls_teams ht ON f.home_team_id = ht.id
        JOIN mls_teams at ON f.away_team_id = at.id
        WHERE f.season = ? AND f.status = 'FT'
    """, (season,))
    rows = cur.fetchall()
    conn.close()

    opponents: Dict[str, list] = {}
    for r in rows:
        opponents.setdefault(r["home_name"], []).append(r["away_name"])
        opponents.setdefault(r["away_name"], []).append(r["home_name"])
    return opponents


def _compute_ratings(xg_per_game: Dict[str, float], xga_per_game: Dict[str, float], season: int) -> Dict[str, dict]:
    """
    Opponent-adjusted Attack/Defense Rating, adapted from the client's
    methodology:

        Attack Rating  = Team xG / Opponent Average xGA
        Defense Rating = Opponent xG / Opponent Average xG  (lower is better)

    intended to be computed per match then averaged. FotMob's team-stats API
    only exposes *season-total* xG/xGA per team, not a per-match breakdown,
    so there's no real "opponent xG in this specific match" to use. Instead
    we average over the team's *actual* schedule (from `mls_fixtures`,
    correctly weighting repeat conference matchups) using each opponent's own
    season-average xG/xGA — i.e. "how did this team's underlying output
    compare to what an average defense/attack allows/creates, given the mix
    of opponents they actually played this season."

    Attack Rating(T)  = T's xG/game  ÷ mean(opponent's xGA/game, over T's schedule)
    Defense Rating(T) = T's xGA/game ÷ mean(opponent's xG/game,  over T's schedule)

    1.00 = league-average given that schedule; for Attack, higher is better;
    for Defense, lower is better (allowed less than the opponents' attacks
    would typically produce). Ranked 1-30 each direction across every team
    with a computable rating.
    """
    opponents_by_team = _load_current_season_opponents(season)

    ratings: Dict[str, dict] = {}
    for team, opponents in opponents_by_team.items():
        if team not in xg_per_game or team not in xga_per_game:
            continue
        opp_xga = [xga_per_game[o] for o in opponents if o in xga_per_game]
        opp_xg = [xg_per_game[o] for o in opponents if o in xg_per_game]
        if not opp_xga or not opp_xg:
            continue
        avg_opp_xga = sum(opp_xga) / len(opp_xga)
        avg_opp_xg = sum(opp_xg) / len(opp_xg)
        if avg_opp_xga <= 0 or avg_opp_xg <= 0:
            continue
        ratings[team] = {
            "attack_rating": round(xg_per_game[team] / avg_opp_xga, 2),
            "defense_rating": round(xga_per_game[team] / avg_opp_xg, 2),
        }

    by_attack = sorted(ratings, key=lambda t: ratings[t]["attack_rating"], reverse=True)
    by_defense = sorted(ratings, key=lambda t: ratings[t]["defense_rating"])
    for i, team in enumerate(by_attack, start=1):
        ratings[team]["attack_rank"] = i
    for i, team in enumerate(by_defense, start=1):
        ratings[team]["defense_rank"] = i

    return ratings


async def refresh_all_team_stats() -> int:
    """
    Fetch corners/shots-on-target/fouls/xG/xGA per game for every MLS team,
    compute the opponent-adjusted Attack/Defense Rating + rank (see
    `_compute_ratings`), and upsert all of it into mls_team_season_stats.
    Five HTTP calls total (all against FotMob's public, unauthenticated
    deep-stats endpoint — no quota to worry about, unlike the Odds API).
    """
    corners_total = await _fetch_stat("corner_taken_team")
    shots_on_target = await _fetch_stat("ontarget_scoring_att_team")
    fouls = await _fetch_stat("fk_foul_lost_team")
    xg_total = await _fetch_stat("expected_goals_team")
    xga_total = await _fetch_stat("expected_goals_conceded_team")

    played = _load_games_played()
    all_teams = set(corners_total) | set(shots_on_target) | set(fouls) | set(xg_total) | set(xga_total)
    if not all_teams:
        return 0

    def per_game(totals: Dict[str, float], team_name: str) -> Optional[float]:
        games = played.get(team_name)
        if team_name not in totals or not games:
            return None
        return round(totals[team_name] / games, 2)

    xg_per_game = {t: v for t in all_teams if (v := per_game(xg_total, t)) is not None}
    xga_per_game = {t: v for t in all_teams if (v := per_game(xga_total, t)) is not None}
    ratings = _compute_ratings(xg_per_game, xga_per_game, settings.mls_season)

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
        rating = ratings.get(team_name, {})

        cur.execute("""
            INSERT INTO mls_team_season_stats
                (team_name, corners, shots, fouls, xg, xga, attack_rating, defense_rating, attack_rank, defense_rank, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'fotmob', ?)
            ON CONFLICT(team_name) DO UPDATE SET
                corners = excluded.corners,
                shots = excluded.shots,
                fouls = excluded.fouls,
                xg = excluded.xg,
                xga = excluded.xga,
                attack_rating = excluded.attack_rating,
                defense_rating = excluded.defense_rating,
                attack_rank = excluded.attack_rank,
                defense_rank = excluded.defense_rank,
                source = excluded.source,
                updated_at = excluded.updated_at
        """, (
            team_name,
            corners_pg,
            shots_on_target.get(team_name),
            fouls.get(team_name),
            xg_per_game.get(team_name),
            xga_per_game.get(team_name),
            rating.get("attack_rating"),
            rating.get("defense_rating"),
            rating.get("attack_rank"),
            rating.get("defense_rank"),
            now,
        ))

    conn.commit()
    conn.close()

    if unmatched:
        print(f"MLS team stats: {len(unmatched)} team name(s) not found in mls_standings — extend FOTMOB_NAME_TO_MLS_NAME: {unmatched}")

    return len(all_teams)
