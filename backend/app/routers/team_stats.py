from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.config import get_settings
from app.database import get_connection

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


@router.post("/backfill")
async def backfill_team_stats(background_tasks: BackgroundTasks, x_ingest_key: str = Header(default="")):
    """
    One-off: fetch Tavily-sourced stats for every team that has already
    played at least one match, instead of waiting for their next match to
    finish. Runs in the background — a few dozen sequential Tavily+Groq
    calls would otherwise blow past a normal request timeout.
    """
    if not settings.scraper_ingest_key or x_ingest_key != settings.scraper_ingest_key:
        raise HTTPException(status_code=401, detail="Invalid or missing ingest key")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT t.name
        FROM teams t
        JOIN fixtures f ON t.id = f.home_team_id OR t.id = f.away_team_id
        WHERE f.status IN ('FT', 'AET', 'PEN')
    """)
    team_names = [r["name"] for r in cur.fetchall()]
    conn.close()

    background_tasks.add_task(_run_backfill, team_names)
    return {"status": "started", "teams_queued": len(team_names)}


async def _run_backfill(team_names: List[str]):
    from app.services.tavily_team_stats import fetch_team_stats
    updated = 0
    for name in team_names:
        try:
            result = await fetch_team_stats(name)
            if result:
                updated += 1
        except Exception as e:
            print(f"team stats backfill failed for {name}: {e}")
    print(f"Team stats backfill complete — {updated}/{len(team_names)} teams updated")
