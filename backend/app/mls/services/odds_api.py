"""
The Odds API client — MLS win/draw/loss, BTTS, and Over 2.5/3.5 probabilities.

No Dixon-Coles model needed for MLS: the client's Odds API Professional tier
exposes h2h, totals, and btts markets, so every percentage the frontend needs
is derived straight from bookmaker prices (devigged), not fitted from
historical results.

Verified live 2026-07-20 against a real key:
- h2h + totals come back on the bulk `/sports/{sport}/odds` call (one request
  for the whole slate). `btts` does NOT — the bulk endpoint 422s with
  INVALID_MARKET if you ask for it there; The Odds API only serves btts
  through the per-event `/sports/{sport}/events/{id}/odds` endpoint. So this
  fetches btts with one extra call per matched fixture. Refresh is every 12h
  (not hourly) specifically to keep that bounded — see main.py.
- The bulk `totals` market only ever carries each bookmaker's single "main"
  line for a given fixture (observed points across a full slate: 2.5, 2.75,
  3.0, 3.25, 3.5, 3.75 — MLS averages ~3 goals/game, so books split roughly
  evenly between quoting 2.5-ish and 3.5-ish as their main line). That's why
  a fixture often has only one of over_2_5_pct/over_3_5_pct from that source
  alone, and why it never has 1.5 at all — 1.5 isn't a main line anyone
  quotes for MLS.
- 1.5 (and full coverage of 2.5/3.5) DOES exist, just on a different market:
  `alternate_totals`, same per-event-only restriction as btts (422s on the
  bulk endpoint). Verified live 2026-07-23: betmgm, fanduel, and betrivers
  each quote 1.5/2.5/3.5 (plus 0.5, 4.5, 5.5...) via alternate_totals on
  every fixture in a full slate — no region change needed, region=us alone
  has it. So this fetches alternate_totals with one extra call per matched
  fixture (same shape as the btts call) and merges those samples in with
  whatever the bulk totals market found, giving every fixture all three of
  over_1_5_pct/over_2_5_pct/over_3_5_pct instead of at most one of the
  latter two. Unrelated to the World Cup's own over_1_5_pct (Dixon-Coles-
  derived, in the separate `predictions` table).

The team-name alias dict below is a best-effort seed for known MLS naming
mismatches between bookmaker feeds and ESPN's team names; extend it if a
live run logs unmatched names (see `_unmatched` below).
"""
import httpx
from typing import Dict, List, Optional, Tuple
from app.config import get_settings
from app.mls.database import get_connection

settings = get_settings()

# Bookmaker team names vs ESPN team names (mls_teams.name) — same pattern as
# predictions.py's TEAM_NAME_ALIASES / fotmob_team_stats.py's
# FOTMOB_NAME_TO_DB_NAME / tavily_odds.py's _ALIASES. Verified 2026-07-20
# against a real live Odds API slate (30 fixtures) — every entry below is a
# confirmed mismatch from that run, not a guess.
ODDS_API_NAME_ALIASES: Dict[str, str] = {
    "Los Angeles FC": "LAFC",
    "Inter Miami": "Inter Miami CF",
    "St. Louis City SC": "St. Louis CITY SC",
    "Vancouver Whitecaps FC": "Vancouver Whitecaps",
    "Chicago Fire": "Chicago Fire FC",
    "Columbus Crew SC": "Columbus Crew",
    "CF Montreal": "CF Montréal",
    "Houston Dynamo": "Houston Dynamo FC",
}


def _resolve_team_name(cur, odds_api_name: str) -> Optional[int]:
    """Match an Odds API team name to an mls_teams.id, exact match first, then alias."""
    cur.execute("SELECT id FROM mls_teams WHERE name = ?", (odds_api_name,))
    row = cur.fetchone()
    if row:
        return row["id"]

    aliased = ODDS_API_NAME_ALIASES.get(odds_api_name)
    if aliased:
        cur.execute("SELECT id FROM mls_teams WHERE name = ?", (aliased,))
        row = cur.fetchone()
        if row:
            return row["id"]

    return None


def _devig(prices: Dict[str, float]) -> Dict[str, float]:
    """Convert decimal odds to devigged (vig-removed) implied probabilities summing to 1."""
    implied = {name: 1.0 / price for name, price in prices.items() if price and price > 0}
    total = sum(implied.values())
    if total <= 0:
        return {}
    return {name: p / total for name, p in implied.items()}


