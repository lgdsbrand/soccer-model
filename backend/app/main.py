from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

from app.config import get_settings
from app.database import init_db
from app.routers import fixtures, standings, predictions, teams, insights, team_stats
from app.services import football_data_org
from app.mls.database import init_mls_db
from app.mls.services import mls_source, odds_api, mls_team_stats
from app.mls.routers import fixtures as mls_fixtures, standings as mls_standings

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
    """Hourly job: fetch live data, re-run Monte Carlo, sync goals."""
    from app.services.openfootball import sync_goal_scorers
    from scripts.backfill_api_football_ids import sync_api_football_ids

    await football_data_org.fetch_and_store_fixtures()
    await football_data_org.fetch_standings()

    # Sync real goal scorer data from openfootball (fast, no rate limit)
    await sync_goal_scorers()

    # Sync API-Football fixture IDs for stats (sliding 3-day window)
    await sync_api_football_ids()

    # Always re-run — previously gated on "did group standings change," which
    # permanently stops being true once the group stage ends, so eliminated
    # knockout teams (e.g. Japan losing in the Round of 32) kept showing their
    # stale pre-elimination advancement odds indefinitely. This is a cheap,
    # local, ~60s computation with no external API calls, so there's no real
    # cost to just always running it hourly instead of trying to detect
    # exactly which kind of result changed.
    print("Re-running Monte Carlo simulation...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_monte_carlo_sync)


async def _refresh_mls_data():
    """Every-12h job: fetch MLS fixtures/standings (ESPN) and refresh odds-derived match probs.

    Runs less often than the WC refresh (hourly) specifically to bound The
    Odds API credit spend: every refresh now costs 1 bulk call (h2h+totals)
    plus 1 per-event call for btts (~30 MLS fixtures/slate), so hourly would
    run ~31 calls/hour ≈ 22k/month — 12h cuts that to ~1,900/month, well
    inside quota. See MLS_BUILD_STATUS.md.
    """
    n = await mls_source.fetch_and_store_teams_and_fixtures()
    await mls_source.fetch_standings()
    written, unmatched = await odds_api.fetch_and_store_match_probs()
    stats_n = await mls_team_stats.refresh_all_team_stats()
    print(f"MLS refresh: {n} fixtures synced, {written} match-prob rows written, "
          f"{stats_n} team stats updated"
          + (f", {len(unmatched)} unmatched odds team name(s)" if unmatched else ""))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    init_mls_db()
    print("Database initialized")

    scheduler.add_job(_refresh_data, "interval", hours=1, id="refresh_data")
    scheduler.add_job(_refresh_mls_data, "interval", hours=12, id="refresh_mls_data")
    scheduler.start()
    print("Scheduler started (WC hourly, MLS every 12h + conditional Monte Carlo)")

    # Initial data load + goal scorer sync (non-blocking)
    asyncio.create_task(_initial_seed())
    asyncio.create_task(_initial_seed_mls())
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
    """
    Refresh fixtures, standings, and tournament winner odds on every startup.

    Monte Carlo used to only re-run from the hourly scheduler job, which
    doesn't fire until an hour after the process starts. On Render's free
    plan the service spins down after ~15 min idle, so a cold start would
    refresh fixtures/standings immediately but never live long enough to
    reach that first hourly tick — leaving advancement_probs (the
    "tournament winner" odds) frozen on whatever was last computed, even as
    fixtures kept moving further ahead. Running it here too means every
    cold start recomputes odds against the data it just fetched.
    """
    print("Startup refresh: fetching fixtures from football-data.org...")
    n = await football_data_org.fetch_and_store_fixtures()
    print(f"Startup refresh: {n} fixtures synced")
    await football_data_org.fetch_standings()
    print("Startup refresh: standings synced")

    print("Startup refresh: re-running Monte Carlo simulation...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_monte_carlo_sync)
    print("Startup refresh: Monte Carlo complete")


async def _initial_seed_mls():
    """
    MLS equivalent of _initial_seed() — same cold-start reasoning applies:
    on Render's free plan the scheduled job (every 12h) may never fire before
    the service spins back down, so refresh on every startup too. Note this
    means actual Odds API call frequency tracks how often the service cold
    starts, not strictly the 12h interval — see MLS_BUILD_STATUS.md.
    """
    print("Startup refresh: fetching MLS fixtures/standings from ESPN...")
    await _refresh_mls_data()
    print("Startup refresh: MLS data synced")


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
app.include_router(team_stats.router)
app.include_router(mls_fixtures.router)
app.include_router(mls_standings.router)


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
