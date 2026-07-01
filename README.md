# WC2026 Predictor

FIFA World Cup 2026 prediction and statistics web app.

## Stack
- **Backend**: FastAPI (Python 3.11), SQLite, APScheduler
- **Frontend**: Next.js 16, Tailwind CSS, Recharts
- **Statistical model**: Dixon-Coles Poisson model + Monte Carlo simulation
- **AI**: Groq (Llama) + Google GenAI (Gemini)
- **Data**: API-Football (free: 100 req/day), OpenWeatherMap (free: 1000/day)
- **Plays**: Tavily web search → Groq synthesis

---

## 1. Get Your API Keys

The backend needs 5 free-tier API keys. None of these require a credit card. Budget about 15 minutes to sign up for all of them.

| # | Service | What it's used for | Free tier limit | Sign up |
|---|---------|--------------------|-------------------|---------|
| 1 | **API-Football** | Player lineups, last-5 match stats | 100 requests/day | [dashboard.api-football.com](https://dashboard.api-football.com) → Register → copy the key from your dashboard |
| 2 | **football-data.org** | Live WC2026 fixtures, standings, teams | No daily cap | [football-data.org/client/register](https://www.football-data.org/client/register) → confirm via email → key is emailed to you |
| 3 | **OpenWeatherMap** | Match-day weather by venue | 1,000 calls/day | [openweathermap.org/api](https://openweathermap.org/api) → sign up → API keys tab (can take up to 2 hours to activate after signup) |
| 4 | **Tavily** | Live news search for injury/lineup context | 1,000 searches/month | [tavily.com](https://tavily.com) → sign up → key shown on your dashboard immediately |
| 5 | **Groq** | Fast/cheap LLM calls (style of play, lineups, recommended plays) | Generous free tier | [console.groq.com](https://console.groq.com) → sign up → API Keys → Create Key |
| 6 | **Google GenAI (Gemini)** | Primary AI match analysis (Groq is the fallback) | Free tier | [aistudio.google.com](https://aistudio.google.com) → Get API Key → Create API key |

Keep all 6 values somewhere safe (a password manager, not a text file that could get committed) — you'll paste each one into two places: your local `.env` file (step 2) and your Render dashboard (step 3).

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
# Open .env and paste in the 6 keys from step 1

# Seed initial data (uses ~60 API-Football calls)
python scripts/seed_historical.py --api

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
3. Paste the same 6 keys from step 1 into the environment variable fields it prompts for
4. Deploy — copy the resulting URL (e.g. `https://your-service.onrender.com`) once it's live

**Free tier note:** Render's free web services sleep after 15 minutes idle and take ~30-60s to wake on the next request.

### Frontend → Vercel

1. [vercel.com/new](https://vercel.com/new) → log in with GitHub → import this repo
2. Set **Root Directory** to `frontend`
3. Add environment variable `NEXT_PUBLIC_API_URL` = your Render URL from above
4. Deploy

### After both are live

- No CORS setup needed — the backend allows all origins automatically when `APP_ENV=production` (set in `render.yaml`)
- Run `python scripts/seed_historical.py --api` once against production if the deployed database needs seeding from scratch

---

## Key Endpoints

```
GET /                        — Health check
GET /fixtures/               — All WC2026 fixtures
GET /fixtures/today          — Today's matches
GET /fixtures/{id}           — Full match card (weather, lineups, prediction, AI analysis)
GET /standings/groups        — Group standings
GET /standings/bracket       — Knockout stage fixtures
GET /teams/                  — All teams
GET /teams/{id}               — Team detail + squad + style of play
GET /predictions/advancement — Tournament advancement probabilities
POST /predictions/run-monte-carlo — Trigger simulation (background)
POST /predictions/refit-model    — Refit Dixon-Coles model (background)
GET /insights/home           — Homepage aggregate data
```

## Prediction Model

**Dixon-Coles Poisson model** with exponential time decay (λ=0.0065):
- Fits per-team attack/defense strength parameters
- Derives win/draw/loss, BTTS, O1.5, O2.5 probabilities
- 10,000 Monte Carlo simulations for advancement probabilities

**Expected accuracy**: ~54-57% on 3-outcome predictions (baseline: 33%)
