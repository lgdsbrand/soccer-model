# MLS Section — Build Status (checkpoint: Day 4, committed locally, demo-ready on desktop/localhost)

Plan file: `C:\Users\denis\.claude\plans\i-m-adding-an-mls-iterative-volcano.md`

## Safe to demo to Tyler right now (2026-07-20)

**Solid — desktop, localhost:3000 only:**
- MLS Dashboard, Matches list, Standings — real ESPN data, confirmed clean via live screenshots.
- MLS match detail pages — verified correct at the data level (team names, odds-derived predictions, season stats, goals/game, AI analysis/key players/style-of-play/lineups all generating correctly). Not re-screenshotted this session (Playwright tooling error) — do a quick manual look before screenshotting for Tyler.
- World Cup side — regression-tested, unaffected.

**Not ready — don't show:**
- Mobile/responsive view (never checked — desktop screenshots only).
- The "no odds posted yet" empty state for far-future fixtures (untested).
- The deployed Render site — nothing pushed/deployed yet, still running old pre-MLS code, no `ODDS_API_KEY` configured there. Only `localhost:3000` is current.
- Flag to Tyler as by-design, not a bug: Attack Strength / xG / xGA don't show for MLS (no model for MLS yet — see item 9 below).

## Done

### Backend (Day 1-2)
- `backend/app/mls/database.py` — 7 isolated `mls_*` tables (teams, fixtures, standings, match_probs, lineups, match_stats, team_season_stats). Confirmed zero overlap/risk to World Cup tables.
- `backend/app/mls/services/mls_source.py` — MLS teams/fixtures/standings from **ESPN's public API** (no key needed). Verified live: 32 teams, 511 fixtures, correct Eastern/Western conference standings.
  - **Deviation from original plan**: was going to reuse API-Football, but that account is **suspended** (confirmed via live `/status` call — `"Your account is suspended, check on https://dashboard.api-football.com"`). This is also currently breaking World Cup last-5 stats/lineups — worth fixing separately, not urgent for Friday.
