"""
Monte Carlo tournament simulator for WC2026.
WC2026 format: 12 groups of 4. Top 2 per group + 8 best 3rd-place = 32 teams.
Then standard knockout: R32 → R16 → QF → SF → Final.
"""
import numpy as np
import time
import json
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from app.config import get_settings
from app.database import get_connection
from app.services.predictions import predict_match, _load_params_from_db

settings = get_settings()

# ---------------------------------------------------------------------------
# WC2026 R32 bracket structure (group positions, not team names).
# Derived from confirmed DB fixtures + FIFA draw for unknown slots.
# Confirmed slots (from DB): 1, 2, 3(partial), 4, 7(partial), 10(partial),
#   13(partial), 14(partial), 15(partial).
# Format: ("XY", ...) where X=rank(1/2) and Y=group letter, "3P"=3rd-place qualifier.
# ---------------------------------------------------------------------------
R32_BRACKET_SLOTS = [
    ("2A", "2B"),   # Slot  1: Jun 28 — South Africa vs Canada (confirmed)
    ("1C", "2F"),   # Slot  2: Jun 29 — Brazil vs Japan (confirmed)
    ("1E", "2H"),   # Slot  3: Jun 29 — Germany confirmed; 2H inferred
    ("1F", "2C"),   # Slot  4: Jun 30 — Netherlands vs Morocco (confirmed)
    ("1G", "3P"),   # Slot  5: Jun 30 — inferred
    ("1H", "3P"),   # Slot  6: Jul 01 — inferred
    ("1A", "2G"),   # Slot  7: Jul 01 — Mexico confirmed; 2G inferred
    ("1K", "3P"),   # Slot  8: Jul 01 — inferred
    ("1L", "2E"),   # Slot  9: Jul 01 — inferred
    ("1D", "3P"),   # Slot 10: Jul 02 — USA confirmed; 3rd qualifier (incl. Bosnia)
    ("2J", "3P"),   # Slot 11: Jul 02 — inferred
    ("2L", "3P"),   # Slot 12: Jul 03 — inferred
    ("1B", "2I"),   # Slot 13: Jul 03 — Switzerland confirmed; 2I inferred
    ("2D", "1I"),   # Slot 14: Jul 03 — Australia confirmed; 1I inferred
    ("1J", "2K"),   # Slot 15: Jul 04 — Argentina confirmed; 2K inferred
    ("3P", "3P"),   # Slot 16: Jul 04 — two 3rd-place qualifiers
]


def _simulate_match_from_pred(pred: Dict) -> str:
    """Simulate one match outcome from a pre-computed prediction dict."""
    r = np.random.random() * 100
    if r < pred["home_win_pct"]:
        return "home"
    elif r < pred["home_win_pct"] + pred["draw_pct"]:
        return "draw"
    return "away"


def _simulate_knockout_match(
    team_a: str, team_b: str, pred_cache: Dict,
    completed_results: Optional[Dict] = None,
) -> str:
    """
    Knockout match — no draws. If this exact matchup has already been played
    for real, deterministically return the real winner instead of simulating
    (otherwise every one of the 10k iterations would re-gamble a result that
    already happened, e.g. Japan already lost to Brazil in the real Round of
    32 — the simulation should reflect that as certain, not ~40% likely).
    Falls back to the model prediction for matchups that haven't been played.
    """
    if completed_results:
        real_winner = completed_results.get(frozenset((team_a, team_b)))
        if real_winner is not None:
            return real_winner

    key = (team_a, team_b)
    if key not in pred_cache:
        pred_cache[key] = predict_match(team_a, team_b)
    pred = pred_cache[key]
    result = _simulate_match_from_pred(pred)
    if result == "draw":
        return team_a if np.random.random() < 0.5 else team_b
    return team_a if result == "home" else team_b


