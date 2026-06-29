import httpx
import json
import time
import asyncio
from typing import Optional, List, Dict, Any
from app.config import get_settings
from app.database import get_connection

settings = get_settings()

BASE_URL = settings.api_football_base
HEADERS = {
    "x-apisports-key": settings.api_football_key,
    "x-rapidapi-host": "v3.football.api-sports.io",
}


async def _get(endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
    """Single API-Football GET with error handling."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("errors"):
                print(f"API-Football error: {data['errors']}")
                return None
            return data
        except Exception as e:
            print(f"API-Football request failed ({endpoint}): {e}")
            return None


def _cache_valid(fetched_at: float, ttl: int) -> bool:
    return (time.time() - fetched_at) < ttl


async def fetch_and_store_fixtures() -> int:
    """Fetch all WC2026 fixtures and store in DB. Returns count stored."""
    data = await _get("fixtures", {
        "league": settings.wc_league_id,
        "season": settings.wc_season
    })
    if not data:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    count = 0

    for f in data.get("response", []):
        fix = f["fixture"]
        teams = f["teams"]
        goals = f["goals"]
        league = f["league"]

        # Upsert teams first
        for side in ["home", "away"]:
            t = teams[side]
            cur.execute("""
                INSERT OR IGNORE INTO teams (id, name, code, logo)
                VALUES (?, ?, ?, ?)
            """, (t["id"], t["name"], t.get("code"), t.get("logo")))

        venue = fix.get("venue") or {}
        cur.execute("""
            INSERT OR REPLACE INTO fixtures
            (id, league_id, season, round, date_utc, status,
             home_team_id, away_team_id, home_score, away_score,
             venue_name, venue_city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fix["id"],
            settings.wc_league_id,
            settings.wc_season,
            league.get("round"),
            fix.get("timestamp"),
            fix["status"]["short"],
            teams["home"]["id"],
            teams["away"]["id"],
            goals.get("home"),
            goals.get("away"),
            venue.get("name"),
            venue.get("city"),
        ))
        count += 1

    conn.commit()
    conn.close()
    return count


async def fetch_standings() -> bool:
    """Fetch group standings and store."""
    data = await _get("standings", {
        "league": settings.wc_league_id,
        "season": settings.wc_season
    })
    if not data:
        return False

    conn = get_connection()
    cur = conn.cursor()

    for league_data in data.get("response", []):
        for group in league_data.get("league", {}).get("standings", []):
            for entry in group:
                team = entry["team"]
                all_stats = entry.get("all", {})
                goals = all_stats.get("goals", {})
                group_name = entry.get("group", "")
                letter = group_name[-1] if group_name else None

                cur.execute("""
                    INSERT OR REPLACE INTO teams (id, name, code, logo, group_letter)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        group_letter=excluded.group_letter
                """, (team["id"], team["name"], team.get("code"), team.get("logo"), letter))

                cur.execute("""
                    INSERT OR REPLACE INTO standings
                    (team_id, group_letter, rank, points, played, won, drawn, lost,
                     goals_for, goals_against, goal_diff, form, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    team["id"], letter, entry.get("rank"), entry.get("points"),
                    all_stats.get("played", 0),
                    all_stats.get("win", 0), all_stats.get("draw", 0), all_stats.get("lose", 0),
                    goals.get("for", 0), goals.get("against", 0),
                    entry.get("goalsDiff", 0),
                    entry.get("form"),
                    time.time()
                ))

    conn.commit()
    conn.close()
    return True


async def fetch_last5(team_id: int) -> List[Dict]:
    """Fetch last 5 fixtures for a team, cache in DB."""
    conn = get_connection()
    cur = conn.cursor()

    # Check cache — only re-fetch if >24h old
    cur.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo,
               at.name as away_name, at.logo as away_logo
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE (f.home_team_id = ? OR f.away_team_id = ?)
          AND f.status = 'FT'
        ORDER BY f.date_utc DESC
        LIMIT 5
    """, (team_id, team_id))
    cached = cur.fetchall()
    conn.close()

    if len(cached) >= 5:
        return [dict(r) for r in cached]

    # Fetch from API
    data = await _get("fixtures", {
        "team": team_id,
        "last": 10,
        "league": settings.wc_league_id,
        "season": settings.wc_season
    })
    if not data:
        return [dict(r) for r in cached]

    conn = get_connection()
    cur = conn.cursor()
    for f in data.get("response", []):
        fix = f["fixture"]
        teams = f["teams"]
        goals = f["goals"]
        league = f["league"]
        venue = fix.get("venue") or {}

        for side in ["home", "away"]:
            t = teams[side]
            cur.execute("INSERT OR IGNORE INTO teams (id, name, code, logo) VALUES (?, ?, ?, ?)",
                       (t["id"], t["name"], t.get("code"), t.get("logo")))

        cur.execute("""
            INSERT OR REPLACE INTO fixtures
            (id, league_id, season, round, date_utc, status,
             home_team_id, away_team_id, home_score, away_score, venue_name, venue_city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fix["id"], settings.wc_league_id, settings.wc_season,
            league.get("round"), fix.get("timestamp"), fix["status"]["short"],
            teams["home"]["id"], teams["away"]["id"],
            goals.get("home"), goals.get("away"),
            venue.get("name"), venue.get("city")
        ))

    conn.commit()

    cur.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo,
               at.name as away_name, at.logo as away_logo
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE (f.home_team_id = ? OR f.away_team_id = ?)
          AND f.status = 'FT'
        ORDER BY f.date_utc DESC
        LIMIT 5
    """, (team_id, team_id))
    results = [dict(r) for r in cur.fetchall()]
    conn.close()
    return results


