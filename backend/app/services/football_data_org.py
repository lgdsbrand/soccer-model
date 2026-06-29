"""
football-data.org client — free tier, no daily call limit (10 req/min).
Used as primary source for WC2026 live fixtures and standings.
API-Football free tier only covers 2022-2024; football-data.org covers the
current WC.

Docs: https://docs.football-data.org/general/v4/index.html
Competition code for FIFA World Cup: WC
"""
import httpx
import time
import asyncio
from typing import Optional, List, Dict, Any
from app.config import get_settings
from app.database import get_connection

settings = get_settings()

BASE_URL = "https://api.football-data.org/v4"
WC_CODE = "WC"


def _headers() -> Dict[str, str]:
    return {"X-Auth-Token": settings.football_data_key}


async def _get(path: str, params: Optional[Dict] = None) -> Optional[Dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}{path}",
                headers=_headers(),
                params=params or {},
            )
            if resp.status_code == 429:
                # Rate limited (10 req/min free tier) — back off and retry once
                await asyncio.sleep(6)
                resp = await client.get(
                    f"{BASE_URL}{path}",
                    headers=_headers(),
                    params=params or {},
                )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"football-data.org error ({path}): {e}")
            return None


def _map_status(fd_status: str) -> str:
    """Map football-data.org status to our internal format."""
    return {
        "SCHEDULED": "NS",
        "TIMED": "NS",
        "IN_PLAY": "1H",
        "PAUSED": "HT",
        "FINISHED": "FT",
        "AWARDED": "FT",
        "POSTPONED": "PST",
        "CANCELLED": "CANC",
        "SUSPENDED": "SUSP",
    }.get(fd_status, "NS")


def _parse_round(stage: str, group: Optional[str], matchday: Optional[int]) -> str:
    stage_map = {
        "GROUP_STAGE": f"Group Stage - Matchday {matchday or '?'}",
        "LAST_32": "Round of 32",
        "LAST_16": "Round of 16",
        "QUARTER_FINALS": "Quarter-finals",
        "SEMI_FINALS": "Semi-finals",
        "THIRD_PLACE": "3rd Place",
        "FINAL": "Final",
    }
    return stage_map.get(stage, stage.replace("_", " ").title())


async def fetch_and_store_fixtures() -> int:
    """Fetch all WC2026 fixtures from football-data.org and store in DB."""
    if not settings.football_data_key:
        print("FOOTBALL_DATA_KEY not set — skipping football-data.org fixture fetch")
        return 0

    data = await _get(f"/competitions/{WC_CODE}/matches")
    if not data:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    count = 0

    for m in data.get("matches", []):
        home = m["homeTeam"]
        away = m["awayTeam"]
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        ht = score.get("halfTime", {})

        # Upsert teams
        for team in [home, away]:
            cur.execute("""
                INSERT OR IGNORE INTO teams (id, name, code, logo)
                VALUES (?, ?, ?, ?)
            """, (
                team["id"],
                team.get("name") or team.get("shortName") or "TBD",
                team.get("tla"),
                team.get("crest"),
            ))

        # Parse date
        utc_str = m.get("utcDate", "")
        try:
            from datetime import datetime, timezone
            ts = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).timestamp()
        except Exception:
            ts = None

        round_str = _parse_round(
            m.get("stage", "GROUP_STAGE"),
            m.get("group"),
            m.get("matchday"),
        )

        cur.execute("""
            INSERT OR REPLACE INTO fixtures
            (id, league_id, season, round, date_utc, status,
             home_team_id, away_team_id, home_score, away_score,
             home_score_ht, away_score_ht, venue_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["id"],
            1,  # WC league_id
            2026,
            round_str,
            ts,
            _map_status(m.get("status", "SCHEDULED")),
            home["id"],
            away["id"],
            ft.get("home"),
            ft.get("away"),
            ht.get("home"),
            ht.get("away"),
            m.get("venue"),
        ))
        count += 1

    conn.commit()
    conn.close()
    return count


async def fetch_standings() -> bool:
    """Fetch group standings and store."""
    if not settings.football_data_key:
        return False

    data = await _get(f"/competitions/{WC_CODE}/standings")
    if not data:
        return False

    conn = get_connection()
    cur = conn.cursor()

    for standing_group in data.get("standings", []):
        if standing_group.get("type") != "TOTAL":
            continue

        raw_group = standing_group.get("group", "")
        # "GROUP_A" → "A"
        letter = raw_group.replace("GROUP_", "")[-1] if raw_group else None

        for entry in standing_group.get("table", []):
            team = entry["team"]

            cur.execute("""
                INSERT OR IGNORE INTO teams (id, name, code, logo)
                VALUES (?, ?, ?, ?)
            """, (team["id"], team.get("name", ""), team.get("tla"), team.get("crest")))

            cur.execute("""
                UPDATE teams SET group_letter = ? WHERE id = ?
            """, (letter, team["id"]))

            cur.execute("""
                INSERT OR REPLACE INTO standings
                (team_id, group_letter, rank, points, played, won, drawn, lost,
                 goals_for, goals_against, goal_diff, form, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                team["id"],
                letter,
                entry.get("position"),
                entry.get("points", 0),
                entry.get("playedGames", 0),
                entry.get("won", 0),
                entry.get("draw", 0),
                entry.get("lost", 0),
                entry.get("goalsFor", 0),
                entry.get("goalsAgainst", 0),
                entry.get("goalDifference", 0),
                entry.get("form", ""),
                time.time(),
            ))

    conn.commit()
    conn.close()
    return True