def _load_completed_knockout_results() -> Dict[frozenset, str]:
    """
    Real, already-decided knockout results — {frozenset({team_a, team_b}): winner}.
    Only matches with a clear score margin are included; a tied scoreline on
    a PEN/AET match (shootout winner not reflected in home_score/away_score)
    is deliberately skipped rather than guessed at.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ht.name as home_name, at.name as away_name, f.home_score, f.away_score
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.status IN ('FT', 'AET', 'PEN')
          AND f.round NOT LIKE 'Group Stage%'
          AND f.round != '3rd Place'
    """)
    results: Dict[frozenset, str] = {}
    for row in cur.fetchall():
        hs, as_ = row["home_score"], row["away_score"]
        if hs is None or as_ is None or hs == as_:
            continue
        winner = row["home_name"] if hs > as_ else row["away_name"]
        results[frozenset((row["home_name"], row["away_name"]))] = winner
    conn.close()
    return results


def _load_real_r32_matchups() -> List[Tuple[str, str]]:
    """
    Real Round of 32 pairings straight from the fixtures table, in kickoff
    order. Once the group stage (incl. 3rd-place qualification) is settled,
    football-data.org populates all 16 R32 rows with the real, official team
    names — this is ground truth and far more reliable than re-deriving the
    FIFA draw's 3rd-place slotting ourselves (R32_BRACKET_SLOTS above has
    several slots marked "inferred" that were only best-guesses at the time
    they were written, before the real draw/results were known — e.g. this
    is why Germany and Congo DR, both already eliminated in the real R32,
    kept showing large non-zero odds for R16+: the simulation was pairing
    them against a guessed, sometimes-wrong opponent instead of their real
    one, so the "already played" check in _simulate_knockout_match never
    matched).
    """
    return _load_real_round_matchups("Round of 32")


def _load_real_round_matchups(round_name: str) -> List[Tuple[str, str]]:
    """
    Real bracket pairings for one knockout round straight from the fixtures
    table, in kickoff order — covers both already-played matches and matches
    that are merely scheduled (both opponents known, game not yet played).
    Only rows where both teams are populated are returned; football-data.org
    fills a round's fixture rows in with real team names as soon as both of
    that match's participants are determined, even before kickoff.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ht.name as home, at.name as away
        FROM fixtures f
        LEFT JOIN teams ht ON f.home_team_id = ht.id
        LEFT JOIN teams at ON f.away_team_id = at.id
        WHERE f.round = ?
        ORDER BY f.date_utc
    """, (round_name,))
    rows = cur.fetchall()
    conn.close()
    return [(r["home"], r["away"]) for r in rows if r["home"] and r["away"]]


def _resolve_round_matchups(
    round_name: str,
    prev_winners: List[str],
    real_matchups_cache: Dict[str, List[Tuple[str, str]]],
) -> List[Tuple[str, str]]:
    """
    Pair up this round's participants, preferring real confirmed pairings
    from the fixtures table over naive sequential pairing of this
    iteration's simulated winners — sequential pairing doesn't reliably
    reflect the true bracket tree (verified: it mispairs several real Round
    of 16 matchups, e.g. producing "Canada vs Brazil" when the real bracket
    is "Canada vs Morocco" / "Brazil vs Norway"). Falls back to sequential
    pairing only for slots whose real opponents aren't determined yet.
    """
    remaining = list(prev_winners)
    matchups = []

    for home, away in real_matchups_cache.get(round_name, []):
        if home in remaining and away in remaining:
            matchups.append((home, away))
            remaining.remove(home)
            remaining.remove(away)

    for i in range(0, len(remaining) - 1, 2):
        matchups.append((remaining[i], remaining[i + 1]))

    return matchups


def _precompute_group_preds(groups: Dict[str, List[str]], model_params: Dict) -> Dict:
    """
    Pre-compute all group stage match predictions once before the simulation loop.
    72 unique matchups total (6 per group × 12 groups) — reused across all 10k sims.
    """
    cache = {}
    for teams in groups.values():
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                home, away = teams[i], teams[j]
                cache[(home, away)] = predict_match(home, away, model_params)
    return cache


