from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from app.mls.database import get_connection
from app.services import llm, weather as weather_svc

MLS_LABEL = "the 2026 MLS season"

router = APIRouter(prefix="/mls/fixtures", tags=["mls-fixtures"])


@router.get("/", response_model=List[dict])
async def get_mls_fixtures(status: Optional[str] = None, season: Optional[int] = None, limit: int = 50):
    """Get MLS fixtures, optionally filtered by status and/or season.

    `season` matters now that `mls_fixtures` holds 4 backfilled seasons
    (2023-2025 for head-to-head, plus the live 2026 season): with no
    filter, `ORDER BY date_utc ASC LIMIT n` returns the OLDEST n rows
    across all of them, i.e. 2023 season openers — callers that want
    "current" data (dashboard, schedule) need to scope to one season
    explicitly rather than relying on limit alone.
    """
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
    if season:
        query += " AND f.season = ?"
        params.append(season)
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


@router.get("/top-plays", response_model=dict)
async def get_mls_top_plays():
    """
    Dashboard "Top Plays": the highest-probability match for BTTS, O1.5, and
    O2.5 (one per stat), scanned across the next several days rather than
    just today — MLS's 1-2x/week schedule means "today" is very often empty,
    which used to hide the whole section on a no-games day (bad for a demo).
    Returns one entry per day that actually has at least one play, skipping
    empty days entirely, stopping once a handful of populated days are found.
    Must be declared before `/{fixture_id}` — otherwise FastAPI tries to
    parse "top-plays" as the int path param and 422s.
    """
    from app.utils import get_day_bounds_et

    def best(rows: list, field: str):
        candidates = [r for r in rows if r.get(field) is not None]
        if not candidates:
            return None
        top = max(candidates, key=lambda r: r[field])
        return {
            "fixture_id": top["fixture_id"],
            "date_utc": top["date_utc"],
            "home_name": top["home_name"],
            "home_logo": top["home_logo"],
            "away_name": top["away_name"],
            "away_logo": top["away_logo"],
            "value": top[field],
        }

    conn = get_connection()
    cur = conn.cursor()
    days = []
    for offset in range(14):  # scan up to 2 weeks ahead for the next few populated days
        start, end, date_str = get_day_bounds_et(offset)
        cur.execute("""
            SELECT f.id as fixture_id, f.date_utc,
                   ht.name as home_name, ht.logo as home_logo,
                   at.name as away_name, at.logo as away_logo,
                   p.btts_pct, p.over_1_5_pct, p.over_2_5_pct
            FROM mls_fixtures f
            JOIN mls_teams ht ON f.home_team_id = ht.id
            JOIN mls_teams at ON f.away_team_id = at.id
            JOIN mls_match_probs p ON p.fixture_id = f.id
            WHERE f.date_utc BETWEEN ? AND ?
        """, (start, end))
        rows = [dict(r) for r in cur.fetchall()]
        if not rows:
            continue

        day_plays = {
            "btts": best(rows, "btts_pct"),
            "over_1_5": best(rows, "over_1_5_pct"),
            "over_2_5": best(rows, "over_2_5_pct"),
        }
        if any(day_plays.values()):
            days.append({"date": date_str, **day_plays})
        if len(days) >= 5:
            break
    conn.close()

    return {"days": days}


