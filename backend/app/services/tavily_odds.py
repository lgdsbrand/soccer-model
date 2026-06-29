"""
Tavily-based odds service.
Fetches real betting market probabilities for matches and tournament advancement.
Replaces broken Dixon-Coles model outputs with live market data.
"""
import json
import time
from typing import Optional, Dict, Tuple
from app.config import get_settings
from app.database import get_connection
from app.services.llm import _groq_complete

settings = get_settings()

MATCH_TTL = 3600 * 6        # 6 hours — refresh match odds a few times per day
TOURNAMENT_TTL = 3600 * 20  # 20 hours — refresh tournament odds ~daily


# ---------------------------------------------------------------------------
# Match odds
# ---------------------------------------------------------------------------

async def fetch_match_odds(home_team: str, away_team: str) -> Optional[Dict]:
    """
    Fetch betting odds for a specific match via Tavily.
    Stores in tavily_match_probs and updates predictions table.
    Returns probability dict or None.
    """
    cached = _load_match_odds(home_team, away_team)
    if cached:
        return cached

    if not settings.tavily_key:
        return None

    query = f"{home_team} vs {away_team} World Cup 2026 odds win probability betting"
    search_text = await _tavily_search(query)
    if not search_text:
        return None

    probs = _parse_match_probs(search_text, home_team, away_team)
    if not probs:
        return None

    _save_match_odds(home_team, away_team, probs)
    _update_fixture_prediction(home_team, away_team, probs)
    return probs


def _load_match_odds(home_team: str, away_team: str) -> Optional[Dict]:
    """Load cached Tavily match odds, handling both team orderings."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cutoff = time.time() - MATCH_TTL

        cur.execute(
            "SELECT * FROM tavily_match_probs WHERE home_team = ? AND away_team = ? AND fetched_at > ?",
            (home_team, away_team, cutoff),
        )
        row = cur.fetchone()
        if row:
            conn.close()
            return _row_to_pred(dict(row), flipped=False)

        # Try reversed order — flip home/away percentages
        cur.execute(
            "SELECT * FROM tavily_match_probs WHERE home_team = ? AND away_team = ? AND fetched_at > ?",
            (away_team, home_team, cutoff),
        )
        row = cur.fetchone()
        conn.close()
        if row:
            return _row_to_pred(dict(row), flipped=True)

        return None
    except Exception:
        return None


def _row_to_pred(row: Dict, flipped: bool) -> Dict:
    """Convert a tavily_match_probs row into the predict_match() return format."""
    if flipped:
        h_win = row["away_win_pct"]
        a_win = row["home_win_pct"]
        lam_h = row.get("expected_away_goals") or 1.1
        lam_a = row.get("expected_home_goals") or 1.3
    else:
        h_win = row["home_win_pct"]
        a_win = row["away_win_pct"]
        lam_h = row.get("expected_home_goals") or 1.3
        lam_a = row.get("expected_away_goals") or 1.1

    return {
        "home_win_pct": h_win,
        "draw_pct": row["draw_pct"],
        "away_win_pct": a_win,
        "btts_pct": 45.0,
        "over_1_5_pct": 70.0,
        "over_2_5_pct": 50.0,
        "expected_home_goals": lam_h,
        "expected_away_goals": lam_a,
        "home_attack": 0.0,
        "home_defense": 0.0,
        "away_attack": 0.0,
        "away_defense": 0.0,
    }


def _save_match_odds(home_team: str, away_team: str, probs: Dict) -> None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO tavily_match_probs
            (home_team, away_team, home_win_pct, draw_pct, away_win_pct,
             expected_home_goals, expected_away_goals, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                home_team, away_team,
                probs["home_win_pct"], probs["draw_pct"], probs["away_win_pct"],
                probs.get("expected_home_goals", 1.3),
                probs.get("expected_away_goals", 1.1),
                time.time(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"tavily_odds: save_match_odds error: {e}")


def _update_fixture_prediction(home_team: str, away_team: str, probs: Dict) -> None:
    """Overwrite the predictions table row for this fixture with Tavily-derived values."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT f.id FROM fixtures f
            JOIN teams ht ON f.home_team_id = ht.id
            JOIN teams at ON f.away_team_id = at.id
            WHERE ht.name = ? AND at.name = ?
            """,
            (home_team, away_team),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            return

        cur.execute(
            """
            INSERT OR REPLACE INTO predictions
            (fixture_id, home_win_pct, draw_pct, away_win_pct, btts_pct,
             over_1_5_pct, over_2_5_pct, expected_home_goals, expected_away_goals,
             home_attack, home_defense, away_attack, away_defense, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, ?)
            """,
            (
                row["id"],
                probs["home_win_pct"], probs["draw_pct"], probs["away_win_pct"],
                45.0, 70.0, 50.0,
                probs.get("expected_home_goals", 1.3),
                probs.get("expected_away_goals", 1.1),
                time.time(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"tavily_odds: update_fixture_prediction error: {e}")


def _parse_match_probs(search_text: str, home_team: str, away_team: str, timeout_secs: int = 10) -> Optional[Dict]:
    """Use Groq to extract win/draw/loss probabilities from Tavily search text."""
    prompt = f"""From this betting odds text, extract win probabilities for {home_team} vs {away_team}.

