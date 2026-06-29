from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from app.database import get_connection
from app.services import api_football, weather as weather_svc, llm, recommended_plays
from app.services.predictions import compute_and_store_prediction
from app.models.schemas import MatchCard, MatchResult, Lineup, LineupPlayer

router = APIRouter(prefix="/fixtures", tags=["fixtures"])


@router.get("/", response_model=List[dict])
async def get_fixtures(
    round: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get all WC2026 fixtures, optionally filtered."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT f.*, ht.name as home_name, ht.logo as home_logo, ht.code as home_code,
               at.name as away_name, at.logo as away_logo, at.code as away_code
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE 1=1
    """
    params = []

    if round:
        query += " AND f.round LIKE ?"
        params.append(f"%{round}%")
    if status:
        query += " AND f.status = ?"
        params.append(status)

    query += " ORDER BY f.date_utc ASC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/today", response_model=List[dict])
async def get_today_fixtures():
    """Get today's matches."""
    import time
    now = time.time()
    day_start = now - (now % 86400)
    day_end = day_start + 86400

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo, ht.group_letter as home_group,
               at.name as away_name, at.logo as away_logo, at.group_letter as away_group
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.date_utc BETWEEN ? AND ?
        ORDER BY f.date_utc ASC
    """, (day_start, day_end))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/next", response_model=dict)
async def get_next_fixture():
    """Get the next upcoming match."""
    import time
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo, ht.group_letter as home_group,
               at.name as away_name, at.logo as away_logo, at.group_letter as away_group,
               p.home_win_pct, p.draw_pct, p.away_win_pct, p.btts_pct, p.over_1_5_pct
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        LEFT JOIN predictions p ON p.fixture_id = f.id
        WHERE f.date_utc > ? AND f.status IN ('NS', 'TBD')
        ORDER BY f.date_utc ASC
        LIMIT 1
    """, (time.time(),))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="No upcoming fixtures")
    return dict(row)