def _load_live_group_state() -> Tuple[Dict, Dict]:
    """
    Load current standings and remaining unplayed group fixtures from DB.

    Returns:
      live_pts: {group_letter: {team_name: {pts, gd, gf, played}}}
      remaining_fixtures: {group_letter: [(home_name, away_name), ...]}
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.group_letter, t.name, s.points, s.goal_diff, s.goals_for, s.played
        FROM standings s
        JOIN teams t ON s.team_id = t.id
        WHERE s.group_letter IS NOT NULL
    """)
    live_pts: Dict = {}
    for row in cur.fetchall():
        g = row["group_letter"]
        if g not in live_pts:
            live_pts[g] = {}
        live_pts[g][row["name"]] = {
            "pts": row["points"] or 0,
            "gd":  row["goal_diff"] or 0,
            "gf":  row["goals_for"] or 0,
            "played": row["played"] or 0,
        }

    # Only unplayed group-stage fixtures (both teams in same group)
    cur.execute("""
        SELECT ht.name AS home_name, at.name AS away_name, ht.group_letter AS grp
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE f.status IN ('NS', 'TBD', 'PST')
          AND ht.group_letter IS NOT NULL
          AND at.group_letter IS NOT NULL
          AND ht.group_letter = at.group_letter
    """)
    remaining_fixtures: Dict = {}
    for row in cur.fetchall():
        g = row["grp"]
        if g not in remaining_fixtures:
            remaining_fixtures[g] = []
        remaining_fixtures[g].append((row["home_name"], row["away_name"]))

    conn.close()
    return live_pts, remaining_fixtures


def _simulate_group_stage(
    groups: Dict[str, List[str]],
    pred_cache: Dict,
    live_pts: Optional[Dict] = None,
    remaining_fixtures: Optional[Dict] = None,
) -> Dict[str, List]:
    """
    Simulate group stage using pre-computed predictions.

    If live_pts is provided, seeds each group's standings from actual DB data and
    only simulates the unplayed remaining fixtures (not already-completed matches).

    Returns {group_letter: [(team, pts, gd, gf), ...]} sorted by rank.
    """
    group_results = {}

    for group_letter, teams in groups.items():
        # Seed standings from live DB data where available
        if live_pts and group_letter in live_pts:
            standing = {}
            for t in teams:
                live = live_pts[group_letter].get(t, {"pts": 0, "gd": 0, "gf": 0})
                standing[t] = {
                    "pts": live["pts"],
                    "gd":  live["gd"],
                    "gf":  live["gf"],
                }
        else:
            standing = {t: {"pts": 0, "gd": 0, "gf": 0} for t in teams}

        # Determine which fixtures to simulate
        if remaining_fixtures is not None:
            fixtures_to_sim = remaining_fixtures.get(group_letter, [])
        else:
            # No live data — simulate all 6 matches from scratch
            fixtures_to_sim = [
                (teams[i], teams[j])
                for i in range(len(teams))
                for j in range(i + 1, len(teams))
            ]

        for home, away in fixtures_to_sim:
            # Look up prediction; handle both key orderings
            if (home, away) in pred_cache:
                pred = pred_cache[(home, away)]
            elif (away, home) in pred_cache:
                orig = pred_cache[(away, home)]
                pred = {
                    "home_win_pct":         orig["away_win_pct"],
                    "away_win_pct":         orig["home_win_pct"],
                    "draw_pct":             orig["draw_pct"],
                    "expected_home_goals":  orig["expected_away_goals"],
                    "expected_away_goals":  orig["expected_home_goals"],
                }
            else:
                pred = predict_match(home, away)

            lam_h = pred["expected_home_goals"]
            lam_a = pred["expected_away_goals"]
            hg = int(np.random.poisson(lam_h))
            ag = int(np.random.poisson(lam_a))

            standing[home]["gf"] += hg
            standing[away]["gf"] += ag
            standing[home]["gd"] += hg - ag
            standing[away]["gd"] += ag - hg

            if hg > ag:
                standing[home]["pts"] += 3
            elif hg == ag:
                standing[home]["pts"] += 1
                standing[away]["pts"] += 1
            else:
                standing[away]["pts"] += 3

        ranked = sorted(
            teams,
            key=lambda t: (
                standing[t]["pts"],
                standing[t]["gd"],
                standing[t]["gf"],
                np.random.random(),
            ),
            reverse=True,
        )
        group_results[group_letter] = [
            (t, standing[t]["pts"], standing[t]["gd"], standing[t]["gf"])
            for t in ranked
        ]

    return group_results


