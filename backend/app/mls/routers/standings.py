from fastapi import APIRouter
from typing import Dict, List
from app.mls.database import get_connection

router = APIRouter(prefix="/mls/standings", tags=["mls-standings"])


@router.get("/", response_model=Dict[str, List[dict]])
async def get_mls_standings():
    """MLS standings grouped by conference (Eastern/Western)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, t.name as team_name, t.logo as team_logo, t.abbreviation as team_code
        FROM mls_standings s
        JOIN mls_teams t ON s.team_id = t.id
        ORDER BY s.conference ASC, s.rank ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    grouped: Dict[str, List[dict]] = {}
    for row in rows:
        grouped.setdefault(row["conference"] or "Unknown", []).append(row)
    return grouped
