from fastapi import APIRouter, Header, HTTPException
from app.config import get_settings
from app.database import get_connection
from app.services.fotmob_team_stats import refresh_all_team_stats

router = APIRouter(prefix="/team-stats", tags=["team-stats"])
settings = get_settings()


@router.get("/")
async def list_team_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM team_season_stats ORDER BY updated_at DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@router.post("/backfill")
async def backfill_team_stats(x_ingest_key: str = Header(default="")):
    """
    One-off: refresh corners/shots-on-target/fouls for every team right now,
    instead of waiting for the next match to finish. Fast (three FotMob API
    calls total) so this runs synchronously rather than as a background task.
    """
    if not settings.scraper_ingest_key or x_ingest_key != settings.scraper_ingest_key:
        raise HTTPException(status_code=401, detail="Invalid or missing ingest key")

    updated = await refresh_all_team_stats()
    return {"status": "ok", "teams_updated": updated}
