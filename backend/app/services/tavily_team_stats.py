"""
Tavily-based team season stats (corners/shots/fouls per game) for WC2026.

Triggered per-team when that team's match transitions to FT (see
football_data_org.fetch_and_store_fixtures), not on a blanket schedule —
keeps Tavily/Groq usage to a handful of calls a day instead of refreshing
all 48 teams every hour regardless of whether anything changed.
"""
import time
import json
from typing import Optional, Dict
from app.config import get_settings
from app.database import get_connection
from app.services.llm import _groq_complete
from app.services.tavily_odds import _tavily_search

settings = get_settings()

STATS_TTL = 3600 * 4  # don't re-fetch the same team more than once per ~4h

# Realistic per-game bounds — anything outside these is more likely a
# misread season/tournament total than a genuine per-game average (e.g.
# Spain came back with "shots: 27", almost certainly a total across several
# games rather than one game's worth).
_BOUNDS = {
    "corners": (0, 15),
    "shots": (2, 24),
    "fouls": (3, 25),
}


async def fetch_team_stats(team_name: str) -> Optional[Dict]:
    if not settings.tavily_key:
        return None
    if _is_fresh(team_name):
        return None

    query = f"{team_name} World Cup 2026 corners shots fouls per game statistics"
    text = await _tavily_search(query, max_results=5)
    if not text:
        return None

    stats = _parse_team_stats(text, team_name)
    if not stats:
        return None

    _save_team_stats(team_name, stats)
    return stats


def _is_fresh(team_name: str) -> bool:
    """
    A row only counts as fresh (skip re-fetching) if it's both recent AND
    complete — a row with any null field is always eligible for retry
    regardless of TTL, so a partial result from a bad search doesn't get
    stuck for hours.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT corners, shots, fouls, updated_at FROM team_season_stats WHERE team_name = ? AND source = 'tavily'",
        (team_name,),
    )
    row = cur.fetchone()
    conn.close()
    if not row or not row["updated_at"]:
        return False
    if row["corners"] is None or row["shots"] is None or row["fouls"] is None:
        return False
    return row["updated_at"] > time.time() - STATS_TTL


def _parse_team_stats(search_text: str, team_name: str) -> Optional[Dict]:
    """Use Groq to extract corners/shots/fouls per game for one team from search text."""
    prompt = f"""From this web search text, extract {team_name}'s World Cup 2026 average
PER-GAME statistics: corners, shots, and fouls committed.

{search_text[:1500]}

Critical: these must be per-game AVERAGES, not season/tournament TOTALS. If the text
gives a total across multiple games (e.g. "27 shots in 4 games"), divide to compute the
per-game average yourself. If you cannot tell whether a number is a total or an average,
return null for that field rather than guessing — a missing value is better than a wrong one.

Return ONLY this JSON: {{"corners": <number or null>, "shots": <number or null>, "fouls": <number or null>}}
If none of these stats are found for {team_name}, return: {{"corners": null, "shots": null, "fouls": null}}"""

    content = _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=100)
    if not content:
        return None

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        parsed = json.loads(content[start:end])
        parsed = _apply_bounds(parsed)
        if parsed.get("corners") is None and parsed.get("shots") is None and parsed.get("fouls") is None:
            return None
        return parsed
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _apply_bounds(parsed: Dict) -> Dict:
    """Null out any field outside a realistic per-game range instead of trusting it."""
    for field, (lo, hi) in _BOUNDS.items():
        value = parsed.get(field)
        if value is not None:
            try:
                if not (lo <= float(value) <= hi):
                    parsed[field] = None
            except (TypeError, ValueError):
                parsed[field] = None
    return parsed


def _save_team_stats(team_name: str, stats: Dict) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO team_season_stats (team_name, corners, shots, fouls, source, updated_at)
        VALUES (?, ?, ?, ?, 'tavily', ?)
        ON CONFLICT(team_name) DO UPDATE SET
            corners = excluded.corners,
            shots = excluded.shots,
            fouls = excluded.fouls,
            source = excluded.source,
            updated_at = excluded.updated_at
    """, (team_name, stats.get("corners"), stats.get("shots"), stats.get("fouls"), time.time()))
    conn.commit()
    conn.close()