async def fetch_teams() -> int:
    """Fetch all WC2026 teams with squad info."""
    if not settings.football_data_key:
        return 0

    data = await _get(f"/competitions/{WC_CODE}/teams")
    if not data:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    count = 0

    for team in data.get("teams", []):
        # INSERT OR IGNORE to avoid wiping group_letter set by fetch_standings()
        cur.execute("""
            INSERT OR IGNORE INTO teams (id, name, code, logo)
            VALUES (?, ?, ?, ?)
        """, (team["id"], team.get("name", ""), team.get("tla"), team.get("crest")))
        # Update non-group fields without touching group_letter
        cur.execute("""
            UPDATE teams SET name = ?, code = ?, logo = ? WHERE id = ?
        """, (team.get("name", ""), team.get("tla"), team.get("crest"), team["id"]))

        # Seed squad players
        for player in team.get("squad", []):
            from datetime import datetime as _dt
            dob = player.get("dateOfBirth")
            age = None
            if dob:
                try:
                    age = (_dt.now() - _dt.strptime(dob[:10], "%Y-%m-%d")).days // 365
                except Exception:
                    pass
            cur.execute("""
                INSERT INTO players (id, name, team_id, position, nationality, age, number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name       = excluded.name,
                    team_id    = excluded.team_id,
                    position   = excluded.position,
                    nationality= excluded.nationality,
                    age        = excluded.age,
                    number     = excluded.number
            """, (
                player.get("id"),
                player.get("name", ""),
                team["id"],
                player.get("position"),
                player.get("nationality"),
                age,
                player.get("shirtNumber"),
            ))

        count += 1

    conn.commit()
    conn.close()
    return count


async def fetch_last5_fd(team_id: int) -> List[Dict]:
    """Fetch last 5 completed WC matches for a team from football-data.org."""
    if not settings.football_data_key:
        return []

    data = await _get(f"/teams/{team_id}/matches", params={
        "competitions": WC_CODE,
        "status": "FINISHED",
        "limit": 5,
    })
    if not data:
        return []

    conn = get_connection()
    cur = conn.cursor()

    for m in data.get("matches", []):
        home = m["homeTeam"]
        away = m["awayTeam"]
        ft = m.get("score", {}).get("fullTime", {})

        for team in [home, away]:
            cur.execute("INSERT OR IGNORE INTO teams (id, name, code, logo) VALUES (?, ?, ?, ?)",
                       (team["id"], team.get("name", ""), team.get("tla"), team.get("crest")))

        try:
            from datetime import datetime
            ts = datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).timestamp()
        except Exception:
            ts = None

        cur.execute("""
            INSERT OR REPLACE INTO fixtures
            (id, league_id, season, round, date_utc, status,
             home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["id"], 1, 2026,
            _parse_round(m.get("stage", ""), m.get("group"), m.get("matchday")),
            ts, _map_status(m.get("status", "FINISHED")),
            home["id"], away["id"],
            ft.get("home"), ft.get("away"),
        ))

    conn.commit()
    conn.close()

    cur2 = conn.cursor() if False else get_connection().cursor()
    conn2 = get_connection()
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo,
               at.name as away_name, at.logo as away_logo
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE (f.home_team_id = ? OR f.away_team_id = ?)
          AND f.status = 'FT'
        ORDER BY f.date_utc DESC LIMIT 5
    """, (team_id, team_id))
    rows = [dict(r) for r in cur2.fetchall()]
    conn2.close()
    return rows
