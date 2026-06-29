from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.database import get_connection
from app.services.predictions import compute_and_store_prediction, load_historical_from_db, fit_model
from app.services.monte_carlo import simulate_tournament, store_advancement_probs, load_advancement_probs

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/fixture/{fixture_id}", response_model=dict)
async def get_fixture_prediction(fixture_id: int):
    """Get prediction for a specific fixture."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, f.home_team_id, f.away_team_id,
               ht.name as home_name, at.name as away_name
        FROM predictions p
        JOIN fixtures f ON p.fixture_id = f.id
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE p.fixture_id = ?
    """, (fixture_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        return dict(row)

    # Compute on demand
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.*, ht.name as home_name, at.name as away_name
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.id = ?
    """, (fixture_id,))
    fix = cur.fetchone()
    conn.close()

    if not fix:
        raise HTTPException(status_code=404, detail="Fixture not found")

    pred = compute_and_store_prediction(fixture_id, fix["home_name"], fix["away_name"])
    pred["fixture_id"] = fixture_id
    return pred


@router.get("/advancement", response_model=List[dict])
async def get_advancement_probabilities():
    """Get tournament advancement probabilities for all teams."""
    return load_advancement_probs()


@router.post("/refit-model", response_model=dict)
async def refit_model(background_tasks: BackgroundTasks):
    """Trigger model refit in background."""
    background_tasks.add_task(_run_model_fit)
    return {"status": "Model refit queued"}


@router.post("/run-monte-carlo", response_model=dict)
async def run_monte_carlo(background_tasks: BackgroundTasks):
    """Run Monte Carlo tournament simulation in background."""
    background_tasks.add_task(_run_monte_carlo)
    return {"status": "Monte Carlo simulation queued"}


@router.get("/tournament-winners", response_model=List[dict])
async def get_tournament_winners():
    """Get teams ranked by tournament win probability."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ap.winner_pct, ap.final_pct, ap.sf_pct,
               t.id as team_id, t.name as team_name, t.logo, t.group_letter
        FROM advancement_probs ap
        JOIN teams t ON ap.team_id = t.id
        ORDER BY ap.winner_pct DESC
        LIMIT 16
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


async def _run_model_fit():
    """Fit Dixon-Coles model from historical data in DB."""
    matches = load_historical_from_db()
    if len(matches) < 20:
        print(f"Not enough historical data: {len(matches)} matches")
        return
    result = fit_model(matches)
    if result:
        print(f"Model fitted on {result['n_matches']} matches, {len(result['teams'])} teams")
    else:
        print("Model fit failed")


async def _run_monte_carlo():
    """Run MC simulation and store results."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, group_letter FROM teams WHERE group_letter IS NOT NULL")
    team_rows = cur.fetchall()
    conn.close()

    if not team_rows:
        print("No teams with group assignments found")
        return

    groups = {}
    team_name_to_id = {}
    for row in team_rows:
        g = row["group_letter"]
        if g not in groups:
            groups[g] = []
        groups[g].append(row["name"])
        team_name_to_id[row["name"]] = row["id"]

    probs = simulate_tournament(groups)
    if probs:
        store_advancement_probs(probs, team_name_to_id)
        print(f"Monte Carlo complete: {len(probs)} teams")