- `backend/app/mls/services/odds_api.py` — devigs h2h/totals/btts markets into win/draw/loss/BTTS/O2.5/O3.5. **Verified live 2026-07-20** against a real key — 30/30 MLS fixtures matched and written, real bookmaker data confirmed. Three real bugs found and fixed during verification (not anticipated in the original plan):
  1. **`btts` isn't a valid market on the bulk `/sports/{sport}/odds` endpoint** — it 422s with `INVALID_MARKET` if requested there, which was failing the *entire* call (h2h/totals included, not just btts — 0 rows would've been written). The Odds API only serves btts through the per-event `/sports/{sport}/events/{id}/odds` endpoint. Fix: bulk call now requests only `h2h,totals`; btts is fetched with one extra per-fixture call, but only for fixtures that already passed team-name/schedule matching (no point spending a credit on one we can't write anyway).
     - **Cost tradeoff, decided with the user**: per-event btts costs API credits per fixture per refresh. Chose real per-fixture bookmaker data over dropping BTTS, and moved the MLS refresh from hourly to **every 12h** (`main.py`) to keep it bounded: ~30 fixtures × (1 bulk call + 1 btts call each) ≈ 31 calls/refresh × 2 refreshes/day × 30 days ≈ **1,900 calls/month** — comfortably inside the Professional tier's monthly quota (confirmed ~13,000 remaining mid-testing after ~7,000 used elsewhere). Note: Render's free-tier cold-start-triggers-a-refresh behavior (see `_initial_seed_mls`) means actual call volume tracks traffic/cold-starts too, not strictly the 12h interval — worth revisiting if quota ever gets tight.
  2. **No MLS bookmaker ever quotes a 1.5-goals total line** — checked actual `point` values across the full live slate: `2.5, 2.75, 3.0, 3.25, 3.5, 3.75`, never `1.5` (MLS averages ~3 goals/game, so a 1.5 line isn't useful to books). The original code only captured `point == 1.5 or 2.5`, so `over_1_5_pct` would've always been `null` — and `MatchCard.tsx` rendered it unconditionally, which would've shown literal **"null%"** on every MLS match. **Decided with the user**: swapped MLS's second goals-total stat from O1.5 to O3.5 (tracks O2.5 + O3.5 now). This only affects MLS's own `mls_match_probs.over_3_5_pct` column/field — the World Cup's separate `predictions.over_1_5_pct` (Dixon-Coles-derived, genuinely meaningful there) is untouched.
  3. **O2.5 and O3.5 are mutually exclusive per MLS fixture** — confirmed across all 30 live fixtures: every single one has *exactly one* of the two populated, never both, never neither (bookmakers quote either a 2.5 or a 3.5 total for a given match, not both). The O2.5 chip was rendered unconditionally in `MatchCard.tsx`, which would've shown "null%" on whichever MLS matches only had a 3.5 line. Fixed by gating both O2.5 and O3.5 chips on presence (same pattern already used for `expected_home_goals`), while leaving WC's O1.5/O2.5 unconditional since Dixon-Coles always computes both.
  4. Five team names came back unmatched on first live run (`Chicago Fire`, `Columbus Crew SC`, `Vancouver Whitecaps FC`, `CF Montreal`, `Houston Dynamo` vs. ESPN's `Chicago Fire FC`, `Columbus Crew`, `Vancouver Whitecaps`, `CF Montréal`, `Houston Dynamo FC`) — `ODDS_API_NAME_ALIASES` extended with all five (one, `Vancouver Whitecaps`, had been aliased backwards in the original seed list — fixed). Re-run after the fix: 30/30 matched, 0 unmatched.
- `backend/app/mls/services/mls_team_stats.py` — season stats (corners/shots/fouls) from FotMob. Had to reverse-engineer the MLS league/season IDs (130/29580, opaque FotMob internals) via a live browser network capture. Verified live: 30/30 teams matched, zero unmatched names.
- `backend/app/mls/routers/fixtures.py`, `standings.py` — registered in `main.py`. Verified live end-to-end including background LLM tasks (lineups, key players, AI analysis all generate and persist correctly).
- `main.py` — MLS refresh runs both hourly *and* on startup (same fix applied earlier to the WC Monte Carlo staleness bug — Render's free tier spins down before the first hourly tick would ever fire).
- `llm.py` — additive `competition_label`/`team_type` params on 4 functions. Existing WC call sites unaffected (defaults preserve old behavior). Also fixed a bug not in original scope: `get_style_of_play`'s prompt hardcoded "national football team," which would've produced nonsense for MLS clubs.

### Frontend (Day 3)
- `lib/mlsApi.ts`, `components/mls/LeagueSwitcher.tsx` (+ `Sidebar.tsx` edit), `components/mls/StandingsTable.tsx`, `components/mls/MatchDayNav.tsx`, `app/mls/page.tsx`, `app/mls/matches/page.tsx`, `app/mls/matches/[id]/page.tsx`, `app/mls/standings/page.tsx`.
- Verified live in a real browser (Playwright) — dashboard, matches list, match detail, standings all render correctly with real data. Zero console errors.
- **Regression-tested the World Cup side** — dashboard, a knockout match, and a group-stage match all confirmed pixel-identical/functionally unchanged.

### Real bugs found and fixed along the way (not anticipated in the original plan)
1. `MatchCard.tsx`'s stats-comparison section was gated on a Dixon-Coles-only field MLS doesn't have — widened the gate so season stats show even without a Dixon-Coles rating.
2. `pred.expected_home_goals.toFixed(2)` would have thrown for MLS (no xG concept from odds markets) — made that one stat chip conditional.
3. `isKnockout` was a blacklist heuristic (`!round.startsWith("Group Stage")`) that would've silently hidden the draw percentage for every MLS match. Changed to an explicit allowlist of real WC knockout round names.
4. `FixtureRow.tsx` and `MatchCard.tsx` both hardcoded `/matches/{id}` links — would have sent MLS fixture clicks to the wrong route (or worse, collided with an unrelated WC fixture sharing the same numeric ID). Added a `basePath` prop to both.
5. `DateNav` turned out to be a Yesterday/Today/Tomorrow relative widget, not a "show next N days" selector — it would've rendered nothing most of the time for MLS's 1-2x/week schedule. Built `MatchDayNav` instead, which is what "next 3-5 match days" actually needs.
6. The "Recommended Play" section showed a permanent "Generating recommendation — refresh in a few seconds" for MLS, since that feature is legitimately out of scope and nothing was ever going to generate one. Added a `showRecommendedPlay` prop to suppress it cleanly instead of showing a misleading perpetual-loading state.
7. ESPN labels the club at team id 190 by its old sponsor-led name ("Red Bull New York" / "Red Bull NY" / "RBNY") throughout `name`/`short_name`/`abbreviation` — the club rebranded to "New York Red Bulls" years ago. Corrected at ingest via `ESPN_TEAM_NAME_OVERRIDES` in `mls_source.py` (keyed by team id, not the wrong name) so every consumer sees the right name automatically. Also fixed the two places that depended on the old name: `FOTMOB_NAME_TO_MLS_NAME` (FotMob's own data still calls it "Red Bull New York") and `odds_api.py`'s `ODDS_API_NAME_ALIASES` (removed — no longer needed, the Odds API's own name is an exact match to the corrected one).
8. `MatchCard.tsx`'s "IMPORTANT STATS" section showed an orphaned "Attack Strength on a 0-100 scale" caption for MLS matches even though the Attack Strength row itself is filtered out (MLS has no Dixon-Coles model, so `home_attack_rating`/`away_attack_rating` are always null there). Caption is now gated on the Attack Strength row actually being present.
9. Added real **Goals/Goals Allowed per game** for MLS — wired `mls_standings.goals_for/goals_against/played` (already synced from ESPN) into the fixture response via a new `_get_mls_goals_per_game()` helper in `app/mls/routers/fixtures.py`. This is genuinely different from Attack Strength/xG/xGA: those three are all derived from a fitted Dixon-Coles Poisson model (see `predictions.py`'s `get_attack_xg_ratings` — `xg_rating`/`xga_rating` aren't real external xG data either, they're the same fitted attack/defense params re-expressed as `exp(attack + avg_defense)`), which doesn't exist for MLS. Goals/Goals Allowed per game, by contrast, are just real observed averages MLS already had the raw data for. The "Goals / xG" and "Goals Allowed / xGA" rows now show for MLS with a real goals number and "—" for the xG/xGA half (existing `fmt()` already handles that gracefully).

**Deliberately not done** — flagged with the user, decided to scope as a future task rather than build now: a separate Dixon-Coles/Poisson model fitted on MLS results, which would unlock real Attack Strength (0-100) and xG/xGA for MLS matches. This is genuine new modeling work (fit attack/defense parameters per team from historical MLS results, tune time-decay, etc.), not a data-wiring fix like the goals-per-game addition above — worth scoping separately if wanted.

## Left for Day 4 (Friday)

1. ~~Finish verifying `odds_api.py` against a real Odds API key~~ — **done 2026-07-20**. Real key in `backend/.env`, live-verified, 3 real bugs found and fixed (see above). Local dev DB (`wc2026.db`) migrated in place (`over_1_5_pct` → `over_3_5_pct`, 0 rows lost — table was still empty pre-fix).
2. Mobile/responsive pass on the new MLS pages (not checked yet).
3. Confirm the "odds not yet available" empty state (for far-future fixtures with no posted lines) looks right, not broken.
4. Add `ODDS_API_KEY` to `render.yaml` env list + Render dashboard secret (still open — production deploy hasn't happened yet).
5. Final end-to-end smoke test against the deployed site.
6. ~~Nothing has been committed to git yet~~ — **done 2026-07-20**, commit `b62693c` ("Add MLS section: fixtures, standings, odds-derived predictions"). Not pushed to origin yet.

## Open questions for you
- Separately: want me to look at fixing the suspended API-Football account (also affects WC last-5 stats), or leave it since MLS no longer depends on it?