{search_text[:800]}

Convert to implied probabilities:
- Decimal odds 2.50 → 1/2.50 × 100 = 40%
- Fractional 3/1 → 1/4 × 100 = 25%
- American +300 → 100/400 × 100 = 25%; -150 → 150/250 × 100 = 60%

Return ONLY this JSON: {{"home_win_pct": <0-100>, "draw_pct": <0-100>, "away_win_pct": <0-100>}}
If you cannot reliably extract values, return: {{"home_win_pct": null, "draw_pct": null, "away_win_pct": null}}"""

    content = _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=80)
    if not content:
        return None

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start < 0 or end <= start:
            return None
        parsed = json.loads(content[start:end])

        h = parsed.get("home_win_pct")
        d = parsed.get("draw_pct")
        a = parsed.get("away_win_pct")
        if h is None or d is None or a is None:
            return None

        total = float(h) + float(d) + float(a)
        if total < 80 or total > 140:  # allow bookmaker overround up to 40%
            return None

        # Remove overround → normalize to 100
        h_n = round(float(h) / total * 100, 1)
        d_n = round(float(d) / total * 100, 1)
        a_n = round(100 - h_n - d_n, 1)

        lam_h, lam_a = _goals_from_probs(h_n, a_n)
        return {
            "home_win_pct": h_n,
            "draw_pct": d_n,
            "away_win_pct": a_n,
            "expected_home_goals": lam_h,
            "expected_away_goals": lam_a,
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _goals_from_probs(home_win_pct: float, away_win_pct: float) -> Tuple[float, float]:
    """Approximate expected goals from win probabilities (WC avg ~2.5 goals/game)."""
    total = home_win_pct + away_win_pct + 1e-10
    lam_h = round(2.5 * (home_win_pct / total) * 1.05, 2)
    lam_a = round(2.5 * (away_win_pct / total) * 0.95, 2)
    return max(0.4, min(3.0, lam_h)), max(0.3, min(2.5, lam_a))


# ---------------------------------------------------------------------------
# Tournament advancement odds
# ---------------------------------------------------------------------------

async def fetch_tournament_odds() -> int:
    """
    Fetch WC2026 tournament advancement odds via Tavily.
    Updates advancement_probs with Tavily-sourced winner/final/sf percentages.
    Returns number of teams updated.
    """
    if not settings.tavily_key:
        return 0

    team_data: Dict[str, Dict] = {}

    searches = [
        ("World Cup 2026 winner odds outright betting",                "winner"),
        ("FIFA World Cup 2026 to reach the Final odds betting market", "final"),
        ("FIFA World Cup 2026 semifinal qualification odds betting",   "sf"),
    ]

    for query, stage in searches:
        text = await _tavily_search(query)
        if not text:
            continue
        probs = _parse_tournament_probs(text, stage)
        field = {"winner": "tavily_winner_pct", "final": "tavily_final_pct", "sf": "tavily_sf_pct"}[stage]
        for team_name, pct in probs.items():
            team_data.setdefault(team_name, {})[field] = pct

    return _save_tournament_odds(team_data)


def _parse_tournament_probs(search_text: str, stage: str) -> Dict[str, float]:
    """Use Groq to extract team → probability from tournament odds search text."""
    stage_label = {
        "winner": "win the tournament",
        "final": "reach the Final",
        "sf": "reach the Semifinals",
    }[stage]

    prompt = f"""From this betting text, list all teams and their implied probability to {stage_label} at the 2026 FIFA World Cup.

