"""
Dixon-Coles Poisson model for football match prediction.
Reference: Dixon & Coles (1997) "Modelling Association Football Scores"
"""
import numpy as np
import time
import json
from typing import Dict, List, Tuple, Optional
from scipy.optimize import minimize
from scipy.stats import poisson
from scipy.special import gammaln
from app.config import get_settings
from app.database import get_connection

settings = get_settings()

MAX_GOALS = 10  # Cap for goal probability summation

# Pre-computed log(k!) for k = 0..19 — avoids repeated gammaln calls in the hot path
_LOG_FACT = gammaln(np.arange(20) + 1)

# ---------------------------------------------------------------------------
# Confederation strength multiplier — corrects for uneven opponent quality
# across confederations. Without this, teams that mostly play weak regional
# opponents (e.g. Japan in AFC qualifiers) get inflated attack/defense params.
# ---------------------------------------------------------------------------
CONFEDERATION = {
    # UEFA
    "Albania": "UEFA", "Andorra": "UEFA", "Armenia": "UEFA", "Austria": "UEFA",
    "Azerbaijan": "UEFA", "Belarus": "UEFA", "Belgium": "UEFA",
    "Bosnia and Herzegovina": "UEFA", "Bulgaria": "UEFA", "Croatia": "UEFA",
    "Cyprus": "UEFA", "Czech Republic": "UEFA", "Czechia": "UEFA",
    "Denmark": "UEFA", "England": "UEFA", "Estonia": "UEFA",
    "Faroe Islands": "UEFA", "Finland": "UEFA", "France": "UEFA",
    "Georgia": "UEFA", "Germany": "UEFA", "Gibraltar": "UEFA",
    "Greece": "UEFA", "Hungary": "UEFA", "Iceland": "UEFA",
    "Israel": "UEFA", "Italy": "UEFA", "Kazakhstan": "UEFA",
    "Kosovo": "UEFA", "Latvia": "UEFA", "Liechtenstein": "UEFA",
    "Lithuania": "UEFA", "Luxembourg": "UEFA", "Malta": "UEFA",
    "Moldova": "UEFA", "Montenegro": "UEFA", "Netherlands": "UEFA",
    "North Macedonia": "UEFA", "Northern Ireland": "UEFA", "Norway": "UEFA",
    "Poland": "UEFA", "Portugal": "UEFA", "Republic of Ireland": "UEFA",
    "Romania": "UEFA", "Russia": "UEFA", "San Marino": "UEFA",
    "Scotland": "UEFA", "Serbia": "UEFA", "Slovakia": "UEFA",
    "Slovenia": "UEFA", "Spain": "UEFA", "Sweden": "UEFA",
    "Switzerland": "UEFA", "Turkey": "UEFA", "Türkiye": "UEFA",
    "Ukraine": "UEFA", "Wales": "UEFA",
    # CONMEBOL
    "Argentina": "CONMEBOL", "Bolivia": "CONMEBOL", "Brazil": "CONMEBOL",
    "Chile": "CONMEBOL", "Colombia": "CONMEBOL", "Ecuador": "CONMEBOL",
    "Paraguay": "CONMEBOL", "Peru": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Venezuela": "CONMEBOL",
    # CONCACAF
    "Antigua and Barbuda": "CONCACAF", "Bahamas": "CONCACAF",
    "Barbados": "CONCACAF", "Belize": "CONCACAF", "Bermuda": "CONCACAF",
    "Canada": "CONCACAF", "Cayman Islands": "CONCACAF",
    "Costa Rica": "CONCACAF", "Cuba": "CONCACAF", "Curaçao": "CONCACAF",
    "Dominica": "CONCACAF", "Dominican Republic": "CONCACAF",
    "El Salvador": "CONCACAF", "Grenada": "CONCACAF",
    "Guatemala": "CONCACAF", "Guyana": "CONCACAF", "Haiti": "CONCACAF",
    "Honduras": "CONCACAF", "Jamaica": "CONCACAF", "Mexico": "CONCACAF",
    "Montserrat": "CONCACAF", "Nicaragua": "CONCACAF", "Panama": "CONCACAF",
    "Puerto Rico": "CONCACAF", "Saint Kitts and Nevis": "CONCACAF",
    "Saint Lucia": "CONCACAF",
    "Saint Vincent and the Grenadines": "CONCACAF",
    "Suriname": "CONCACAF", "Trinidad and Tobago": "CONCACAF",
    "Turks and Caicos Islands": "CONCACAF",
    "United States": "CONCACAF", "USA": "CONCACAF",
    "United States Virgin Islands": "CONCACAF",
    "British Virgin Islands": "CONCACAF", "Anguilla": "CONCACAF",
    "Aruba": "CONCACAF", "Bonaire": "CONCACAF",
    "French Guiana": "CONCACAF", "Guadeloupe": "CONCACAF",
    "Martinique": "CONCACAF", "Sint Maarten": "CONCACAF",
    # CAF
    "Algeria": "CAF", "Angola": "CAF", "Benin": "CAF", "Botswana": "CAF",
    "Burkina Faso": "CAF", "Burundi": "CAF", "Cameroon": "CAF",
    "Cape Verde": "CAF", "Central African Republic": "CAF", "Chad": "CAF",
    "Comoros": "CAF", "Congo": "CAF", "DR Congo": "CAF",
    "Djibouti": "CAF", "Egypt": "CAF", "Equatorial Guinea": "CAF",
    "Eswatini": "CAF", "Ethiopia": "CAF", "Gabon": "CAF",
    "Gambia": "CAF", "Ghana": "CAF", "Guinea": "CAF",
    "Guinea-Bissau": "CAF", "Ivory Coast": "CAF", "Kenya": "CAF",
    "Lesotho": "CAF", "Liberia": "CAF", "Libya": "CAF",
    "Madagascar": "CAF", "Malawi": "CAF", "Mali": "CAF",
    "Mauritania": "CAF", "Mauritius": "CAF", "Morocco": "CAF",
    "Mozambique": "CAF", "Namibia": "CAF", "Niger": "CAF",
    "Nigeria": "CAF", "Rwanda": "CAF", "Réunion": "CAF",
    "São Tomé and Príncipe": "CAF",
    "Senegal": "CAF", "Seychelles": "CAF", "Sierra Leone": "CAF",
    "Somalia": "CAF", "South Africa": "CAF", "South Sudan": "CAF",
    "Sudan": "CAF", "Tanzania": "CAF", "Togo": "CAF",
    "Tunisia": "CAF", "Uganda": "CAF", "Zambia": "CAF",
    "Zimbabwe": "CAF",
    # AFC
    "Afghanistan": "AFC", "Australia": "AFC", "Bahrain": "AFC",
    "Bangladesh": "AFC", "Bhutan": "AFC", "Brunei": "AFC",
    "Cambodia": "AFC", "China": "AFC", "Guam": "AFC",
    "Hong Kong": "AFC", "India": "AFC", "Indonesia": "AFC",
    "Iran": "AFC", "Iraq": "AFC", "Japan": "AFC", "Jordan": "AFC",
    "Kuwait": "AFC", "Kyrgyzstan": "AFC", "Laos": "AFC",
    "Lebanon": "AFC", "Macau": "AFC", "Malaysia": "AFC",
    "Maldives": "AFC", "Mongolia": "AFC", "Myanmar": "AFC",
    "Nepal": "AFC", "North Korea": "AFC", "Oman": "AFC",
    "Pakistan": "AFC", "Palestine": "AFC", "Philippines": "AFC",
    "Qatar": "AFC", "Saudi Arabia": "AFC", "Singapore": "AFC",
    "South Korea": "AFC", "Sri Lanka": "AFC", "Syria": "AFC",
    "Taiwan": "AFC", "Tajikistan": "AFC", "Thailand": "AFC",
    "Timor-Leste": "AFC", "Turkmenistan": "AFC",
    "United Arab Emirates": "AFC", "Uzbekistan": "AFC",
    "Vietnam": "AFC", "Yemen": "AFC",
    # OFC
    "American Samoa": "OFC", "Cook Islands": "OFC", "Fiji": "OFC",
    "New Caledonia": "OFC", "New Zealand": "OFC",
    "Papua New Guinea": "OFC", "Samoa": "OFC",
    "Solomon Islands": "OFC", "Tahiti": "OFC", "Tonga": "OFC",
    "Tuvalu": "OFC", "Vanuatu": "OFC",
    "Northern Mariana Islands": "OFC", "Marshall Islands": "OFC",
}

