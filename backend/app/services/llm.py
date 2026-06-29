"""
LLM integration: Groq (quick analysis, style-of-play, lineups) +
Google GenAI (full AI analysis card).
All outputs cached in SQLite.
"""
import json
import time
from typing import Optional, Dict, List
from app.config import get_settings
from app.database import get_connection

settings = get_settings()


def _get_cached(key: str, ttl: int = None) -> Optional[str]:
    if ttl is None:
        ttl = settings.cache_llm_ttl
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT content, generated_at FROM llm_cache WHERE cache_key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row and (time.time() - row["generated_at"]) < ttl:
        return row["content"]
    return None


def _set_cached(key: str, content: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO llm_cache (cache_key, content, generated_at)
        VALUES (?, ?, ?)
    """, (key, content, time.time()))
    conn.commit()
    conn.close()


def _groq_complete(prompt: str, model: str = "llama-3.1-8b-instant", max_tokens: int = 500) -> Optional[str]:
    if not settings.groq_api_key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq error: {e}")
        return None


def _gemini_complete(prompt: str, max_tokens: int = 800) -> Optional[str]:
    if not settings.google_genai_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.google_genai_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens, "temperature": 0.7}
        )
        return resp.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return None


async def get_style_of_play(team_name: str, coach: Optional[str] = None) -> str:
    """Generate or retrieve cached team style of play description."""
    cache_key = f"style:{team_name.lower().replace(' ', '_')}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    coach_info = f"coached by {coach}" if coach else ""
    prompt = f"""In 2-3 sentences, describe {team_name}'s typical style of play at the 2026 FIFA World Cup {coach_info}.
Focus on: formation tendencies, pressing intensity, build-up style, attacking approach.
Be specific and tactical. No fluff."""

    content = _groq_complete(prompt, max_tokens=150) or f"{team_name} plays a competitive style with organized defending and dangerous counter-attacks."
    _set_cached(cache_key, content)
    return content


async def get_predicted_lineup(
    team_name: str,
    formation: Optional[str] = None,
    known_players: Optional[List[str]] = None
) -> Dict:
    """Generate predicted lineup using LLM."""
    cache_key = f"lineup_pred:{team_name.lower().replace(' ', '_')}"
    cached = _get_cached(cache_key, ttl=3600 * 6)  # 6hr TTL for lineup predictions
    if cached:
        return json.loads(cached)

    players_hint = ""
    if known_players:
        players_hint = f"Known squad members include: {', '.join(known_players[:15])}."

    prompt = f"""Predict the most likely starting XI for {team_name} at the 2026 FIFA World Cup.
Formation: {formation or 'most common'}.
{players_hint}

Return ONLY a JSON object with this exact structure:
{{
  "formation": "4-3-3",
  "players": [
    {{"name": "Player Name", "position": "GK", "number": 1, "grid": "1:1"}},
    ...
  ]
}}
Grid format: "row:col" where row 1=goalkeeper, row 2=defenders, etc.
Include exactly 11 players."""

    content = _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=400)

    if content:
        try:
            # Extract JSON from response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                lineup_data = json.loads(content[start:end])
                _set_cached(cache_key, json.dumps(lineup_data))
                return lineup_data
        except json.JSONDecodeError:
            pass

    default = {
        "formation": formation or "4-4-2",
        "players": [],
        "is_fallback": True
    }
    return default


async def _search_team_news(home: str, away: str) -> str:
    """
    Tavily search for pre-match news: injuries, lineup updates, recent form.
    Two targeted queries — one per team — merged into a single context block.
    Results cached for 3 hours so the same match doesn't burn search quota on
    every page load.
    """
    if not settings.tavily_key:
        return ""

    cache_key = f"news_search:{home.lower().replace(' ', '_')}_vs_{away.lower().replace(' ', '_')}"
    cached = _get_cached(cache_key, ttl=3600 * 3)
    if cached:
        return cached

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_key)

        snippets: List[str] = []

        for team, query in [
            (home, f"{home} World Cup 2026 injury news lineup team news"),
            (away, f"{away} World Cup 2026 injury news lineup team news"),
        ]:
            resp = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=False,
            )
            team_snippets: List[str] = []
            for r in resp.get("results", []):
                title = r.get("title", "")
                snippet = r.get("content", "")[:250].strip()
                source = r.get("url", "").split("/")[2] if r.get("url") else ""
                if snippet:
                    team_snippets.append(f"  • [{source}] {title}: {snippet}")

            if team_snippets:
                snippets.append(f"{team} news:\n" + "\n".join(team_snippets))

        result = "\n\n".join(snippets)
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        print(f"Team news search failed: {e}")
        return ""


async def get_match_analysis(match_context: Dict) -> str:
    """
    Full AI match analysis using Gemini (deeper) with Groq fallback.
    Enriched with live Tavily news search for injuries and lineup updates.
    """
    fixture_id = match_context.get("fixture_id", "")
    cache_key = f"analysis:{fixture_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    home = match_context.get("home_team", "Home Team")
    away = match_context.get("away_team", "Away Team")
    home_win = match_context.get("home_win_pct", 40)
    draw = match_context.get("draw_pct", 25)
    away_win = match_context.get("away_win_pct", 35)
    btts = match_context.get("btts_pct", 45)
    over15 = match_context.get("over_1_5_pct", 70)
    home_last5 = match_context.get("home_form", "")
    away_last5 = match_context.get("away_form", "")
    venue = match_context.get("venue", "")
    weather = match_context.get("weather", "")

    # Fetch live news for both teams before building the prompt
    live_news = await _search_team_news(home, away)
    news_section = f"\nLatest news and injury updates (live web search):\n{live_news}" if live_news else ""

    prompt = f"""You are an expert football analyst. Write a sharp, data-driven match preview for:

{home} vs {away}
Venue: {venue}
Weather: {weather}

Model probabilities: {home} wins {home_win}% | Draw {draw}% | {away} wins {away_win}%
BTTS: {btts}% | Over 1.5 goals: {over15}%

{home} recent form: {home_last5}
{away} recent form: {away_last5}
{news_section}

Write 3-4 sentences covering: key tactical matchup, any injury or lineup concerns from the news above, most likely outcome, one specific prediction. Be direct and confident. If the news reveals a key absence, factor it into your assessment."""

    content = (
        _gemini_complete(prompt, max_tokens=350) or
        _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=350) or
        f"{home} faces {away} with the model giving {home} a {home_win}% win probability. "
        f"Both teams to score looks likely at {btts}%."
    )

    _set_cached(cache_key, content)
    return content


async def get_key_players(team_name: str, squad_names: Optional[List[str]] = None) -> List[Dict]:
    """Return 3-5 key players for a team."""
    cache_key = f"key_players:{team_name.lower().replace(' ', '_')}"
    cached = _get_cached(cache_key)
    if cached:
        return json.loads(cached)

    squad_hint = f"Known squad: {', '.join(squad_names[:20])}." if squad_names else ""

    prompt = f"""List the 4 most important players for {team_name} at the 2026 FIFA World Cup.
{squad_hint}

Return ONLY a JSON array:
[
  {{"name": "Player Name", "position": "CF", "role": "Target striker and penalty taker", "club": "Club Name"}},
  ...
]"""

    content = _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=300)

    players = []
    if content:
        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                players = json.loads(content[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

    if not players:
        players = [{"name": "Squad data loading", "position": "—", "role": "—", "club": "—"}]

    _set_cached(cache_key, json.dumps(players))
    return players
