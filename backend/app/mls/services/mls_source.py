"""
ESPN public soccer API client — MLS teams/fixtures/standings.

No API key required. Used in place of API-Football (the account tied to
API_FOOTBALL_KEY was found suspended when this was built — see PROJECT_LOG)
and in place of football-data.org (MLS isn't in that provider's free-tier
competition list). Same async-fetch + upsert pattern as
app/services/football_data_org.py, pointed at ESPN's undocumented but
widely-used site.api.espn.com endpoints instead.
"""
import httpx
import time
from datetime import datetime
from typing import Optional, Dict, Any
from app.config import get_settings
from app.mls.database import get_connection

settings = get_settings()

# ESPN naming quirks — corrected at ingest so every downstream consumer (UI,
# LLM prompts, FotMob/Odds API name matching) sees the real club name instead
# of propagating the fix everywhere it's read. Keyed by ESPN team id (stable)
# rather than the stale name (which is exactly what's wrong).
ESPN_TEAM_NAME_OVERRIDES: Dict[int, Dict[str, str]] = {
    # ESPN still labels this club (and its short_name/abbreviation) after its
    # old sponsor-led name; the club rebranded to "New York Red Bulls" years
    # ago. Confirmed 2026-07-20.
    190: {"name": "New York Red Bulls", "short_name": "NY Red Bulls"},
}


def _team_display_fields(team_id: int, name: str, short_name: Optional[str]) -> tuple:
    override = ESPN_TEAM_NAME_OVERRIDES.get(team_id)
    if override:
        return override.get("name", name), override.get("short_name", short_name)
    return name, short_name


async def _get(base: str, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{base}{path}", params=params or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"ESPN MLS source error ({path}): {e}")
            return None


def _map_status(espn_type: Dict[str, Any]) -> str:
    """Map ESPN's status.type.name to the same status vocabulary fixtures.status uses."""
    name = (espn_type or {}).get("name", "")
    return {
        "STATUS_SCHEDULED": "NS",
        "STATUS_IN_PROGRESS": "1H",
        "STATUS_FIRST_HALF": "1H",
        "STATUS_HALFTIME": "HT",
        "STATUS_SECOND_HALF": "2H",
        "STATUS_FULL_TIME": "FT",
        "STATUS_FINAL": "FT",
        "STATUS_POSTPONED": "PST",
        "STATUS_CANCELED": "CANC",
        "STATUS_SUSPENDED": "SUSP",
    }.get(name, "NS")


def _parse_date(date_str: str) -> Optional[float]:
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


async def fetch_and_store_teams_and_fixtures() -> int:
    """
    Fetch the full MLS scoreboard (ESPN returns whatever window it considers
    "current" by default — this call widens it across the season with an
    explicit dates range) and upsert into mls_teams/mls_fixtures.
    """
    season = settings.mls_season
    data = await _get(
        settings.espn_soccer_base,
        f"/{settings.mls_espn_league_slug}/scoreboard",
        params={"dates": f"{season}0101-{season}1231", "limit": 1000},
    )
    if not data:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    count = 0

    for event in data.get("events", []):
        comps = event.get("competitions", [])
        if not comps:
            continue
        comp = comps[0]
        competitors = comp.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue

        for side in (home, away):
            team = side["team"]
            team_id = int(team["id"])
            name, short_name = _team_display_fields(
                team_id,
                team.get("displayName") or team.get("name") or "TBD",
                team.get("shortDisplayName"),
            )
            cur.execute("""
                INSERT INTO mls_teams (id, name, short_name, abbreviation, logo)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    short_name=excluded.short_name,
                    abbreviation=excluded.abbreviation,
                    logo=excluded.logo
            """, (
                team_id,
                name,
                short_name,
                team.get("abbreviation"),
                team.get("logo"),
            ))

        venue = comp.get("venue", {})
        status_obj = comp.get("status", {})
        # ESPN fills score with a "0" placeholder even for matches that
        # haven't kicked off yet — only trust it once the match has actually
        # started, otherwise store NULL (matches the WC fixtures convention).
        started = (status_obj.get("type", {}) or {}).get("state") != "pre"

        cur.execute("""
            INSERT INTO mls_fixtures
            (id, season, date_utc, status, home_team_id, away_team_id,
             home_score, away_score, venue_name, venue_city)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                season=excluded.season,
                date_utc=excluded.date_utc,
                status=excluded.status,
                home_team_id=excluded.home_team_id,
                away_team_id=excluded.away_team_id,
                home_score=excluded.home_score,
                away_score=excluded.away_score,
                venue_name=excluded.venue_name,
                venue_city=excluded.venue_city
        """, (
            int(event["id"]),
            season,
            _parse_date(event.get("date", "")),
            _map_status(status_obj.get("type", {})),
            int(home["team"]["id"]),
            int(away["team"]["id"]),
            int(home["score"]) if started and home.get("score") not in (None, "") else None,
            int(away["score"]) if started and away.get("score") not in (None, "") else None,
            venue.get("fullName"),
            (venue.get("address") or {}).get("city"),
        ))
        count += 1

    conn.commit()
    conn.close()
    return count


async def fetch_standings() -> bool:
    """Fetch MLS standings (Eastern + Western Conference) and store."""
    data = await _get(settings.espn_soccer_v2_base, f"/{settings.mls_espn_league_slug}/standings")
    if not data:
        return False

    conn = get_connection()
    cur = conn.cursor()

    for conference in data.get("children", []):
        conf_name = conference.get("name", "").replace(" Conference", "")
        entries = (conference.get("standings") or {}).get("entries", [])

        for entry in entries:
            team = entry["team"]
            stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
            team_id = int(team["id"])
            name, short_name = _team_display_fields(
                team_id,
                team.get("displayName") or team.get("name") or "TBD",
                team.get("shortDisplayName"),
            )

            cur.execute("""
                INSERT INTO mls_teams (id, name, short_name, abbreviation, logo, conference)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    short_name=excluded.short_name,
                    abbreviation=excluded.abbreviation,
                    logo=excluded.logo,
                    conference=excluded.conference
            """, (
                team_id,
                name,
                short_name,
                team.get("abbreviation"),
                (team.get("logos") or [{}])[0].get("href"),
                conf_name,
            ))

            cur.execute("""
                INSERT INTO mls_standings
                (team_id, conference, rank, points, played, won, drawn, lost,
                 goals_for, goals_against, goal_diff, form, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_id) DO UPDATE SET
                    conference=excluded.conference,
                    rank=excluded.rank,
                    points=excluded.points,
                    played=excluded.played,
                    won=excluded.won,
                    drawn=excluded.drawn,
                    lost=excluded.lost,
                    goals_for=excluded.goals_for,
                    goals_against=excluded.goals_against,
                    goal_diff=excluded.goal_diff,
                    updated_at=excluded.updated_at
            """, (
                int(team["id"]),
                conf_name,
                int(stats.get("rank", 0)),
                int(stats.get("points", 0)),
                int(stats.get("gamesPlayed", 0)),
                int(stats.get("wins", 0)),
                int(stats.get("ties", 0)),
                int(stats.get("losses", 0)),
                int(stats.get("pointsFor", 0)),
                int(stats.get("pointsAgainst", 0)),
                int(stats.get("pointDifferential", 0)),
                None,  # ESPN standings don't expose a recent-form string
                time.time(),
            ))

    conn.commit()
    conn.close()
    return True