_AF_NAME_MAP = {
    "usa": "united states",
    "ir iran": "iran",
    "korea republic": "south korea",
    "dr congo": "congo dr",
    "cape verde": "cape verde islands",
    "czech republic": "czechia",
    "bosnia & herzegovina": "bosnia-herzegovina",
    "côte d'ivoire": "ivory coast",
    "trinidad & tobago": "trinidad and tobago",
}


def _norm_team(name: str) -> str:
    n = name.lower().strip()
    return _AF_NAME_MAP.get(n, n)


async def fetch_match_stats(fixture_id: int) -> Optional[List[Dict]]:
    """Fetch match statistics using the api_football_id mapping to avoid ID mismatch."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM match_stats WHERE fixture_id = ?", (fixture_id,))
    cached = cur.fetchall()
    conn.close()

    if cached:
        return [dict(r) for r in cached]

    # Look up the API-Football fixture ID and team info
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.api_football_id, f.home_team_id, f.away_team_id,
               ht.name as home_name, at.name as away_name
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.id = ?
    """, (fixture_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row["api_football_id"]:
        return None

    af_id = row["api_football_id"]
    home_team_id = row["home_team_id"]
    away_team_id = row["away_team_id"]
    home_norm = _norm_team(row["home_name"])
    away_norm = _norm_team(row["away_name"])

    data = await _get("fixtures/statistics", {"fixture": af_id})
    if not data:
        return None

    response = data.get("response", [])
    if not response:
        return None

    conn = get_connection()
    cur = conn.cursor()

    for idx, team_stats in enumerate(response):
        af_name = _norm_team(team_stats["team"].get("name", ""))

        # Match by name; fall back to position (0=home, 1=away)
        if af_name == home_norm:
            db_team_id = home_team_id
        elif af_name == away_norm:
            db_team_id = away_team_id
        else:
            db_team_id = home_team_id if idx == 0 else away_team_id

        stats = {s["type"]: s["value"] for s in team_stats.get("statistics", [])}

        cur.execute("""
            INSERT OR REPLACE INTO match_stats
            (fixture_id, team_id, shots_total, shots_on_target, corners, fouls,
             yellow_cards, red_cards, possession, passes_total, passes_accuracy, offsides)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fixture_id, db_team_id,
            stats.get("Total Shots"), stats.get("Shots on Goal"),
            stats.get("Corner Kicks"), stats.get("Fouls"),
            stats.get("Yellow Cards"), stats.get("Red Cards"),
            stats.get("Ball Possession"),
            stats.get("Total passes"), stats.get("Passes %"),
            stats.get("Offsides")
        ))

    conn.commit()
    cur.execute("SELECT * FROM match_stats WHERE fixture_id = ?", (fixture_id,))
    result = [dict(r) for r in cur.fetchall()]
    conn.close()
    return result


async def fetch_lineups(fixture_id: int) -> Optional[List[Dict]]:
    """Fetch official lineups — only available ~1hr before kickoff."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT l.*, p.club, p.club_logo
        FROM lineups l
        LEFT JOIN players p ON l.player_id = p.id
        WHERE l.fixture_id = ? AND l.is_predicted = 0
    """, (fixture_id,))
    cached = cur.fetchall()
    conn.close()

    if cached:
        return [dict(r) for r in cached]

    data = await _get("fixtures/lineups", {"fixture": fixture_id})
    if not data or not data.get("response"):
        return None

    conn = get_connection()
    cur = conn.cursor()

    for team_lineup in data["response"]:
        team_id = team_lineup["team"]["id"]
        formation = team_lineup.get("formation")

        cur.execute("DELETE FROM lineups WHERE fixture_id = ? AND team_id = ? AND is_predicted = 1",
                   (fixture_id, team_id))

        for player_entry in team_lineup.get("startXI", []) + team_lineup.get("substitutes", []):
            p = player_entry["player"]
            is_sub = player_entry in team_lineup.get("substitutes", [])
            try:
                cur.execute("""
                    INSERT OR REPLACE INTO lineups
                    (fixture_id, team_id, formation, player_id, player_name,
                     player_number, player_pos, player_grid, is_substitute, is_predicted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (fixture_id, team_id, formation, p.get("id"), p.get("name"),
                      p.get("number"), p.get("pos"), p.get("grid"), int(is_sub)))
            except Exception:
                pass

    conn.commit()
    cur.execute("""
        SELECT l.*, p.club, p.club_logo
        FROM lineups l
        LEFT JOIN players p ON l.player_id = p.id
        WHERE l.fixture_id = ?
    """, (fixture_id,))
    result = [dict(r) for r in cur.fetchall()]
    conn.close()
    return result


async def fetch_squad(team_id: int) -> List[Dict]:
    """Fetch squad/players for a team."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE team_id = ?", (team_id,))
    cached = cur.fetchall()
    conn.close()

    if cached:
        return [dict(r) for r in cached]

    data = await _get("players/squads", {"team": team_id})
    if not data:
        return []

    conn = get_connection()
    cur = conn.cursor()
    players = []

    for squad in data.get("response", []):
        for p in squad.get("players", []):
            cur.execute("""
                INSERT OR REPLACE INTO players
                (id, name, age, nationality, team_id, position, number, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["name"], p.get("age"), p.get("nationality"),
                  team_id, p.get("position"), p.get("number"), p.get("photo")))
            players.append(dict(p))

    conn.commit()
    conn.close()
    return players


async def fetch_team_recent_for_model(team_name: str, team_id: int, n: int = 20) -> List[Dict]:
    """Fetch recent match results for the Poisson model fitting."""
    data = await _get("fixtures", {
        "team": team_id,
        "last": n,
        "season": settings.wc_season
    })
    if not data:
        return []

    results = []
    conn = get_connection()
    cur = conn.cursor()

    for f in data.get("response", []):
        fix = f["fixture"]
        teams = f["teams"]
        goals = f["goals"]

        if goals.get("home") is None or goals.get("away") is None:
            continue
        if fix["status"]["short"] != "FT":
            continue

        ts = fix.get("timestamp", 0)
        days_ago = (time.time() - ts) / 86400

        home_name = teams["home"]["name"]
        away_name = teams["away"]["name"]

        cur.execute("""
            INSERT OR IGNORE INTO historical_results
            (match_date, home_team, away_team, home_goals, away_goals, tournament, neutral, days_ago)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fix.get("date"), home_name, away_name,
            goals["home"], goals["away"],
            f["league"].get("name", ""), 0, days_ago
        ))

        results.append({
            "home_team": home_name,
            "away_team": away_name,
            "home_goals": goals["home"],
            "away_goals": goals["away"],
            "days_ago": days_ago,
        })

    conn.commit()
    conn.close()
    return results


async def get_api_status() -> Dict:
    """Check remaining API calls for today."""
    data = await _get("status", {})
    if not data:
        return {}
    return data.get("response", {})