@router.get("/{fixture_id}", response_model=dict)
async def get_fixture_detail(fixture_id: int, background_tasks: BackgroundTasks):
    """
    Full match card: fixture + weather + last5 + lineup + stats + prediction + analysis.
    Non-blocking: analysis/lineup generated in background if not cached.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*,
               ht.name as home_name, ht.logo as home_logo, ht.group_letter as home_group,
               ht.coach as home_coach, ht.formation_default as home_formation,
               at.name as away_name, at.logo as away_logo, at.group_letter as away_group,
               at.coach as away_coach, at.formation_default as away_formation
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.id = ?
    """, (fixture_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Fixture not found")

    fixture = dict(row)

    # Weather
    fixture["weather"] = None
    if fixture.get("venue_city"):
        try:
            fixture["weather"] = await weather_svc.get_weather(
                fixture["venue_city"],
                fixture.get("venue_lat"),
                fixture.get("venue_lon")
            )
        except Exception:
            pass

    # Last 5 results
    try:
        fixture["home_last5"] = await api_football.fetch_last5(fixture["home_team_id"])
    except Exception:
        fixture["home_last5"] = []
    try:
        fixture["away_last5"] = await api_football.fetch_last5(fixture["away_team_id"])
    except Exception:
        fixture["away_last5"] = []

    # Lineup (confirmed if available, else predicted)
    try:
        lineups = await api_football.fetch_lineups(fixture_id)
    except Exception:
        lineups = None
    if lineups:
        fixture["lineups"] = lineups
        fixture["lineups_confirmed"] = True
    else:
        fixture["lineups_confirmed"] = False
        background_tasks.add_task(
            _generate_predicted_lineups, fixture_id,
            fixture["home_team_id"], fixture["home_name"], fixture["home_formation"],
            fixture["away_team_id"], fixture["away_name"], fixture["away_formation"]
        )
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM lineups WHERE fixture_id = ? AND is_predicted = 1", (fixture_id,))
            fixture["lineups"] = [dict(r) for r in cur.fetchall()]
            conn.close()
        except Exception:
            fixture["lineups"] = []

    # Match stats (shots, corners, fouls) for finished matches
    fixture["home_match_stats"] = None
    fixture["away_match_stats"] = None
    if fixture.get("status") in ("FT", "AET", "PEN"):
        try:
            stats_list = await api_football.fetch_match_stats(fixture_id)
            if stats_list:
                for s in stats_list:
                    if s["team_id"] == fixture["home_team_id"]:
                        fixture["home_match_stats"] = s
                    elif s["team_id"] == fixture["away_team_id"]:
                        fixture["away_match_stats"] = s
        except Exception:
            pass

    # Avg stats (last 5 games)
    try:
        fixture["home_stats_avg"] = await _get_team_avg_stats(fixture["home_team_id"])
    except Exception:
        fixture["home_stats_avg"] = {}
    try:
        fixture["away_stats_avg"] = await _get_team_avg_stats(fixture["away_team_id"])
    except Exception:
        fixture["away_stats_avg"] = {}

    # Prediction
    fixture["prediction"] = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM predictions WHERE fixture_id = ?", (fixture_id,))
        pred_row = cur.fetchone()
        conn.close()
        if pred_row:
            fixture["prediction"] = dict(pred_row)
        else:
            fixture["prediction"] = compute_and_store_prediction(fixture_id, fixture["home_name"], fixture["away_name"])
    except Exception:
        pass

    # AI Analysis (background if not cached)
    analysis_key = f"analysis:{fixture_id}"
    from app.services.llm import _get_cached
    try:
        cached_analysis = _get_cached(analysis_key)
        if cached_analysis:
            fixture["ai_analysis"] = cached_analysis
        else:
            fixture["ai_analysis"] = None
            background_tasks.add_task(_generate_analysis, fixture_id, fixture)
    except Exception:
        fixture["ai_analysis"] = None

    # Recommended play
    fixture["recommended_play"] = None
    try:
        play_key = f"play_v2:{fixture_id}"
        cached_play = _get_cached(play_key, ttl=3600 * 12)
        if cached_play:
            import json
            fixture["recommended_play"] = json.loads(cached_play)
        else:
            background_tasks.add_task(
                recommended_plays.get_recommended_play,
                fixture["home_name"], fixture["away_name"], fixture_id,
            )
    except Exception:
        pass

    # Key players
    try:
        fixture["home_key_players"] = await llm.get_key_players(fixture["home_name"])
    except Exception:
        fixture["home_key_players"] = []
    try:
        fixture["away_key_players"] = await llm.get_key_players(fixture["away_name"])
    except Exception:
        fixture["away_key_players"] = []

    return fixture


async def _get_team_avg_stats(team_id: int) -> dict:
    """Compute avg stats over last 5 completed matches for this team."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ms.*
        FROM match_stats ms
        JOIN fixtures f ON ms.fixture_id = f.id
        WHERE ms.team_id = ? AND f.status = 'FT'
        ORDER BY f.date_utc DESC
        LIMIT 5
    """, (team_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return {}

    def avg(field):
        vals = [r[field] for r in rows if r[field] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "shots_total": avg("shots_total"),
        "shots_on_target": avg("shots_on_target"),
        "corners": avg("corners"),
        "fouls": avg("fouls"),
        "yellow_cards": avg("yellow_cards"),
    }


async def _generate_predicted_lineups(
    fixture_id: int,
    home_id: int, home_name: str, home_formation: Optional[str],
    away_id: int, away_name: str, away_formation: Optional[str]
):
    """Background task: generate LLM-predicted lineups."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM players WHERE team_id = ? LIMIT 25", (home_id,))
    home_players = [r["name"] for r in cur.fetchall()]
    cur.execute("SELECT name FROM players WHERE team_id = ? LIMIT 25", (away_id,))
    away_players = [r["name"] for r in cur.fetchall()]
    conn.close()

    for team_id, team_name, formation, known_players in [
        (home_id, home_name, home_formation, home_players),
        (away_id, away_name, away_formation, away_players)
    ]:
        lineup_data = await llm.get_predicted_lineup(team_name, formation, known_players)
        if not lineup_data.get("players"):
            continue

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lineups WHERE fixture_id = ? AND team_id = ? AND is_predicted = 1",
                   (fixture_id, team_id))
        for i, p in enumerate(lineup_data["players"][:11]):
            cur.execute("""
                INSERT INTO lineups
                (fixture_id, team_id, formation, player_name, player_pos, player_grid, is_substitute, is_predicted)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            """, (fixture_id, team_id, lineup_data.get("formation"), p.get("name"),
                  p.get("position"), p.get("grid")))
        conn.commit()
        conn.close()


async def _generate_analysis(fixture_id: int, fixture: dict):
    """Background task: generate AI match analysis."""
    pred = fixture.get("prediction") or {}
    home_form = " ".join([
        "W" if r.get("home_team_id") == fixture["home_team_id"] and r.get("home_score", 0) > r.get("away_score", 0)
        else "D" if r.get("home_score") == r.get("away_score") else "L"
        for r in fixture.get("home_last5", [])
    ])
    away_form = " ".join([
        "W" if r.get("home_team_id") == fixture["away_team_id"] and r.get("home_score", 0) > r.get("away_score", 0)
        else "D" if r.get("home_score") == r.get("away_score") else "L"
        for r in fixture.get("away_last5", [])
    ])

    weather_str = ""
    if fixture.get("weather"):
        w = fixture["weather"]
        weather_str = f"{w['temperature_c']}°C, {w['description']}"

    await llm.get_match_analysis({
        "fixture_id": fixture_id,
        "home_team": fixture["home_name"],
        "away_team": fixture["away_name"],
        "home_win_pct": pred.get("home_win_pct", 40),
        "draw_pct": pred.get("draw_pct", 25),
        "away_win_pct": pred.get("away_win_pct", 35),
        "btts_pct": pred.get("btts_pct", 45),
        "over_1_5_pct": pred.get("over_1_5_pct", 70),
        "home_form": home_form,
        "away_form": away_form,
        "venue": fixture.get("venue_name", ""),
        "weather": weather_str,
    })

from typing import Optional