CONFED_STRENGTH = {
    "CONMEBOL": 1.000,
    "UEFA":     0.895,
    "CAF":      0.736,
    "AFC":      0.668,
    "CONCACAF": 0.539,
    "OFC":      0.376,
}


def _confederation_weight(home_team: str, away_team: str) -> Optional[float]:
    """
    Weight multiplier based on confederation strength of both teams.
    Returns None if either team is not a recognized FIFA member (should be filtered).
    """
    h = CONFEDERATION.get(home_team)
    a = CONFEDERATION.get(away_team)
    if h is None or a is None:
        return None
    return CONFED_STRENGTH[h] * CONFED_STRENGTH[a]


def _dc_correction(x: int, y: int, lam_x: float, lam_y: float, rho: float) -> float:
    """Dixon-Coles low-score correction factor (scalar, used in predict_match)."""
    if x == 0 and y == 0:
        return 1 - lam_x * lam_y * rho
    elif x == 1 and y == 0:
        return 1 + lam_y * rho
    elif x == 0 and y == 1:
        return 1 + lam_x * rho
    elif x == 1 and y == 1:
        return 1 - rho
    return 1.0


def _log_likelihood(
    params: np.ndarray,
    home_idx: np.ndarray,
    away_idx: np.ndarray,
    hg: np.ndarray,
    ag: np.ndarray,
    weights: np.ndarray,
    n_teams: int,
) -> float:
    """
    Vectorized negative log-likelihood for Dixon-Coles model.
    All 132 matches computed in a single numpy pass — no Python loop,
    no per-row scipy.stats calls. ~150x faster than the loop version.
    """
    home_adv = params[0]
    rho = params[1]
    attacks = params[2: 2 + n_teams]
    defenses = params[2 + n_teams: 2 + 2 * n_teams]

    lam_home = np.exp(home_adv + attacks[home_idx] + defenses[away_idx])
    lam_away = np.exp(attacks[away_idx] + defenses[home_idx])

    # Vectorized Poisson log-PMF: -λ + k*log(λ) - log(k!)
    log_p_home = -lam_home + hg * np.log(np.maximum(lam_home, 1e-10)) - _LOG_FACT[hg]
    log_p_away = -lam_away + ag * np.log(np.maximum(lam_away, 1e-10)) - _LOG_FACT[ag]

    # Vectorized Dixon-Coles low-score correction (log scale)
    dc_log = np.zeros(len(hg))
    m00 = (hg == 0) & (ag == 0)
    m10 = (hg == 1) & (ag == 0)
    m01 = (hg == 0) & (ag == 1)
    m11 = (hg == 1) & (ag == 1)
    if m00.any():
        dc_log[m00] = np.log(np.maximum(1 - lam_home[m00] * lam_away[m00] * rho, 1e-10))
    if m10.any():
        dc_log[m10] = np.log(np.maximum(1 + lam_away[m10] * rho, 1e-10))
    if m01.any():
        dc_log[m01] = np.log(np.maximum(1 + lam_home[m01] * rho, 1e-10))
    if m11.any():
        dc_log[m11] = np.log(np.maximum(1 - rho, 1e-10))

    return -float(np.sum(weights * (log_p_home + log_p_away + dc_log)))


