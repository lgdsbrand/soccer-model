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
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT updated_at FROM team_season_stats WHERE team_name = ? AND source = 'tavily'",
        (team_name,),
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row["updated_at"] and row["updated_at"] > time.time() - STATS_TTL)


def _parse_team_stats(search_text: str, team_name: str) -> Optional[Dict]:
    """Use Groq to extract corners/shots/fouls per game for one team from search text."""
    prompt = f"""From this web search text, extract {team_name}'s World Cup 2026 average
per-game statistics: corners, shots, and fouls committed.

{search_text[:1500]}

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
        if parsed.get("corners") is None and parsed.get("shots") is None and parsed.get("fouls") is None:
            return None
        return parsed
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


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
