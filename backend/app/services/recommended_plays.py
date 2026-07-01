"""
Recommended plays: Tavily web search → Groq synthesis.
Replicates Tyler's manual process (reading Covers, ESPN, etc.) automatically.
"""
import json
import re
import time
from typing import Optional, Dict


def _extract_field(text: str, field: str) -> Optional[str]:
    """Regex-recover a string field from JSON that may be truncated mid-response."""
    m = re.search(rf'"{field}"\s*:\s*"([^"]*)', text)
    return m.group(1) if m else None
from app.config import get_settings
from app.database import get_connection
from app.services.llm import _groq_complete, _get_cached, _set_cached

settings = get_settings()


async def get_recommended_play(
    home_team: str,
    away_team: str,
    fixture_id: int,
    *args,
    **kwargs,
) -> Dict:
    """
    Search public expert predictions for this match and synthesize a recommendation.
    Based purely on external expert consensus — no internal model probabilities used.
    """
    cache_key = f"play_v2:{fixture_id}"
    cached = _get_cached(cache_key, ttl=3600 * 12)  # 12hr TTL
    if cached:
        return json.loads(cached)

    search_results = await _tavily_search(home_team, away_team)

    prompt = f"""You are a sharp sports analyst. Synthesize a betting recommendation for:

{home_team} vs {away_team} — FIFA World Cup 2026

Public expert consensus from major sports and betting sites:
{search_results if search_results else "No external data available — base your answer on general tournament knowledge."}

Provide:
1. PRIMARY BET: One specific recommendation (e.g., "{home_team} to win", "BTTS Yes", "Over 1.5 goals")
2. CONFIDENCE: High / Medium / Low
3. REASONING: 2 sentences explaining why, citing the expert consensus above

Format as JSON: {{"primary_bet": "...", "confidence": "...", "reasoning": "...", "alternative": "..."}}"""

    content = _groq_complete(prompt, model="llama-3.3-70b-versatile", max_tokens=400)

    result = {
        "primary_bet": "Recommendation unavailable",
        "confidence": "Medium",
        "reasoning": "Unable to generate a recommendation for this match yet — check back soon.",
        "alternative": None,
        "search_used": bool(search_results),
    }

    if content:
        start = content.find("{")
        end = content.rfind("}") + 1
        raw = content[start:end] if start >= 0 and end > start else content
        try:
            parsed = json.loads(raw)
            result.update(parsed)
            result["search_used"] = bool(search_results)
        except (json.JSONDecodeError, ValueError):
            # Response was likely truncated mid-JSON (hit max_tokens) — recover
            # whatever fields completed before the cutoff instead of leaving
            # the placeholder primary_bet/reasoning in the cached result.
            primary = _extract_field(raw, "primary_bet")
            confidence = _extract_field(raw, "confidence")
            reasoning = _extract_field(raw, "reasoning")
            if primary:
                result["primary_bet"] = primary
            if confidence:
                result["confidence"] = confidence
            if reasoning:
                result["reasoning"] = reasoning
            result["search_used"] = bool(search_results)

    _set_cached(f"play_v2:{fixture_id}", json.dumps(result))
    return result


async def _tavily_search(home_team: str, away_team: str) -> str:
    """Search for expert predictions using Tavily API."""
    if not settings.tavily_key:
        return ""

    query = f"{home_team} vs {away_team} World Cup 2026 prediction betting odds"

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
        )

        snippets = []
        if response.get("answer"):
            snippets.append(f"AI Summary: {response['answer']}")

        for r in response.get("results", [])[:4]:
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            source = r.get("url", "").split("/")[2] if r.get("url") else ""
            snippets.append(f"[{source}] {title}: {content}")

        return "\n\n".join(snippets)

    except Exception as e:
        print(f"Tavily search failed: {e}")
        return ""
