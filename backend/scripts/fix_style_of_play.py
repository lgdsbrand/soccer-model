"""
Clear all cached style-of-play entries and regenerate them with the improved
prompt (app/services/llm.py get_style_of_play), which forbids disclaimers and
retries once before falling back to a generic line.

Run from backend/:
    python scripts/fix_style_of_play.py
"""
import asyncio
from app.database import get_connection
from app.services import llm


async def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM llm_cache WHERE cache_key LIKE 'style:%'")
    conn.commit()

    cur.execute("SELECT DISTINCT name, coach FROM teams WHERE name != 'TBD' ORDER BY name")
    teams = cur.fetchall()
    conn.close()

    print(f"Regenerating style of play for {len(teams)} teams...")
    bad = []
    for t in teams:
        content = await llm.get_style_of_play(t["name"], t["coach"])
        flagged = llm._is_bad_response(content)
        marker = "BAD " if flagged else "ok  "
        print(f"{marker} {t['name']}: {content[:100]}")
        if flagged:
            bad.append(t["name"])

    print(f"\nDone. {len(bad)} teams still flagged: {bad}")


if __name__ == "__main__":
    asyncio.run(main())
