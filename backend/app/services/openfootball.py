"""
openfootball WC2026 open data — no API key, no rate limits.
Provides real goal scorer names + minutes for all completed matches.
https://github.com/openfootball/worldcup.json
"""
import httpx
import unicodedata
from typing import Dict
from app.database import get_connection

DATA_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json"
    "/master/2026/worldcup.json"
)


def _normalize(name: str) -> str:
    """Strip accents, lowercase — used for fuzzy player name matching."""
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


async def sync_goal_scorers() -> int:
    """
    Fetch WC2026 match data from openfootball and update players.goals_intl
    with real tournament goal counts.  Safe to re-run; resets counts each time.
    Returns number of DB players successfully matched.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(DATA_URL)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"openfootball fetch error: {e}")
            return 0

    # Tally goals per scorer name (skip own-goal entries marked with 'OG')
    goal_tally: Dict[str, int] = {}
    for match in data.get("matches", []):
        for goal in (match.get("goals1") or []) + (match.get("goals2") or []):
            name = (goal.get("name") or "").strip()
            if not name or name.upper().endswith("(OG)") or name.upper() == "OG":
                continue
            goal_tally[name] = goal_tally.get(name, 0) + 1

    if not goal_tally:
        return 0

    conn = get_connection()
    cur = conn.cursor()

    # Build normalized name → player_id lookup from DB
    cur.execute("SELECT id, name FROM players")
    norm_to_id: Dict[str, int] = {}
    last_to_id: Dict[str, int] = {}  # last-name-only fallback
    for p in cur.fetchall():
        norm = _normalize(p["name"])
        if norm not in norm_to_id:
            norm_to_id[norm] = p["id"]
        last = norm.split()[-1]
        if last not in last_to_id:
            last_to_id[last] = p["id"]

    # Reset all tournament goals, then apply fresh counts
    cur.execute("UPDATE players SET goals_intl = 0")

    matched = 0
    unmatched = []
    for raw_name, goals in goal_tally.items():
        norm = _normalize(raw_name)
        pid = norm_to_id.get(norm)
        if pid is None:
            # Last-name fallback (handles "Messi" matching "Lionel Messi")
            last = norm.split()[-1]
            pid = last_to_id.get(last)
        if pid:
            cur.execute(
                "UPDATE players SET goals_intl = ? WHERE id = ?", (goals, pid)
            )
            matched += 1
        else:
            unmatched.append(raw_name)

    conn.commit()
    conn.close()

    print(
        f"openfootball goals: {len(goal_tally)} scorers, "
        f"{matched} matched, {len(unmatched)} unmatched"
    )
    if unmatched:
        print(f"  Unmatched: {unmatched[:10]}")
    return matched
