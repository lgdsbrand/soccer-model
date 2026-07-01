from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

from app.config import get_settings
from app.database import init_db
from app.routers import fixtures, standings, predictions, teams, insights
from app.services import football_data_org

settings = get_settings()
scheduler = AsyncIOScheduler()


def _run_monte_carlo_sync():
    """Run Monte Carlo simulation synchronously (called from thread executor)."""
    from app.database import get_connection
    from app.services.monte_carlo import simulate_tournament, store_advancement_probs

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, group_letter FROM teams WHERE group_letter IS NOT NULL")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return

    groups: dict = {}
    team_name_to_id: dict = {}
    for row in rows:
        g = row["group_letter"]
        if g not in groups:
            groups[g] = []
        groups[g].append(row["name"])
        team_name_to_id[row["name"]] = row["id"]

    probs = simulate_tournament(groups, n_sims=10000)
    store_advancement_probs(probs, team_name_to_id)
    print(f"Monte Carlo complete — {len(probs)} teams updated")



async def _refresh_data():
    """Hourly job: fetch live data, re-run Monte Carlo if standings changed, sync goals."""
    from app.services.openfootball import sync_goal_scorers
    from scripts.backfill_api_football_ids import sync_api_football_ids

    await football_data_org.fetch_and_store_fixtures()
    standings_changed = await football_data_org.fetch_standings()

    # Sync real goal scorer data from openfootball (fast, no rate limit)
    await sync_goal_scorers()

    # Sync API-Football fixture IDs for stats (sliding 3-day window)
    await sync_api_football_ids()

    if not standings_changed:
        return

    # Check whether standings are newer than the last MC run
    from app.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT MAX(updated_at) as last_standings FROM standings")
    last_standings = (cur.fetchone()["last_standings"] or 0)
    cur.execute("SELECT MIN(computed_at) as last_mc FROM advancement_probs")
    last_mc = (cur.fetchone()["last_mc"] or 0)
    conn.close()

    if last_standings <= last_mc:
        return

    print("Standings updated — re-running Monte Carlo simulation...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_monte_carlo_sync)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("Database initialized")

    scheduler.add_job(_refresh_data, "interval", hours=1, id="refresh_data")
    scheduler.start()
    print("Scheduler started (hourly refresh + conditional Monte Carlo)")

    # Initial data load + goal scorer sync (non-blocking)
    asyncio.create_task(_initial_seed())
    asyncio.create_task(_sync_goals_on_startup())

    yield

    # Shutdown
    scheduler.shutdown()


async def _sync_goals_on_startup():
    """Sync real goal scorer data from openfootball on every startup."""
    from app.services.openfootball import sync_goal_scorers
    matched = await sync_goal_scorers()
    print(f"Goal scorer sync complete — {matched} players updated")


async def _initial_seed():
    """Refresh fixtures and standings on every startup."""
    print("Startup refresh: fetching fixtures from football-data.org...")
    n = await football_data_org.fetch_and_store_fixtures()
    print(f"Startup refresh: {n} fixtures synced")
    await football_data_org.fetch_standings()
    print("Startup refresh: standings synced")


app = FastAPI(
    title="WC2026 Prediction API",
    description="World Cup 2026 match predictions and statistics",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins = (
    ["*"]
    if settings.app_env == "production"
    else [settings.frontend_url, "http://localhost:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=settings.app_env != "production",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fixtures.router)
app.include_router(standings.router)
app.include_router(predictions.router)
app.include_router(teams.router)
app.include_router(insights.router)


@app.get("/")
async def root():
    return {
        "service": "WC2026 Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    from app.database import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as fixtures FROM fixtures")
    fixtures_count = cur.fetchone()["fixtures"]
    cur.execute("SELECT COUNT(*) as teams FROM teams")
    teams_count = cur.fetchone()["teams"]
    conn.close()
    return {
        "status": "ok",
        "fixtures": fixtures_count,
        "teams": teams_count,
    }


@app.get("/api-status")
async def api_status():
    """Check football-data.org connectivity."""
    n = await football_data_org.fetch_and_store_fixtures()
    return {"source": "football-data.org", "fixtures_synced": n}
