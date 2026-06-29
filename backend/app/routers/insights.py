from fastapi import APIRouter
from typing import List, Optional
from app.database import get_connection
from app.services.llm import get_style_of_play, get_match_analysis, _get_cached

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/style/{team_id}", response_model=dict)
async def get_team_style(team_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, coach FROM teams WHERE id = ?", (team_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"style": "Team not found"}
    style = await get_style_of_play(row["name"], row["coach"])
    return {"team_id": team_id, "team_name": row["name"], "style": style}


@router.get("/analysis/{fixture_id}", response_model=dict)
async def get_analysis(fixture_id: int):
    """Get cached AI analysis for a fixture."""
    cache_key = f"analysis:{fixture_id}"
    cached = _get_cached(cache_key)
    if cached:
        return {"fixture_id": fixture_id, "analysis": cached, "cached": True}
    return {"fixture_id": fixture_id, "analysis": None, "cached": False}


@router.get("/home", response_model=dict)
async def get_home_data():
    """Aggregate homepage data: next match, top players, recent results, winner odds."""
    import time
    import datetime
    conn = get_connection()
    cur = conn.cursor()

    # Next match
    cur.execute("""
        SELECT f.id, f.date_utc, f.round, f.status, f.venue_name, f.venue_city,
               ht.id as home_id, ht.name as home_name, ht.logo as home_logo,
               at.id as away_id, at.name as away_name, at.logo as away_logo,
               p.home_win_pct, p.draw_pct, p.away_win_pct, p.btts_pct
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        LEFT JOIN predictions p ON p.fixture_id = f.id
        WHERE f.date_utc > ? AND f.status IN ('NS', 'TBD', '1H', '2H', 'HT')
        ORDER BY f.date_utc ASC LIMIT 1
    """, (time.time() - 7200,))
    next_match = cur.fetchone()

    # Recent results (last 8 completed)
    cur.execute("""
        SELECT f.id, f.date_utc, f.round, f.status, f.home_score, f.away_score,
               ht.name as home_name, ht.logo as home_logo,
               at.name as away_name, at.logo as away_logo
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.status = 'FT'
        ORDER BY f.date_utc DESC LIMIT 8
    """)
    recent_results = [dict(r) for r in cur.fetchall()]

    # Tournament winner probabilities (top 8)
    cur.execute("""
        SELECT ap.winner_pct, ap.final_pct,
               t.id as team_id, t.name as team_name, t.logo, t.group_letter
        FROM advancement_probs ap
        JOIN teams t ON ap.team_id = t.id
        ORDER BY ap.winner_pct DESC
        LIMIT 8
    """)
    winner_probs = [dict(r) for r in cur.fetchall()]

    # Top players by goals (falls back to assists if all goals are 0)
    cur.execute("""
        SELECT p.id, p.name, p.position, p.photo, p.goals_intl, p.assists_intl,
               t.name as team_name, t.logo as team_logo
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE t.group_letter IS NOT NULL AND t.name != 'TBD'
        ORDER BY p.goals_intl DESC, p.assists_intl DESC, p.name ASC
        LIMIT 5
    """)
    top_players = [dict(r) for r in cur.fetchall()]

    # Today's other matches (all today except the one already shown as next_match)
    today_utc = datetime.datetime.now(datetime.timezone.utc).date()
    today_start = datetime.datetime(
        today_utc.year, today_utc.month, today_utc.day,
        tzinfo=datetime.timezone.utc
    ).timestamp()
    today_end = today_start + 86400
    cur.execute("""
        SELECT f.id, f.date_utc, f.round, f.status, f.home_score, f.away_score,
               ht.name as home_name, ht.logo as home_logo,
               at.name as away_name, at.logo as away_logo
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.date_utc >= ? AND f.date_utc < ?
        ORDER BY f.date_utc ASC
    """, (today_start, today_end))
    next_match_id = next_match["id"] if next_match else None
    today_matches = [dict(r) for r in cur.fetchall() if r["id"] != next_match_id]

    # Tournament stats
    cur.execute("SELECT COUNT(*) as total FROM fixtures WHERE status = 'FT'")
    matches_played = cur.fetchone()["total"]

    cur.execute("SELECT COALESCE(SUM(home_score + away_score), 0) as total FROM fixtures WHERE status = 'FT'")
    total_goals = cur.fetchone()["total"]

    cur.execute("SELECT COUNT(*) as total FROM fixtures WHERE status IN ('NS', 'TBD')")
    matches_remaining = cur.fetchone()["total"]

    conn.close()

    next_match_out = None
    if next_match:
        next_match_out = dict(next_match)
        next_match_out["ai_analysis"] = _get_cached(f"analysis:{next_match_out['id']}")

    return {
        "next_match": next_match_out,
        "today_matches": today_matches,
        "recent_results": recent_results,
        "winner_probabilities": winner_probs,
        "top_players": top_players,
        "stats": {
            "matches_played": matches_played,
            "total_goals": total_goals,
            "matches_remaining": matches_remaining,
            "avg_goals_per_match": round(total_goals / matches_played, 2) if matches_played else 0,
        }
    }