def _get_third_place_qualifiers(group_results: Dict[str, List]) -> List[str]:
    """Select 8 best 3rd-place teams from 12 groups."""
    thirds = []
    for group_letter, ranked in group_results.items():
        if len(ranked) >= 3:
            t, pts, gd, gf = ranked[2]
            thirds.append((t, pts, gd, gf))

    thirds.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    return [t[0] for t in thirds[:8]]


def _build_r32_bracket(
    group_results: Dict[str, List],
    third_qualifiers: List[str],
) -> List[Tuple[str, str]]:
    """
    Build Round of 32 matchups using the fixed WC2026 bracket structure.
    Bracket slots are deterministic (derived from FIFA draw), not randomly shuffled.
    Third-place qualifiers are assigned best-to-worst across the 8 '3P' slots.
    """
    third_idx = [0]

    def get_team(pos: str) -> Optional[str]:
        if pos == "3P":
            idx = third_idx[0]
            if idx < len(third_qualifiers):
                third_idx[0] += 1
                return third_qualifiers[idx]
            return None
        rank = int(pos[0])
        group = pos[1]
        results = group_results.get(group, [])
        if len(results) >= rank:
            return results[rank - 1][0]
        return None

    matchups = []
    for home_pos, away_pos in R32_BRACKET_SLOTS:
        home = get_team(home_pos)
        away = get_team(away_pos)
        if home and away:
            matchups.append((home, away))

    return matchups


