"""
Seed WC2026 data.

Two data sources:
  football-data.org  - live WC2026 fixtures, standings, squads (free, no daily cap)
  API-Football       - historical international results for model training
                       (free tier covers 2022-2024: WC2022, Euro2024, Copa America)

Usage:
  python scripts/seed_historical.py            # full seed (recommended)
  python scripts/seed_historical.py --csv results.csv  # also ingest Kaggle CSV
  python scripts/seed_historical.py --fixtures-only    # just fixtures/standings
"""
import sys
import os
import time
import argparse
import csv
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from app.database import init_db, get_connection, DB_PATH
from app.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Step 1: WC2026 live data via football-data.org
# ---------------------------------------------------------------------------

async def seed_wc2026_fixtures() -> bool:
    from app.services.football_data_org import fetch_and_store_fixtures, fetch_standings, fetch_teams

    if not settings.football_data_key:
        print("\n[!] FOOTBALL_DATA_KEY not set.")
        print("   Sign up free at https://www.football-data.org/client/register")
        print("   Add the token to backend/.env as FOOTBALL_DATA_KEY=your_token")
        print("   Then re-run this script.\n")
        return False

    print("-- Step 1: WC2026 fixtures (football-data.org) --")
    n = await fetch_and_store_fixtures()
    print(f"  {n} fixtures stored")

    ok = await fetch_standings()
    print(f"  Standings: {'OK' if ok else 'failed'}")

    teams = await fetch_teams()
    print(f"  {teams} teams + squads stored")

    return n > 0


# ---------------------------------------------------------------------------
# Step 2: Historical results for model training via API-Football (2022-2024)
# ---------------------------------------------------------------------------

TRAINING_COMPETITIONS = [
    # (league_id, season, label)
    (1,   2022, "FIFA World Cup 2022"),
    (4,   2024, "UEFA Euro 2024"),
    (9,   2024, "CONMEBOL Copa America 2024"),
    (1,   2018, "FIFA World Cup 2018"),
]

async def seed_training_data():
    from app.services.api_football import _get as api_get

    if not settings.api_football_key:
        print("\n[!] API_FOOTBALL_KEY not set -- skipping historical training data")
        return

    print("\n-- Step 2: Historical training data (API-Football) --")
    conn = get_connection()
    cur = conn.cursor()
    total = 0

    for league_id, season, label in TRAINING_COMPETITIONS:
        data = await api_get("fixtures", {"league": league_id, "season": season, "status": "FT"})
        if not data:
            print(f"  {label}: no data returned (check API quota)")
            continue

        matches = data.get("response", [])
        count = 0
        now = time.time()

        for f in matches:
            goals = f.get("goals", {})
            if goals.get("home") is None or goals.get("away") is None:
                continue

            ts = f["fixture"].get("timestamp", 0)
            days_ago = (now - ts) / 86400
            home_name = f["teams"]["home"]["name"]
            away_name = f["teams"]["away"]["name"]

            cur.execute("""
                INSERT OR IGNORE INTO historical_results
                (match_date, home_team, away_team, home_goals, away_goals,
                 tournament, neutral, days_ago)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                f["fixture"].get("date", ""),
                home_name, away_name,
                int(goals["home"]), int(goals["away"]),
                label, days_ago,
            ))
            count += 1

        conn.commit()
        total += count
        print(f"  {label}: {count} matches")
        await asyncio.sleep(1.2)  # stay under 1 req/sec to protect free quota

    conn.close()
    print(f"  Total training matches stored: {total}")


# ---------------------------------------------------------------------------
# Step 3: Seed from Kaggle CSV (optional)
# ---------------------------------------------------------------------------

def seed_from_csv(csv_path: str) -> int:
    """
    Kaggle 'International Football Results 1872-present' CSV.
    Columns: date,home_team,away_team,home_score,away_score,tournament,city,country,neutral
    """
    conn = get_connection()
    cur = conn.cursor()
    now_dt = datetime.now()
    count = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                match_dt = datetime.strptime(row["date"], "%Y-%m-%d")
                days_ago = (now_dt - match_dt).days
                if days_ago > 365 * 6:          # only last 6 years
                    continue
                cur.execute("""
                    INSERT OR IGNORE INTO historical_results
                    (match_date, home_team, away_team, home_goals, away_goals,
                     tournament, neutral, days_ago)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row["date"],
                    row["home_team"], row["away_team"],
                    int(row["home_score"]), int(row["away_score"]),
                    row.get("tournament", ""),
                    1 if row.get("neutral") == "True" else 0,
                    days_ago,
                ))
                count += 1
            except (ValueError, KeyError):
                continue

    conn.commit()
    conn.close()
    return count


# ---------------------------------------------------------------------------
# Step 4: Fit the prediction model
# ---------------------------------------------------------------------------

async def fit_prediction_model():
    from app.services.predictions import load_historical_from_db, fit_model

    print("\n-- Step 3: Fitting Dixon-Coles prediction model --")
    matches = load_historical_from_db()
    print(f"  {len(matches)} historical matches available")

    if len(matches) < 20:
        print("  Not enough data to fit model - add more training data")
        return

    result = fit_model(matches)
    if result:
        print(f"  Model fitted: {len(result['teams'])} teams, {result['n_matches']} matches used")
    else:
        print("  Model fit failed")


# ---------------------------------------------------------------------------
# Step 5: Run Monte Carlo simulation
# ---------------------------------------------------------------------------

async def run_monte_carlo():
    from app.services.monte_carlo import simulate_tournament, store_advancement_probs

    print("\n-- Step 4: Monte Carlo advancement simulation --")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, group_letter FROM teams WHERE group_letter IS NOT NULL")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("  No teams with group assignments - skipping (run after standings are seeded)")
        return

    groups: dict = {}
    team_name_to_id: dict = {}
    for row in rows:
        g = row["group_letter"]
        if g not in groups:
            groups[g] = []
        groups[g].append(row["name"])
        team_name_to_id[row["name"]] = row["id"]

    print(f"  Simulating {len(groups)} groups x 10,000 tournaments...")
    probs = simulate_tournament(groups, n_sims=10000)
    store_advancement_probs(probs, team_name_to_id)
    print(f"  Done - {len(probs)} teams with advancement probabilities")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(args):
    init_db()
    print(f"Database: {DB_PATH}\n")

    if args.csv:
        if not Path(args.csv).exists():
            print(f"CSV not found: {args.csv}")
            sys.exit(1)
        n = seed_from_csv(args.csv)
        print(f"Seeded {n} matches from CSV")

    if not args.model_only:
        ok = await seed_wc2026_fixtures()
        if not ok and not args.fixtures_only:
            print("Continuing without WC2026 live data - model will use historical data only")

    if not args.fixtures_only:
        if not args.model_only:
            await seed_training_data()
        await fit_prediction_model()
        await run_monte_carlo()

    print("\n[OK] Seed complete. Start the server with:")
    print("  uvicorn app.main:app --reload")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv",           help="Path to Kaggle results CSV")
    parser.add_argument("--fixtures-only", action="store_true", help="Only seed WC2026 fixtures/standings")
    parser.add_argument("--model-only",    action="store_true", help="Only refit model + MC (no API calls)")
    args = parser.parse_args()

    asyncio.run(main(args))
