"""
MLS power rankings, scraped from Sonny Moore's Computer Power Ratings
(https://sonnymoorepowerratings.com/mls.htm) — a plain-text <pre> table,
not JSON, so this is regex parsing rather than an API client.

The site 406s a bare httpx request (Mod_Security blocking requests that
don't look like a real browser) — confirmed live 2026-07-25; a full
browser-like header set (Accept/Accept-Language, not just User-Agent)
is required to get a 200.
"""
import re
import time
from typing import Dict, List, Tuple
from app.mls.database import get_connection

POWER_RATINGS_URL = "https://sonnymoorepowerratings.com/mls.htm"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Matches rows like " 13 NYC FC                  6    6   4   94.278  94.378"
# inside the page's <pre> block: rank, team name (letters/periods/spaces,
# non-greedy so it doesn't swallow the W column), then W L T SOS PR.
_ROW_RE = re.compile(r"^\s*(\d+)\s+([A-Z][A-Z. ]*?)\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+[\d.]+\s*$", re.MULTILINE)

# Sonny Moore's team names vs. mls_teams.name — most rows match mls_teams's
# short_name directly (case-insensitive), these are the exceptions. Verified
# live 2026-07-25 against a real fetch: all 30 MLS clubs matched, 0 unmatched.
SONNY_MOORE_NAME_TO_MLS_NAME: Dict[str, str] = {
    "LOS ANGELES FC": "LAFC",
    "NYC FC": "New York City FC",
    "NEW YORK": "New York Red Bulls",
    "WASHINGTON": "D.C. United",
    "MONTREAL": "CF Montréal",
}


def _parse_ratings(html: str) -> List[Tuple[int, str]]:
    return [(int(rank), name.strip()) for rank, name in _ROW_RE.findall(html)]


async def refresh_power_ratings() -> int:
    """Fetch the current MLS power-rating table and upsert into mls_power_ratings."""
    import httpx

    async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(POWER_RATINGS_URL)
        resp.raise_for_status()
        html = resp.text

    rows = _parse_ratings(html)
    if not rows:
        return 0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, short_name FROM mls_teams")
    by_short_name = {r["short_name"].upper(): r["name"] for r in cur.fetchall() if r["short_name"]}

    now = time.time()
    unmatched = []
    matched = 0
    for rank, raw_name in rows:
        mls_name = SONNY_MOORE_NAME_TO_MLS_NAME.get(raw_name) or by_short_name.get(raw_name)
        if not mls_name:
            unmatched.append(raw_name)
            continue
        cur.execute("""
            INSERT INTO mls_power_ratings (team_name, rank, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(team_name) DO UPDATE SET
                rank = excluded.rank,
                updated_at = excluded.updated_at
        """, (mls_name, rank, now))
        matched += 1

    conn.commit()
    conn.close()

    if unmatched:
        print(f"MLS power ratings: {len(unmatched)} team name(s) not matched — "
              f"extend SONNY_MOORE_NAME_TO_MLS_NAME: {unmatched}")

    return matched
