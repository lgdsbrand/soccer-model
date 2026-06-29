from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Team(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    country: Optional[str] = None
    logo: Optional[str] = None
    group_letter: Optional[str] = None
    coach: Optional[str] = None
    formation_default: Optional[str] = None
    style_of_play: Optional[str] = None


class Player(BaseModel):
    id: int
    name: str
    age: Optional[int] = None
    nationality: Optional[str] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    number: Optional[int] = None
    photo: Optional[str] = None
    club: Optional[str] = None
    club_logo: Optional[str] = None
    is_key_player: bool = False
    goals_intl: int = 0
    assists_intl: int = 0


class MatchResult(BaseModel):
    fixture_id: int
    date_utc: float
    home_team: Team
    away_team: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    round: str


class MatchStats(BaseModel):
    team_id: int
    shots_total: Optional[int] = None
    shots_on_target: Optional[int] = None
    corners: Optional[int] = None
    fouls: Optional[int] = None
    yellow_cards: Optional[int] = None
    possession: Optional[str] = None
    passes_total: Optional[int] = None


class LineupPlayer(BaseModel):
    player_id: Optional[int] = None
    player_name: str
    player_number: Optional[int] = None
    player_pos: Optional[str] = None
    player_grid: Optional[str] = None
    is_substitute: bool = False
    is_predicted: bool = False
    club: Optional[str] = None
    club_logo: Optional[str] = None


class Lineup(BaseModel):
    team_id: int
    team_name: str
    formation: Optional[str] = None
    starters: List[LineupPlayer] = []
    substitutes: List[LineupPlayer] = []
    is_confirmed: bool = False


class Prediction(BaseModel):
    fixture_id: int
    home_win_pct: float
    draw_pct: float
    away_win_pct: float
    btts_pct: float
    over_1_5_pct: float
    over_2_5_pct: float
    expected_home_goals: float
    expected_away_goals: float


class AdvancementProb(BaseModel):
    team_id: int
    team_name: str
    team_logo: Optional[str] = None
    group_letter: Optional[str] = None
    r32_pct: float = 0
    r16_pct: float = 0
    qf_pct: float = 0
    sf_pct: float = 0
    final_pct: float = 0
    winner_pct: float = 0


class Weather(BaseModel):
    venue_city: str
    temperature_c: float
    feels_like_c: float
    description: str
    humidity: int
    wind_speed_ms: float
    icon: str


class Standing(BaseModel):
    rank: int
    team_id: int
    team_name: str
    team_logo: Optional[str] = None
    group_letter: str
    points: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_diff: int
    form: Optional[str] = None


class MatchCard(BaseModel):
    fixture_id: int
    round: str
    date_utc: float
    status: str
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    home_team: Team
    away_team: Team
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    weather: Optional[Weather] = None
    home_last5: List[MatchResult] = []
    away_last5: List[MatchResult] = []
    home_lineup: Optional[Lineup] = None
    away_lineup: Optional[Lineup] = None
    home_stats_avg: Optional[MatchStats] = None
    away_stats_avg: Optional[MatchStats] = None
    home_key_players: List[Player] = []
    away_key_players: List[Player] = []
    prediction: Optional[Prediction] = None
    ai_analysis: Optional[str] = None
    recommended_play: Optional[str] = None


class TournamentWinner(BaseModel):
    team_id: int
    team_name: str
    team_logo: Optional[str] = None
    win_probability: float


class HomePageData(BaseModel):
    next_match: Optional[MatchCard] = None
    tournament_winners: List[TournamentWinner] = []
    top_players: List[Player] = []
    recent_results: List[MatchResult] = []
    total_goals: int = 0
    matches_played: int = 0
    matches_remaining: int = 0