def _match_probs_from_event(event: Dict) -> Optional[Dict]:
    """
    Aggregate all bookmakers on one event into a single set of percentages.
    Averages the devigged probability across every bookmaker that offers
    each market — more stable than trusting a single book, and tolerant of
    books that only carry a subset of markets (e.g. no btts).
    """
    home_team = event.get("home_team")
    away_team = event.get("away_team")
    if not home_team or not away_team:
        return None

    h2h_samples: List[Dict[str, float]] = []
    over_1_5_samples: List[float] = []
    over_2_5_samples: List[float] = []
    over_3_5_samples: List[float] = []
    btts_samples: List[float] = []

    for bookmaker in event.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            if key == "h2h":
                prices = {o["name"]: o["price"] for o in outcomes if "price" in o}
                devigged = _devig(prices)
                if devigged:
                    h2h_samples.append(devigged)

            elif key in ("totals", "alternate_totals"):
                by_point: Dict[float, Dict[str, float]] = {}
                for o in outcomes:
                    point = o.get("point")
                    if point is None:
                        continue
                    by_point.setdefault(point, {})[o["name"]] = o.get("price")
                for point, prices in by_point.items():
                    devigged = _devig(prices)
                    over_p = devigged.get("Over")
                    if over_p is None:
                        continue
                    if point == 1.5:
                        over_1_5_samples.append(over_p)
                    elif point == 2.5:
                        over_2_5_samples.append(over_p)
                    elif point == 3.5:
                        over_3_5_samples.append(over_p)

            elif key == "btts":
                prices = {o["name"]: o["price"] for o in outcomes if "price" in o}
                devigged = _devig(prices)
                yes_p = devigged.get("Yes")
                if yes_p is not None:
                    btts_samples.append(yes_p)

    if not h2h_samples:
        return None

    def _avg(key: str, samples: List[Dict[str, float]]) -> float:
        vals = [s[key] for s in samples if key in s]
        return sum(vals) / len(vals) if vals else 0.0

    home_win = _avg(home_team, h2h_samples)
    away_win = _avg(away_team, h2h_samples)
    draw = _avg("Draw", h2h_samples)
    # Renormalize in case a book was missing one side of the three-way market
    total = home_win + away_win + draw
    if total > 0:
        home_win, away_win, draw = home_win / total, away_win / total, draw / total

    return {
        "home_win_pct": round(home_win * 100, 1),
        "draw_pct": round(draw * 100, 1),
        "away_win_pct": round(away_win * 100, 1),
        "over_1_5_pct": round(sum(over_1_5_samples) / len(over_1_5_samples) * 100, 1) if over_1_5_samples else None,
        "over_2_5_pct": round(sum(over_2_5_samples) / len(over_2_5_samples) * 100, 1) if over_2_5_samples else None,
        "over_3_5_pct": round(sum(over_3_5_samples) / len(over_3_5_samples) * 100, 1) if over_3_5_samples else None,
        "btts_pct": round(sum(btts_samples) / len(btts_samples) * 100, 1) if btts_samples else None,
        "bookmaker_count": len(event.get("bookmakers", [])),
    }


async def _fetch_btts_bookmakers(client: httpx.AsyncClient, event_id: str) -> List[Dict]:
    """Per-event call — the bulk /odds endpoint 422s (INVALID_MARKET) if btts is requested there."""
    try:
        resp = await client.get(
            f"{settings.odds_api_base}/sports/{settings.odds_api_sport_key}/events/{event_id}/odds",
            params={
                "apiKey": settings.odds_api_key,
                "regions": "us",
                "markets": "btts",
                "oddsFormat": "decimal",
            },
        )
        resp.raise_for_status()
        return resp.json().get("bookmakers", [])
    except Exception as e:
        print(f"The Odds API error (btts, event {event_id}): {e}")
        return []