def fit_model(matches: List[Dict]) -> Optional[Dict]:
    """
    Fit Dixon-Coles model to match data.
    matches: list of {home_team, away_team, home_goals, away_goals, days_ago}
    Returns dict of team params + home_adv + rho.
    """
    if len(matches) < 10:
        return None

    xi = settings.dc_time_decay
    filtered = []
    for m in matches:
        cw = _confederation_weight(m["home_team"], m["away_team"])
        if cw is None:
            continue
        tourn = m.get("tournament", "")
        friendly_factor = 0.5 if ("Friendly" in tourn or "Series" in tourn) else 1.0
        m["weight"] = np.exp(-xi * m.get("days_ago", 0)) * cw * friendly_factor
        filtered.append(m)

    matches = filtered
    if len(matches) < 10:
        return None

    teams = sorted(set(
        [m["home_team"] for m in matches] + [m["away_team"] for m in matches]
    ))
    n = len(teams)

    if n < 4:
        return None

    # Pre-compute integer arrays once — reused on every optimizer call
    team_idx = {t: i for i, t in enumerate(teams)}
    valid = [m for m in matches if m["home_team"] in team_idx and m["away_team"] in team_idx]
    home_idx = np.array([team_idx[m["home_team"]] for m in valid], dtype=np.int32)
    away_idx = np.array([team_idx[m["away_team"]] for m in valid], dtype=np.int32)
    GOAL_CAP = 3
    hg = np.minimum(np.array([int(m["home_goals"]) for m in valid], dtype=np.int32), GOAL_CAP)
    ag = np.minimum(np.array([int(m["away_goals"]) for m in valid], dtype=np.int32), GOAL_CAP)
    weights = np.array([m.get("weight", 1.0) for m in valid])

    x0 = np.zeros(2 + 2 * n)
    x0[0] = 0.1   # home advantage
    x0[1] = 0.01  # rho

    constraints = [{"type": "eq", "fun": lambda p: np.mean(p[2: 2 + n])}]

    result = minimize(
        _log_likelihood,
        x0,
        args=(home_idx, away_idx, hg, ag, weights, n),
        method="SLSQP",
        constraints=constraints,
        options={"maxiter": 1000, "ftol": 1e-9},
    )

    if not result.success:
        print(f"Model fit warning: {result.message}")

    params = result.x
    home_adv = params[0]
    rho = params[1]
    attacks = {teams[i]: float(params[2 + i]) for i in range(n)}
    defenses = {teams[i]: float(params[2 + n + i]) for i in range(n)}

    # Store in DB (clear stale params from prior fits first)
    conn = get_connection()
    cur = conn.cursor()
    now = time.time()
    cur.execute("DELETE FROM team_model_params")
    for team_name in teams:
        cur.execute("""
            INSERT OR REPLACE INTO team_model_params (team_name, attack, defense, fitted_at)
            VALUES (?, ?, ?, ?)
        """, (team_name, attacks[team_name], defenses[team_name], now))

    cur.execute("""
        INSERT OR REPLACE INTO model_globals (key, value, fitted_at)
        VALUES ('home_adv', ?, ?), ('rho', ?, ?)
    """, (float(home_adv), now, float(rho), now))

    conn.commit()
    conn.close()

    return {
        "teams": teams,
        "attacks": attacks,
        "defenses": defenses,
        "home_adv": float(home_adv),
        "rho": float(rho),
        "n_matches": len(matches),
    }