{search_text[:1000]}

Convert all formats to fair implied probabilities (remove bookmaker margin).
Decimal odds 5.00 → 20%. Fractional 4/1 → 20%. American +400 → 20%.

Return ONLY a JSON array: [{{"team": "Brazil", "pct": 14.5}}, {{"team": "France", "pct": 11.2}}, ...]
Include only teams with a clear probability. Return [] if none found."""

    content = _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=600)
    if not content:
        return {}

    try:
        start = content.find("[")
        end = content.rfind("]") + 1
        if start < 0 or end <= start:
            return {}
        items = json.loads(content[start:end])
        result = {}
        for item in items:
            team = str(item.get("team", "")).strip()
            pct = item.get("pct")
            if team and pct is not None and 0 < float(pct) <= 100:
                result[team] = round(float(pct), 1)
        return result
    except (json.JSONDecodeError, ValueError, TypeError):
        return {}


def _save_tournament_odds(team_data: Dict[str, Dict]) -> int:
    if not team_data:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM teams WHERE group_letter IS NOT NULL")
    db_teams = {row["name"].lower(): row["id"] for row in cur.fetchall()}
    conn.close()

    count = 0
    conn = get_connection()
    cur = conn.cursor()
    now = time.time()

    for tavily_name, updates in team_data.items():
        team_id = _match_team_name(tavily_name, db_teams)
        if not team_id:
            continue

        set_parts, values = [], []
        for field in ("tavily_winner_pct", "tavily_final_pct", "tavily_sf_pct"):
            if field in updates:
                set_parts.append(f"{field} = ?")
                values.append(updates[field])

        if not set_parts:
            continue

        values += [now, team_id]
        try:
            cur.execute(
                f"UPDATE advancement_probs SET {', '.join(set_parts)}, computed_at = ? WHERE team_id = ?",
                values,
            )
            if cur.rowcount > 0:
                count += 1
        except Exception as e:
            print(f"tavily_odds: save_tournament_odds error for {tavily_name}: {e}")

    conn.commit()
    conn.close()
    return count


# ---------------------------------------------------------------------------
# Team name matching
# ---------------------------------------------------------------------------

_ALIASES: Dict[str, str] = {
    "usa": "united states",
    "us": "united states",
    "ivory coast": "côte d'ivoire",
    "cote d'ivoire": "côte d'ivoire",
    "south korea": "korea republic",
    "korea": "korea republic",
    "iran": "ir iran",
    "cape verde islands": "cape verde",
    "türkiye": "turkey",
    "czechia": "czech republic",
    "drc": "dr congo",
    "democratic republic of congo": "dr congo",
}


def _match_team_name(tavily_name: str, db_teams: Dict[str, int]) -> Optional[int]:
    name = tavily_name.lower().strip()

    if name in db_teams:
        return db_teams[name]

    alias = _ALIASES.get(name)
    if alias and alias in db_teams:
        return db_teams[alias]

    # Substring match
    for db_name, team_id in db_teams.items():
        if name in db_name or db_name in name:
            return team_id

    return None


# ---------------------------------------------------------------------------
# Shared Tavily helper
# ---------------------------------------------------------------------------

async def _tavily_search(query: str, max_results: int = 3) -> str:
    if not settings.tavily_key:
        return ""
    import asyncio

    def _do_search():
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_key)
        return client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
        )

    try:
        # Run blocking Tavily call in a thread so it doesn't freeze the event loop
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, _do_search),
            timeout=15,
        )
        snippets = []
        if response.get("answer"):
            snippets.append(f"Summary: {response['answer']}")
        for r in response.get("results", [])[:max_results]:
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            source = r.get("url", "").split("/")[2] if r.get("url") else ""
            snippets.append(f"[{source}] {title}: {content}")
        return "\n\n".join(snippets)
    except asyncio.TimeoutError:
        print(f"Tavily search timed out: {query[:60]}")
        return ""
    except Exception as e:
        print(f"Tavily search error: {e}")
        return ""
