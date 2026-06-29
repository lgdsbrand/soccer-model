# WC2026 Predictor

FIFA World Cup 2026 prediction and statistics web app.

## Stack
- **Backend**: FastAPI (Python 3.12), SQLite, APScheduler
- **Frontend**: Next.js 15, Tailwind CSS, Recharts
- **Statistical model**: Dixon-Coles Poisson model + Monte Carlo simulation
- **AI**: Groq (Llama) + Google GenAI (Gemini)
- **Data**: API-Football (free: 100 req/day), OpenWeatherMap (free: 1000/day)
- **Plays**: Tavily web search → Groq synthesis

## Setup

### 1. Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your API keys

# Seed initial data (uses ~60 API-Football calls)
python scripts/seed_historical.py --api

# Start server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit NEXT_PUBLIC_API_URL if needed

npm run dev
```

Frontend runs at: http://localhost:3000

## API Keys Required

| Service | Free Tier | Where to Get |
|---------|-----------|-------------|
| API-Football | 100 req/day | https://dashboard.api-football.com |
| OpenWeatherMap | 1,000/day | https://openweathermap.org/api |
| Tavily | 1,000/month | https://tavily.com |
| Groq | Very cheap | https://console.groq.com |
| Google GenAI | Free tier | https://aistudio.google.com |

## Key Endpoints

```
GET /                        — Health check
GET /fixtures/               — All WC2026 fixtures
GET /fixtures/today          — Today's matches
GET /fixtures/{id}           — Full match card (weather, lineups, prediction, AI analysis)
GET /standings/groups        — Group standings
GET /standings/bracket       — Knockout stage fixtures
GET /teams/                  — All teams
GET /teams/{id}              — Team detail + squad + style of play
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

## Handoff to Tyler's Team

1. Clone repo
2. `cp backend/.env.example backend/.env` and fill in their keys
3. `cp frontend/.env.local.example frontend/.env.local` and set production backend URL
4. Deploy frontend to Vercel
5. Deploy backend to Railway/Fly.io
6. Run `python scripts/seed_historical.py --api` once to populate data