def predict_match(
    home_team: str,
    away_team: str,
    model_params: Optional[Dict] = None,
) -> Dict:
    """
    Compute win/draw/loss, BTTS, O1.5, O2.5 probabilities.
    Falls back to DB-cached params if model_params not provided.
    Returns default (50/25/25) if team not in model.
    """
    if model_params is None:
        model_params = _load_params_from_db()

    if model_params is None:
        return _default_prediction()

    attacks = model_params.get("attacks", {})
    defenses = model_params.get("defenses", {})
    home_adv = model_params.get("home_adv", 0.1)
    rho = model_params.get("rho", 0.0)

    if home_team not in attacks or away_team not in attacks:
        return _default_prediction()

    lam_home = np.exp(home_adv + attacks[home_team] + defenses[away_team])
    lam_away = np.exp(attacks[away_team] + defenses[home_team])

    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    btts = 0.0
    over_1_5 = 0.0
    over_2_5 = 0.0

    score_matrix = np.zeros((MAX_GOALS + 1, MAX_GOALS + 1))

    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = (poisson.pmf(i, lam_home) *
                 poisson.pmf(j, lam_away) *
                 _dc_correction(i, j, lam_home, lam_away, rho))
            score_matrix[i, j] = max(p, 0)

    # Renormalize (DC correction can shift total slightly)
    total = score_matrix.sum()
    if total > 0:
        score_matrix /= total

    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = score_matrix[i, j]
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
            if i > 0 and j > 0:
                btts += p
            if i + j > 1:
                over_1_5 += p
            if i + j > 2:
                over_2_5 += p

    return {
        "home_win_pct": round(home_win * 100, 1),
        "draw_pct": round(draw * 100, 1),
        "away_win_pct": round(away_win * 100, 1),
        "btts_pct": round(btts * 100, 1),
        "over_1_5_pct": round(over_1_5 * 100, 1),
        "over_2_5_pct": round(over_2_5 * 100, 1),
        "expected_home_goals": round(float(lam_home), 2),
        "expected_away_goals": round(float(lam_away), 2),
        "home_attack": round(float(attacks[home_team]), 3),
        "home_defense": round(float(defenses[home_team]), 3),
        "away_attack": round(float(attacks[away_team]), 3),
        "away_defense": round(float(defenses[away_team]), 3),
    }


