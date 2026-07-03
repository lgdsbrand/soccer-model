from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.config import get_settings
from app.database import get_connection

router = APIRouter(prefix="/team-stats", tags=["team-stats"])
settings = get_settings()


class TeamStatEntry(BaseModel):
    team_name: str
    corners: Optional[int] = None
    shots: Optional[int] = None
    fouls: Optional[int] = None


class IngestPayload(BaseModel):
    source: str = "fifa.com"
    teams: List[TeamStatEntry]


@router.post("/ingest")
async def ingest_team_stats(payload: IngestPayload, x_ingest_key: str = Header(default="")):
    """
    Receives scraped season-total corners/shots/fouls per team, called twice
    daily by the GitHub Actions scraper (see .github/workflows/scrape-team-stats.yml).
    Protected by a shared secret since this writes data — not for public use.
    """
    if not settings.scraper_ingest_key or x_ingest_key != settings.scraper_ingest_key:
        raise HTTPException(status_code=401, detail="Invalid or missing ingest key")

    conn = get_connection()
    cur = conn.cursor()
    for t in payload.teams:
        cur.execute("""
            INSERT INTO team_season_stats (team_name, corners, shots, fouls, source, updated_at)
            VALUES (?, ?, ?, ?, ?, unixepoch())
            ON CONFLICT(team_name) DO UPDATE SET
                corners = excluded.corners,
                shots = excluded.shots,
                fouls = excluded.fouls,
                source = excluded.source,
                updated_at = excluded.updated_at
        """, (t.team_name, t.corners, t.shots, t.fouls, payload.source))
    conn.commit()
    conn.close()

    return {"status": "ok", "teams_updated": len(payload.teams)}
