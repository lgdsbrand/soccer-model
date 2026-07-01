from fastapi import APIRouter, HTTPException
from typing import List
from app.database import get_connection
from app.services import llm
from app.services.predictions import get_attack_xg_ratings

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/", response_model=List[dict])
async def get_teams():
    """Get all WC2026 teams."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, s.points, s.played, s.won, s.drawn, s.lost,
               s.goals_for, s.goals_against, s.rank as group_rank
        FROM teams t
        LEFT JOIN standings s ON t.id = s.team_id
        WHERE t.name != 'TBD' AND t.group_letter IS NOT NULL
        ORDER BY t.group_letter ASC, s.rank ASC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    ratings = get_attack_xg_ratings()
    for row in rows:
        rating = ratings.get(row["name"]) or {}
        row["attack_rating"] = rating.get("attack_rating")
        row["xg_rating"] = rating.get("xg_rating")
        row["xga_rating"] = rating.get("xga_rating")
        row["goals_per_game"] = rating.get("goals_per_game")
        row["goals_allowed_per_game"] = rating.get("goals_allowed_per_game")

    return rows


@router.get("/{team_id}", response_model=dict)
async def get_team(team_id: int):
    """Get team detail with players and style."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
    team = cur.fetchone()
    if not team:
        conn.close()
        raise HTTPException(status_code=404, detail="Team not found")

    team_dict = dict(team)

    rating = get_attack_xg_ratings().get(team_dict["name"]) or {}
    team_dict["attack_rating"] = rating.get("attack_rating")
    team_dict["xg_rating"] = rating.get("xg_rating")
    team_dict["xga_rating"] = rating.get("xga_rating")
    team_dict["goals_per_game"] = rating.get("goals_per_game")
    team_dict["goals_allowed_per_game"] = rating.get("goals_allowed_per_game")

    # Players
    cur.execute("SELECT * FROM players WHERE team_id = ? ORDER BY position, number", (team_id,))
    team_dict["players"] = [dict(p) for p in cur.fetchall()]

    # Standing
    cur.execute("SELECT * FROM standings WHERE team_id = ?", (team_id,))
    standing = cur.fetchone()
    team_dict["standing"] = dict(standing) if standing else None

    # Upcoming fixture
    import time
    cur.execute("""
        SELECT f.id, f.date_utc, f.round, f.status,
               ht.name as home_name, at.name as away_name
        FROM fixtures f
        JOIN teams ht ON f.home_team_id = ht.id
        JOIN teams at ON f.away_team_id = at.id
        WHERE (f.home_team_id = ? OR f.away_team_id = ?)
          AND f.date_utc > ? AND f.status IN ('NS', 'TBD')
        ORDER BY f.date_utc ASC LIMIT 1
    """, (team_id, team_id, time.time()))
    next_fix = cur.fetchone()
    team_dict["next_fixture"] = dict(next_fix) if next_fix else None

    # Advancement probabilities
    cur.execute("SELECT * FROM advancement_probs WHERE team_id = ?", (team_id,))
    adv = cur.fetchone()
    team_dict["advancement"] = dict(adv) if adv else None

    conn.close()

    # Style of play (LLM-cached)
    if not team_dict.get("style_of_play"):
        team_dict["style_of_play"] = await llm.get_style_of_play(
            team_dict["name"], team_dict.get("coach")
        )

    # Key players
    squad_names = [p["name"] for p in team_dict["players"][:20]]
    team_dict["key_players"] = await llm.get_key_players(team_dict["name"], squad_names)

    return team_dict


@router.get("/{team_id}/players", response_model=List[dict])
async def get_team_players(team_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE team_id = ? ORDER BY position, number", (team_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


@router.get("/players/top", response_model=List[dict])
async def get_top_players(limit: int = 100):
    """Squad players for all WC2026 teams, ordered by goals then name."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, t.name as team_name, t.logo as team_logo
        FROM players p
        JOIN teams t ON p.team_id = t.id
        WHERE t.group_letter IS NOT NULL AND t.name != 'TBD'
        ORDER BY t.name ASC,
                 CASE p.position
                   WHEN 'Goalkeeper' THEN 1
                   WHEN 'Defence'    THEN 2
                   WHEN 'Midfield'   THEN 3
                   WHEN 'Offence'    THEN 4
                   ELSE 5
                 END ASC,
                 p.name ASC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
