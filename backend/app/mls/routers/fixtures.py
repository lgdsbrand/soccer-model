from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from app.mls.database import get_connection
from app.services import llm

MLS_LABEL = "the 2026 MLS season"

router = APIRouter(prefix="/mls/fixtures", tags=["mls-fixtures"])


@router.get("/", response_model=List[dict])
async def get_mls_fixtures(status: Optional[str] = None, limit: int = 50):
    """Get MLS fixtures, optionally filtered by status."""
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT f.*, ht.name as home_name, ht.logo as home_logo, ht.abbreviation as home_code,
               at.name as away_name, at.logo as away_logo, at.abbreviation as away_code
        FROM mls_fixtures f
        JOIN mls_teams ht ON f.home_team_id = ht.id
        JOIN mls_teams at ON f.away_team_id = at.id
        WHERE 1=1
    """
    params: list = []
    if status:
        query += " AND f.status = ?"
        params.append(status)
    query += " ORDER BY f.date_utc ASC LIMIT ?"
    params.append(limit)

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    # Frontend's shared Fixture type requires `round` and uses it (via an
    # explicit knockout-round allowlist, not a "Group Stage" blacklist) to
    # decide whether to show a 3-way win/draw/loss bar or a 2-way knockout
    # one — "Regular Season" correctly falls on the non-knockout side, which
    # is what MLS matches (real draws) need.
    for r in rows:
        r["round"] = "Regular Season"
    return rows


@router.get("/{fixture_id}", response_model=dict)
async def get_mls_fixture_detail(fixture_id: int, background_tasks: BackgroundTasks):
    """
    MLS match card: fixture + odds-derived prediction + lineups (LLM-predicted)
    + key players + style of play + season stats + AI analysis.
    No Dixon-Coles model, no weather, no live match stats — matches the
    scope confirmed for the MLS launch (see plan doc).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*,
               ht.name as home_name, ht.logo as home_logo, ht.conference as home_conference,
               at.name as away_name, at.logo as away_logo, at.conference as away_conference
        FROM mls_fixtures f
        JOIN mls_teams ht ON f.home_team_id = ht.id
        JOIN mls_teams at ON f.away_team_id = at.id
        WHERE f.id = ?
    """, (fixture_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="MLS fixture not found")

    fixture = dict(row)
    fixture["round"] = "Regular Season"

    # Lineups — LLM-predicted only (no confirmed-lineup source wired for MLS)
    cur.execute("SELECT * FROM mls_lineups WHERE fixture_id = ? AND is_predicted = 1", (fixture_id,))
    existing_lineups = [dict(r) for r in cur.fetchall()]
    conn.close()

    fixture["lineups_confirmed"] = False
    if existing_lineups:
        fixture["lineups"] = existing_lineups
    else:
        fixture["lineups"] = []
        background_tasks.add_task(
            _generate_predicted_lineups, fixture_id,
            fixture["home_team_id"], fixture["home_name"],
            fixture["away_team_id"], fixture["away_name"],
        )

    fixture["home_formation"] = None
    fixture["away_formation"] = None
    for entry in fixture["lineups"]:
        if entry.get("formation"):
            if entry.get("team_id") == fixture["home_team_id"]:
                fixture["home_formation"] = entry["formation"]
            elif entry.get("team_id") == fixture["away_team_id"]:
                fixture["away_formation"] = entry["formation"]

    fixture["home_match_stats"] = None
    fixture["away_match_stats"] = None
    fixture["home_last5"] = []
    fixture["away_last5"] = []

    fixture["home_team_stats"] = _get_mls_team_season_stats(fixture["home_name"])
    fixture["away_team_stats"] = _get_mls_team_season_stats(fixture["away_name"])

    # Goals/Goals Allowed per game — real observed averages from ESPN standings,
    # the same arithmetic WC uses for its own goals_per_game (see predictions.py's
    # get_attack_xg_ratings: gf/played, ga/played). No xg_rating/xga_rating
    # counterpart for MLS — those are WC's fitted Dixon-Coles attack/defense
    # params re-expressed, not real xG data, and there's no such model for MLS.
    fixture["home_goals_per_game"], fixture["home_goals_allowed_per_game"] = \
        _get_mls_goals_per_game(fixture["home_team_id"])
    fixture["away_goals_per_game"], fixture["away_goals_allowed_per_game"] = \
        _get_mls_goals_per_game(fixture["away_team_id"])

    # Prediction — odds-derived, same field shape as the WC `predictions` table
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM mls_match_probs WHERE fixture_id = ?", (fixture_id,))
    pred_row = cur.fetchone()
    conn.close()
    fixture["prediction"] = dict(pred_row) if pred_row else None

    # AI Analysis — cache key prefixed "mls-" so it can't collide with a WC
    # fixture_id from a totally different, uncoordinated ID space
    analysis_key = f"analysis:mls-{fixture_id}"
    from app.services.llm import _get_cached
    cached_analysis = _get_cached(analysis_key)
    if cached_analysis:
        fixture["ai_analysis"] = cached_analysis
    else:
        fixture["ai_analysis"] = None
        background_tasks.add_task(_generate_analysis, fixture_id, fixture)

    fixture["recommended_play"] = None  # out of scope for MLS launch

    # Key players
    try:
        fixture["home_key_players"] = await llm.get_key_players(fixture["home_name"], competition_label=MLS_LABEL)
    except Exception:
        fixture["home_key_players"] = []
    try:
        fixture["away_key_players"] = await llm.get_key_players(fixture["away_name"], competition_label=MLS_LABEL)
    except Exception:
        fixture["away_key_players"] = []

    # Style of play — "MLS club" framing, not "national football team"
    try:
        fixture["home_style_of_play"] = await llm.get_style_of_play(fixture["home_name"], team_type="MLS club")
    except Exception as e:
        print(f"Style of play failed for {fixture['home_name']}: {e}")
        fixture["home_style_of_play"] = None
    try:
        fixture["away_style_of_play"] = await llm.get_style_of_play(fixture["away_name"], team_type="MLS club")
    except Exception as e:
        print(f"Style of play failed for {fixture['away_name']}: {e}")
        fixture["away_style_of_play"] = None

    return fixture


def _get_mls_team_season_stats(team_name: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT corners, shots, fouls FROM mls_team_season_stats WHERE team_name = ?",
        (team_name,),
    )
    row = cur.fetchone()
    conn.close()
    if not row or (row["corners"] is None and row["shots"] is None and row["fouls"] is None):
        return None
    return dict(row)


def _get_mls_goals_per_game(team_id: int) -> tuple:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT goals_for, goals_against, played FROM mls_standings WHERE team_id = ?",
        (team_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row or not row["played"]:
        return None, None
    return round(row["goals_for"] / row["played"], 2), round(row["goals_against"] / row["played"], 2)


async def _generate_predicted_lineups(fixture_id: int, home_id: int, home_name: str, away_id: int, away_name: str):
    """Background task: generate LLM-predicted lineups for an MLS match."""
    for team_id, team_name in [(home_id, home_name), (away_id, away_name)]:
        lineup_data = await llm.get_predicted_lineup(team_name, competition_label=MLS_LABEL)
        if not lineup_data.get("players"):
            continue

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM mls_lineups WHERE fixture_id = ? AND team_id = ? AND is_predicted = 1",
                   (fixture_id, team_id))
        for p in lineup_data["players"][:11]:
            cur.execute("""
                INSERT INTO mls_lineups
                (fixture_id, team_id, formation, player_name, player_pos, player_grid, is_substitute, is_predicted)
                VALUES (?, ?, ?, ?, ?, ?, 0, 1)
            """, (fixture_id, team_id, lineup_data.get("formation"), p.get("name"),
                  p.get("position"), p.get("grid")))
        conn.commit()
        conn.close()


async def _generate_analysis(fixture_id: int, fixture: dict):
    """Background task: generate AI match analysis for an MLS match."""
    pred = fixture.get("prediction") or {}
    await llm.get_match_analysis({
        "fixture_id": f"mls-{fixture_id}",
        "home_team": fixture["home_name"],
        "away_team": fixture["away_name"],
        "home_win_pct": pred.get("home_win_pct", 40),
        "draw_pct": pred.get("draw_pct", 25),
        "away_win_pct": pred.get("away_win_pct", 35),
        "btts_pct": pred.get("btts_pct", 45),
        "over_3_5_pct": pred.get("over_3_5_pct", 55),
        "home_form": "",
        "away_form": "",
        "venue": fixture.get("venue_name", ""),
        "weather": "",
    }, competition_label="MLS")
