# WC2026 Predictor

Prediction and statistics dashboard covering two competitions:
- **FIFA World Cup 2026** — Dixon-Coles/Monte Carlo win probabilities, group/knockout advancement odds, AI match analysis.
- **MLS** — live fixtures, standings, odds-derived match probabilities, opponent-adjusted Attack/Defense ratings, head-to-head history, and more.

Both sections share one Next.js frontend and one FastAPI backend, but MLS runs on its own isolated set of `mls_*` database tables and data sources — nothing about it touches or risks the World Cup data/model.

## Features

**World Cup**
- Group stage & knockout bracket with live win/draw/loss and advancement probabilities (Dixon-Coles Poisson model + 10,000-run Monte Carlo simulation)
- Match detail pages: team form, head-to-head, lineups, AI-generated match analysis/style-of-play/key-players, match-day weather
- AI-synthesized "recommended plays" from live news search

**MLS**
- Dashboard, schedule, and Eastern/Western conference standings from live ESPN data
- Match detail pages: odds-derived win/draw/BTTS/goals-total probabilities, last-10 form, head-to-head history, season W-D-L records, scoring trends, opponent-adjusted Attack/Defense Strength (1-30 ranked), power ranking, match-day weather
- "Top Plays" carousel — best BTTS/O1.5/O2.5 matches across the next ~2 weeks
- Fully responsive, verified on mobile

## Stack
- **Backend**: FastAPI (Python 3.11), SQLite, APScheduler
- **Frontend**: Next.js 16, Tailwind CSS, Recharts
- **Statistical model**: Dixon-Coles Poisson model + Monte Carlo simulation (World Cup only — MLS uses odds-derived probabilities + an opponent-adjusted xG rating instead)
- **AI**: Groq (Llama) + Google GenAI (Gemini)
- **Data — World Cup**: API-Football (free: 100 req/day), football-data.org, OpenWeatherMap (free: 1000/day)
- **Data — MLS**: ESPN public API (teams/fixtures/standings, no key needed), The Odds API (match odds), FotMob (season stats/xG, no key needed)
- **Plays**: Tavily web search → Groq synthesis

---

## 1. Get Your API Keys

The backend needs 7 free/paid-tier API keys. Budget about 15-20 minutes to sign up for all of them.

| # | Service | What it's used for | Tier | Sign up |
|---|---------|--------------------|-------------------|---------|
| 1 | **API-Football** | Player lineups, last-5 match stats (World Cup) | Free: 100 requests/day | [dashboard.api-football.com](https://dashboard.api-football.com) → Register → copy the key from your dashboard |
| 2 | **football-data.org** | Live WC2026 fixtures, standings, teams | Free, no daily cap | [football-data.org/client/register](https://www.football-data.org/client/register) → confirm via email → key is emailed to you |
| 3 | **OpenWeatherMap** | Match-day weather by venue (both competitions) | Free: 1,000 calls/day | [openweathermap.org/api](https://openweathermap.org/api) → sign up → API keys tab (can take up to 2 hours to activate after signup) |
| 4 | **Tavily** | Live news search for injury/lineup context | Free: 1,000 searches/month | [tavily.com](https://tavily.com) → sign up → key shown on your dashboard immediately |
| 5 | **Groq** | Fast/cheap LLM calls (style of play, lineups, recommended plays) | Generous free tier | [console.groq.com](https://console.groq.com) → sign up → API Keys → Create Key |
| 6 | **Google GenAI (Gemini)** | Primary AI match analysis (Groq is the fallback) | Free tier | [aistudio.google.com](https://aistudio.google.com) → Get API Key → Create API key |
| 7 | **The Odds API** | MLS match odds (win/draw/loss, BTTS, goals totals) | Paid, Professional tier used in production (~1,900 calls/month at current refresh cadence) | [the-odds-api.com](https://the-odds-api.com) → sign up → key shown on your dashboard |

MLS's other two data sources (ESPN, FotMob) are public endpoints and need no key or signup.

Keep all 7 values somewhere safe (a password manager, not a text file that could get committed) — you'll paste each one into two places: your local `.env` file (step 2) and your Render dashboard (step 3).

---

## 2. Local Development Setup

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Open .env and paste in the 7 keys from step 1

# Seed initial World Cup data (uses ~60 API-Football calls)
python scripts/seed_historical.py --api
# MLS data (teams/fixtures/standings/odds) seeds itself automatically on server startup — no separate script needed

# Start server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Leave NEXT_PUBLIC_API_URL as http://localhost:8000 for local dev

npm run dev
```

Frontend runs at: http://localhost:3000

---

## 3. Production Deployment

Two separate services, deployed independently:

### Backend → Render

1. [dashboard.render.com](https://dashboard.render.com) → log in with GitHub → **New +** → **Blueprint**
2. Select this repo (grant Render access if it's private) — it auto-detects `render.yaml`
3. Paste the same 7 keys from step 1 into the environment variable fields it prompts for (`ODDS_API_KEY` isn't listed in `render.yaml` itself — add it manually as an env var in the Render dashboard, same as the others)
4. Deploy — copy the resulting URL (e.g. `https://your-service.onrender.com`) once it's live

**Free tier note:** Render's free web services sleep after 15 minutes idle and take ~30-60s to wake on the next request. This also stops the hourly data-refresh scheduler from running while asleep, so a GitHub Actions workflow (`.github/workflows/keepalive.yml`) pings `/health` every 10 minutes to keep it awake — no setup needed, it runs automatically once this repo is on GitHub. If you ever change the backend's URL, update the URL in that workflow file to match.

### Frontend → Vercel

1. [vercel.com/new](https://vercel.com/new) → log in with GitHub → import this repo
2. Set **Root Directory** to `frontend`
3. Add environment variable `NEXT_PUBLIC_API_URL` = your Render URL from above
4. Deploy

### After both are live

- No CORS setup needed — the backend allows all origins automatically when `APP_ENV=production` (set in `render.yaml`)
- Run `python scripts/seed_historical.py --api` once against production if the deployed database needs seeding from scratch

---

## Prediction Model

**World Cup — Dixon-Coles Poisson model** with exponential time decay (λ=0.0065):
- Fits per-team attack/defense strength parameters
- Derives win/draw/loss, BTTS, O1.5, O2.5 probabilities
- 10,000 Monte Carlo simulations for advancement probabilities
- **Expected accuracy**: ~54-57% on 3-outcome predictions (baseline: 33%)

**MLS — odds-derived probabilities + opponent-adjusted rating**:
- Win/draw/loss, BTTS, and O1.5/O2.5/O3.5 goals-total probabilities are devigged directly from live bookmaker odds (The Odds API), not a fitted model
- Attack/Defense Strength (ranked 1-30) is computed from each team's real FotMob season xG/xGA, adjusted against the actual strength of opponents faced so far this season

## Project History

`MLS_BUILD_STATUS.md` in this repo has a full day-by-day build log of the MLS section — useful background if extending it further.
