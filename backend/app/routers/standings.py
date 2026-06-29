from fastapi import APIRouter
from typing import List, Optional
from app.database import get_connection

router = APIRouter(prefix="/standings", tags=["standings"])


@router.get("/", response_model=List[dict])
async def get_standings(group: Optional[str] = None):
    """Get group standings, optionally filtered by group letter."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT s.*, t.name as team_name, t.logo as team_logo, t.code as team_code
        FROM standings s
        JOIN teams t ON s.team_id = t.id
        WHERE 1=1
    """
    params = []

    if group:
        query += " AND s.group_letter = ?"
        params.append(group.upper())

    query += " ORDER BY s.group_letter ASC, s.rank ASC"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/groups", response_model=dict)
async def get_all_groups():
    """Get standings organized by group."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.*, t.name as team_name, t.logo as team_logo, t.code as team_code
        FROM standings s
        JOIN teams t ON s.team_id = t.id
        ORDER BY s.group_letter ASC, s.rank ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    groups = {}
    for row in rows:
        g = row["group_letter"] or "?"
        if g not in groups:
            groups[g] = []
        groups[g].append(row)

    return groups


@router.get("/bracket", response_model=List[dict])
async def get_bracket():
    """Get knockout stage fixtures."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*,
               COALESCE(ht.name, 'TBD') as home_name, ht.logo as home_logo,
               COALESCE(at.name, 'TBD') as away_name, at.logo as away_logo,
               p.home_win_pct, p.away_win_pct, p.draw_pct
        FROM fixtures f
        LEFT JOIN teams ht ON f.home_team_id = ht.id
        LEFT JOIN teams at ON f.away_team_id = at.id
        LEFT JOIN predictions p ON p.fixture_id = f.id
        WHERE f.round NOT LIKE '%Group%'
        ORDER BY f.date_utc ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