def simulate_tournament(
    groups: Dict[str, List[str]],
    n_sims: int = None,
) -> Dict[str, Dict]:
    """
    Run Monte Carlo simulation.
    groups: {letter: [team1, team2, team3, team4]}
    Returns: {team_name: {r32, r16, qf, sf, final, winner}} as probabilities 0-100.
    """
    if n_sims is None:
        n_sims = settings.mc_simulations

    model_params = _load_params_from_db()
    if model_params is None:
        return {}

    all_teams = [t for teams in groups.values() for t in teams]
    counts = {t: defaultdict(int) for t in all_teams}

    # Load live standings + remaining fixtures once; shared across all sims
    live_pts, remaining_fixtures = _load_live_group_state()
    # Real knockout results already played — shared across all sims so eliminated
    # teams (e.g. Japan) can't keep winning simulated rematches against reality.
    completed_results = _load_completed_knockout_results()
    # Real R32 pairings once the bracket is fully set (see docstring) — takes
    # priority over the guessed group-position bracket below when available.
    real_r32_matchups = _load_real_r32_matchups()
    r32_bracket_locked = len(real_r32_matchups) == len(R32_BRACKET_SLOTS)
    # Real R16+ pairings as football-data.org fills them in — see
    # _resolve_round_matchups for why naive sequential pairing isn't enough.
    real_matchups_cache = {
        rnd: _load_real_round_matchups(rnd)
        for rnd in ("Round of 16", "Quarter-finals", "Semi-finals", "Final")
    }

    # Pre-compute all 72 group stage predictions once — reused across all n_sims iterations
    group_pred_cache = _precompute_group_preds(groups, model_params)
    # Knockout prediction cache grows as new matchups appear; shared across all sims
    knockout_pred_cache: Dict = {}

    for _ in range(n_sims):
        group_results = _simulate_group_stage(
            groups, group_pred_cache, live_pts, remaining_fixtures
        )
        third_qualifiers = _get_third_place_qualifiers(group_results)

        r32_teams = set()
        for g, ranked in group_results.items():
            if ranked:
                r32_teams.add(ranked[0][0])
            if len(ranked) > 1:
                r32_teams.add(ranked[1][0])
        r32_teams.update(third_qualifiers)

        for t in r32_teams:
            counts[t]["r32"] += 1

        matchups = real_r32_matchups if r32_bracket_locked else _build_r32_bracket(group_results, third_qualifiers)
        r32_winners = [
            _simulate_knockout_match(a, b, knockout_pred_cache, completed_results)
            for a, b in matchups
        ]

        for t in r32_winners:
            counts[t]["r16"] += 1

        r16_matchups = _resolve_round_matchups("Round of 16", r32_winners, real_matchups_cache)
        r16_winners = [
            _simulate_knockout_match(a, b, knockout_pred_cache, completed_results)
            for a, b in r16_matchups
        ]
        for w in r16_winners:
            counts[w]["qf"] += 1

        qf_matchups = _resolve_round_matchups("Quarter-finals", r16_winners, real_matchups_cache)
        qf_winners = [
            _simulate_knockout_match(a, b, knockout_pred_cache, completed_results)
            for a, b in qf_matchups
        ]
        for w in qf_winners:
            counts[w]["sf"] += 1

        sf_matchups = _resolve_round_matchups("Semi-finals", qf_winners, real_matchups_cache)
        sf_winners = [
            _simulate_knockout_match(a, b, knockout_pred_cache, completed_results)
            for a, b in sf_matchups
        ]
        for w in sf_winners:
            counts[w]["final"] += 1

        final_matchups = _resolve_round_matchups("Final", sf_winners, real_matchups_cache)
        if final_matchups:
            champion = _simulate_knockout_match(
                *final_matchups[0], knockout_pred_cache, completed_results
            )
            counts[champion]["winner"] += 1

    # Convert to percentages
    result = {}
    for team in all_teams:
        result[team] = {
            "r32_pct":    round(counts[team]["r32"]    / n_sims * 100, 1),
            "r16_pct":    round(counts[team]["r16"]    / n_sims * 100, 1),
            "qf_pct":     round(counts[team]["qf"]     / n_sims * 100, 1),
            "sf_pct":     round(counts[team]["sf"]     / n_sims * 100, 1),
            "final_pct":  round(counts[team]["final"]  / n_sims * 100, 1),
            "winner_pct": round(counts[team]["winner"] / n_sims * 100, 1),
        }

    return result


def store_advancement_probs(probs: Dict[str, Dict], team_name_to_id: Dict[str, int]):
    """Save Monte Carlo results to DB."""
    conn = get_connection()
    cur = conn.cursor()
    now = time.time()

    for team_name, prob in probs.items():
        team_id = team_name_to_id.get(team_name)
        if team_id is None:
            continue
        cur.execute("""
            INSERT INTO advancement_probs
            (team_id, r32_pct, r16_pct, qf_pct, sf_pct, final_pct, winner_pct, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team_id) DO UPDATE SET
                r32_pct    = excluded.r32_pct,
                r16_pct    = excluded.r16_pct,
                qf_pct     = excluded.qf_pct,
                sf_pct     = excluded.sf_pct,
                final_pct  = excluded.final_pct,
                winner_pct = excluded.winner_pct,
                computed_at = excluded.computed_at
        """, (
            team_id, prob["r32_pct"], prob["r16_pct"], prob["qf_pct"],
            prob["sf_pct"], prob["final_pct"], prob["winner_pct"], now,
        ))

    conn.commit()
    conn.close()


def load_advancement_probs() -> List[Dict]:
    """Load stored advancement probabilities with team info."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ap.*, t.name as team_name, t.logo, t.group_letter
        FROM advancement_probs ap
        JOIN teams t ON ap.team_id = t.id
        ORDER BY ap.winner_pct DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