async def _fetch_alternate_totals_bookmakers(client: httpx.AsyncClient, event_id: str) -> List[Dict]:
    """Per-event call — same INVALID_MARKET restriction as btts. This is where the 1.5 line
    (and full 2.5/3.5 coverage) actually lives; the bulk `totals` market only has each
    bookmaker's single main line, which is rarely 1.5 — see module docstring."""
    try:
        resp = await client.get(
            f"{settings.odds_api_base}/sports/{settings.odds_api_sport_key}/events/{event_id}/odds",
            params={
                "apiKey": settings.odds_api_key,
                "regions": "us",
                "markets": "alternate_totals",
                "oddsFormat": "decimal",
            },
        )
        resp.raise_for_status()
        return resp.json().get("bookmakers", [])
    except Exception as e:
        print(f"The Odds API error (alternate_totals, event {event_id}): {e}")
        return []


async def fetch_and_store_match_probs() -> Tuple[int, List[str]]:
    """
    Fetch odds for the full upcoming MLS slate (one bulk h2h+totals call,
    plus one btts call and one alternate_totals call per matched fixture —
    see _fetch_btts_bookmakers / _fetch_alternate_totals_bookmakers),
    devig into win/draw/loss/BTTS/O1.5/O2.5/O3.5, and store per mls_fixture_id.

    Returns (rows written, unmatched team names) — unmatched names indicate
    ODDS_API_NAME_ALIASES needs another entry.
    """
    if not settings.odds_api_key:
        print("ODDS_API_KEY not set — skipping The Odds API fetch")
        return 0, []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{settings.odds_api_base}/sports/{settings.odds_api_sport_key}/odds",
                params={
                    "apiKey": settings.odds_api_key,
                    "regions": "us",
                    "markets": "h2h,totals",
                    "oddsFormat": "decimal",
                },
            )
            resp.raise_for_status()
            events = resp.json()
        except Exception as e:
            print(f"The Odds API error: {e}")
            return 0, []

        conn = get_connection()
        cur = conn.cursor()
        written = 0
        unmatched: List[str] = []

        for event in events:
            home_name = event.get("home_team")
            away_name = event.get("away_team")
            home_id = _resolve_team_name(cur, home_name) if home_name else None
            away_id = _resolve_team_name(cur, away_name) if away_name else None
            for name, tid in ((home_name, home_id), (away_name, away_id)):
                if name and tid is None and name not in unmatched:
                    unmatched.append(name)
            if home_id is None or away_id is None:
                continue

            cur.execute("""
                SELECT id FROM mls_fixtures
                WHERE home_team_id = ? AND away_team_id = ? AND status = 'NS'
                ORDER BY date_utc ASC LIMIT 1
            """, (home_id, away_id))
            row = cur.fetchone()
            if row is None:
                continue
            fixture_id = row["id"]

            # Only spend btts/alternate_totals credits on fixtures we're actually going to write.
            event_id = event.get("id")
            if event_id:
                event["bookmakers"] = (
                    event.get("bookmakers", [])
                    + await _fetch_btts_bookmakers(client, event_id)
                    + await _fetch_alternate_totals_bookmakers(client, event_id)
                )

            probs = _match_probs_from_event(event)
            if probs is None:
                continue

            cur.execute("""
                INSERT INTO mls_match_probs
                (fixture_id, home_win_pct, draw_pct, away_win_pct, btts_pct,
                 over_1_5_pct, over_2_5_pct, over_3_5_pct, bookmaker_count, computed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, unixepoch())
                ON CONFLICT(fixture_id) DO UPDATE SET
                    home_win_pct=excluded.home_win_pct,
                    draw_pct=excluded.draw_pct,
                    away_win_pct=excluded.away_win_pct,
                    btts_pct=excluded.btts_pct,
                    over_1_5_pct=excluded.over_1_5_pct,
                    over_2_5_pct=excluded.over_2_5_pct,
                    over_3_5_pct=excluded.over_3_5_pct,
                    bookmaker_count=excluded.bookmaker_count,
                    computed_at=excluded.computed_at
            """, (
                fixture_id, probs["home_win_pct"], probs["draw_pct"], probs["away_win_pct"],
                probs["btts_pct"], probs["over_1_5_pct"], probs["over_2_5_pct"], probs["over_3_5_pct"],
                probs["bookmaker_count"],
            ))
            written += 1

        conn.commit()
        conn.close()

    if unmatched:
        print(f"Odds API: {len(unmatched)} team name(s) unmatched to mls_teams — extend ODDS_API_NAME_ALIASES: {unmatched}")

    return written, unmatched