@router.get("/{fixture_id}", response_model=dict)
async def get_mls_fixture_detail(fixture_id: int, background_tasks: BackgroundTasks):
    """
    MLS match card: fixture + odds-derived prediction + lineups (LLM-predicted)
    + key players + style of play + season stats + weather + AI analysis.
    No Dixon-Coles model, no live match stats — matches the scope confirmed
    for the MLS launch (see plan doc).
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
    # Field kept as "last5" to match the shared frontend FixtureDetail type
    # (also used by WC), but holds up to 10 results for MLS — see FormRow
    # in MatchCard.tsx, which sizes its "Last N" label off the array length.
    fixture["home_last5"] = _get_mls_last10(fixture["home_team_id"])
    fixture["away_last5"] = _get_mls_last10(fixture["away_team_id"])

    fixture["weather"] = None
    if fixture.get("venue_city"):
        try:
            fixture["weather"] = await weather_svc.get_weather(fixture["venue_city"])
        except Exception:
            pass

    fixture["head_to_head"] = _get_mls_head_to_head(fixture["home_team_id"], fixture["away_team_id"])

    fixture["home_team_record"] = _get_mls_team_record(fixture["home_team_id"], fixture["season"])
    fixture["away_team_record"] = _get_mls_team_record(fixture["away_team_id"], fixture["season"])

    fixture["home_team_stats"] = _get_mls_team_season_stats(fixture["home_name"])
    fixture["away_team_stats"] = _get_mls_team_season_stats(fixture["away_name"])

    fixture["home_power_rank"] = _get_mls_power_rank(fixture["home_name"])
    fixture["away_power_rank"] = _get_mls_power_rank(fixture["away_name"])

    # Goals/Goals Allowed per game — real observed averages from ESPN standings,
    # the same arithmetic WC uses for its own goals_per_game (see predictions.py's
    # get_attack_xg_ratings: gf/played, ga/played). MLS has no Dixon-Coles
    # attack_rating/xg_rating/xga_rating (that's WC's fitted Poisson model
    # re-expressed) — but it does have its own opponent-adjusted Attack/Defense
    # Rating from real xG data, folded into home/away_team_stats below (see
    # mls_team_stats.py's _compute_ratings) rather than reusing WC's field names.
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


def _get_mls_last10(team_id: int) -> list:
    """Team's last 10 finished matches, newest first — same shape/query as WC's fetch_last5,
    just against mls_fixtures/mls_teams and LIMIT 10 instead of 5. All 10 games already sit
    in the local DB (ESPN-sourced), so no external fetch/cache-fill step is needed here."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo, ht.abbreviation as home_code,
               at.name as away_name, at.logo as away_logo, at.abbreviation as away_code
        FROM mls_fixtures f
        JOIN mls_teams ht ON f.home_team_id = ht.id
        JOIN mls_teams at ON f.away_team_id = at.id
        WHERE (f.home_team_id = ? OR f.away_team_id = ?)
          AND f.status = 'FT'
        ORDER BY f.date_utc DESC
        LIMIT 10
    """, (team_id, team_id))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _get_mls_head_to_head(team_a_id: int, team_b_id: int, limit: int = 10) -> list:
    """Last N finished meetings between these two specific teams (either side home),
    newest first, across every season stored in mls_fixtures — not just the current
    one, since two teams often only meet once or twice a season (see
    scripts/backfill_mls_history.py, which backfilled 2023-2025 for exactly this)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*, ht.name as home_name, ht.logo as home_logo, ht.abbreviation as home_code,
               at.name as away_name, at.logo as away_logo, at.abbreviation as away_code
        FROM mls_fixtures f
        JOIN mls_teams ht ON f.home_team_id = ht.id
        JOIN mls_teams at ON f.away_team_id = at.id
        WHERE ((f.home_team_id = ? AND f.away_team_id = ?)
            OR (f.home_team_id = ? AND f.away_team_id = ?))
          AND f.status = 'FT'
        ORDER BY f.date_utc DESC
        LIMIT ?
    """, (team_a_id, team_b_id, team_b_id, team_a_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _record_from_rows(rows: list, is_home_col: str) -> dict:
    """W/D/L + points from a list of finished mls_fixtures rows, from the
    perspective of whichever side `is_home_col` says this team played."""
    won = drawn = lost = 0
    for r in rows:
        team_goals = r["home_score"] if is_home_col == "home" else r["away_score"]
        opp_goals = r["away_score"] if is_home_col == "home" else r["home_score"]
        if team_goals > opp_goals:
            won += 1
        elif team_goals == opp_goals:
            drawn += 1
        else:
            lost += 1
    return {"won": won, "drawn": drawn, "lost": lost, "played": won + drawn + lost, "points": won * 3 + drawn}


def _get_mls_team_record(team_id: int, season: int) -> dict:
    """Overall/home/away W-D-L + points for a team, computed directly from
    mls_fixtures (not mls_standings) so all three splits are guaranteed
    internally consistent (home + away always sums to all) — scoped to the
    fixture's own season so a mid-backfill history query never bleeds in."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT home_score, away_score FROM mls_fixtures
        WHERE home_team_id = ? AND season = ? AND status = 'FT'
    """, (team_id, season))
    home_rows = cur.fetchall()
    cur.execute("""
        SELECT home_score, away_score FROM mls_fixtures
        WHERE away_team_id = ? AND season = ? AND status = 'FT'
    """, (team_id, season))
    away_rows = cur.fetchall()
    conn.close()

    home_record = _record_from_rows(home_rows, "home")
    away_record = _record_from_rows(away_rows, "away")
    all_record = {
        "won": home_record["won"] + away_record["won"],
        "drawn": home_record["drawn"] + away_record["drawn"],
        "lost": home_record["lost"] + away_record["lost"],
        "played": home_record["played"] + away_record["played"],
        "points": home_record["points"] + away_record["points"],
    }
    return {"all": all_record, "home": home_record, "away": away_record}


def _get_mls_team_season_stats(team_name: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT corners, shots, fouls, xg, xga, attack_rating, defense_rating, attack_rank, defense_rank
           FROM mls_team_season_stats WHERE team_name = ?""",
        (team_name,),
    )
    row = cur.fetchone()
    conn.close()
    if not row or all(row[k] is None for k in row.keys()):
        return None
    return dict(row)


def _get_mls_power_rank(team_name: str) -> Optional[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT rank FROM mls_power_ratings WHERE team_name = ?", (team_name,))
    row = cur.fetchone()
    conn.close()
    return row["rank"] if row else None


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