def _default_prediction() -> Dict:
    return {
        "home_win_pct": 40.0,
        "draw_pct": 25.0,
        "away_win_pct": 35.0,
        "btts_pct": 45.0,
        "over_1_5_pct": 70.0,
        "over_2_5_pct": 45.0,
        "expected_home_goals": 1.3,
        "expected_away_goals": 1.1,
        "home_attack": 0.0,
        "home_defense": 0.0,
        "away_attack": 0.0,
        "away_defense": 0.0,
    }


def _load_params_from_db() -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT team_name, attack, defense FROM team_model_params")
    rows = cur.fetchall()

    if not rows:
        conn.close()
        return None

    attacks = {}
    defenses = {}
    for r in rows:
        attacks[r["team_name"]] = r["attack"]
        defenses[r["team_name"]] = r["defense"]

    home_adv = 0.1
    rho = 0.01
    try:
        cur.execute("SELECT key, value FROM model_globals WHERE key IN ('home_adv', 'rho')")
        for r in cur.fetchall():
            if r["key"] == "home_adv":
                home_adv = r["value"]
            elif r["key"] == "rho":
                rho = r["value"]
    except Exception:
        pass

    conn.close()
    return {"attacks": attacks, "defenses": defenses, "home_adv": home_adv, "rho": rho}


def compute_and_store_prediction(fixture_id: int, home_team: str, away_team: str) -> Optional[Dict]:
    """Compute prediction and cache in DB."""
    pred = predict_match(home_team, away_team)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO predictions
        (fixture_id, home_win_pct, draw_pct, away_win_pct, btts_pct,
         over_1_5_pct, over_2_5_pct, expected_home_goals, expected_away_goals,
         home_attack, home_defense, away_attack, away_defense, computed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        fixture_id,
        pred["home_win_pct"], pred["draw_pct"], pred["away_win_pct"],
        pred["btts_pct"], pred["over_1_5_pct"], pred["over_2_5_pct"],
        pred["expected_home_goals"], pred["expected_away_goals"],
        pred["home_attack"], pred["home_defense"],
        pred["away_attack"], pred["away_defense"],
        time.time()
    ))
    conn.commit()
    conn.close()

    pred["fixture_id"] = fixture_id
    return pred


def load_historical_from_db() -> List[Dict]:
    """Load all historical results for model fitting."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT home_team, away_team, home_goals, away_goals, days_ago, tournament
        FROM historical_results
        WHERE days_ago IS NOT NULL
        ORDER BY days_ago ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
