const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
    next: { revalidate: 60 }, // 1-min cache for server components
  });
  if (!res.ok) throw new Error(`API ${path} returned ${res.status}`);
  return res.json();
}

export const api = {
  home: () => apiFetch<HomeData>("/insights/home"),
  fixtures: (params?: string) => apiFetch<Fixture[]>(`/fixtures/${params ? "?" + params : ""}`),
  fixture: (id: number) => apiFetch<FixtureDetail>(`/fixtures/${id}`),
  today: () => apiFetch<Fixture[]>("/fixtures/today"),
  next: () => apiFetch<Fixture>("/fixtures/next"),
  standings: () => apiFetch<Record<string, Standing[]>>("/standings/groups"),
  bracket: () => apiFetch<Fixture[]>("/standings/bracket"),
  teams: () => apiFetch<Team[]>("/teams/"),
  team: (id: number) => apiFetch<TeamDetail>(`/teams/${id}`),
  topPlayers: (limit = 100) => apiFetch<Player[]>(`/teams/players/top?limit=${limit}`),
  advancement: () => apiFetch<AdvancementProb[]>("/predictions/advancement"),
  tournamentWinners: () => apiFetch<TournamentWinner[]>("/predictions/tournament-winners"),
};

// Types
export interface Team {
  id: number;
  name: string;
  code?: string;
  logo?: string;
  group_letter?: string;
  coach?: string;
  style_of_play?: string;
  formation_default?: string;
  fifa_rank?: number;
}

export interface Fixture {
  id: number;
  round: string;
  date_utc: number;
  status: string;
  venue_name?: string;
  venue_city?: string;
  home_team_id: number;
  away_team_id: number;
  home_name: string;
  away_name: string;
  home_logo?: string;
  away_logo?: string;
  home_score?: number;
  away_score?: number;
  home_win_pct?: number;
  draw_pct?: number;
  away_win_pct?: number;
  btts_pct?: number;
  over_1_5_pct?: number;
  home_group?: string;
  away_group?: string;
  home_fifa_rank?: number;
  away_fifa_rank?: number;
}

export interface MatchStat {
  team_id: number;
  shots_total?: number;
  shots_on_target?: number;
  corners?: number;
  fouls?: number;
  yellow_cards?: number;
  red_cards?: number;
  possession?: string;
  passes_total?: number;
  passes_accuracy?: string;
  offsides?: number;
}

export interface FixtureDetail extends Fixture {
  weather?: Weather;
  home_last5: Fixture[];
  away_last5: Fixture[];
  lineups?: LineupEntry[];
  lineups_confirmed: boolean;
  home_stats_avg?: TeamStats;
  away_stats_avg?: TeamStats;
  home_match_stats?: MatchStat;
  away_match_stats?: MatchStat;
  home_key_players?: KeyPlayer[];
  away_key_players?: KeyPlayer[];
  prediction?: Prediction;
  ai_analysis?: string;
  recommended_play?: RecommendedPlay;
  home_coach?: string;
  away_coach?: string;
  home_formation?: string;
  away_formation?: string;
  home_style_of_play?: string;
  away_style_of_play?: string;
}

export interface Weather {
  venue_city: string;
  temperature_c: number;
  feels_like_c: number;
  description: string;
  humidity: number;
  wind_speed_ms: number;
  icon: string;
}

export interface Standing {
  rank: number;
  team_id: number;
  team_name: string;
  team_logo?: string;
  group_letter: string;
  points: number;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  goals_for: number;
  goals_against: number;
  goal_diff: number;
  form?: string;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality?: string;
  team_id?: number;
  position?: string;
  number?: number;
  photo?: string;
  club?: string;
  goals_intl: number;
  assists_intl: number;
  team_name?: string;
  team_logo?: string;
}

export interface KeyPlayer {
  name: string;
  position: string;
  role: string;
  club?: string;
}

export interface LineupEntry {
  fixture_id: number;
  team_id: number;
  formation?: string;
  player_name: string;
  player_number?: number;
  player_pos?: string;
  player_grid?: string;
  is_substitute: number;
  is_predicted: number;
  club?: string;
}

export interface TeamStats {
  shots_total?: number;
  shots_on_target?: number;
  corners?: number;
  fouls?: number;
  yellow_cards?: number;
}

export interface Prediction {
  home_win_pct: number;
  draw_pct: number;
  away_win_pct: number;
  btts_pct: number;
  over_1_5_pct: number;
  over_2_5_pct: number;
  expected_home_goals: number;
  expected_away_goals: number;
}

export interface RecommendedPlay {
  primary_bet: string;
  confidence: string;
  reasoning: string;
  alternative?: string;
}

export interface AdvancementProb {
  team_id: number;
  team_name: string;
  logo?: string;
  group_letter?: string;
  r32_pct: number;
  r16_pct: number;
  qf_pct: number;
  sf_pct: number;
  final_pct: number;
  winner_pct: number;
}

export interface TournamentWinner {
  team_id: number;
  team_name: string;
  logo?: string;
  group_letter?: string;
  winner_pct: number;
  final_pct: number;
  sf_pct: number;
}

export interface HomeData {
  next_match?: Fixture & {
    home_id: number;
    away_id: number;
    home_win_pct?: number;
    draw_pct?: number;
    away_win_pct?: number;
    btts_pct?: number;
    ai_analysis?: string;
  };
  today_matches: Fixture[];
  recent_results: Fixture[];
  winner_probabilities: TournamentWinner[];
  top_players: Player[];
  stats: {
    matches_played: number;
    total_goals: number;
    matches_remaining: number;
    avg_goals_per_match: number;
  };
}

export interface TeamDetail extends Team {
  players: Player[];
  standing?: Standing;
  next_fixture?: Fixture;
  advancement?: AdvancementProb;
  key_players?: KeyPlayer[];
}

export function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

export function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString("en-US", {
    hour: "2-digit", minute: "2-digit", timeZoneName: "short",
  });
}

export function getStatusLabel(status: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    NS: { label: "Upcoming", color: "#9898b8" },
    "1H": { label: "LIVE — 1st Half", color: "#00d084" },
    HT: { label: "Half Time", color: "#f5a623" },
    "2H": { label: "LIVE — 2nd Half", color: "#00d084" },
    ET: { label: "Extra Time", color: "#00d084" },
    P: { label: "Penalties", color: "#00d084" },
    FT: { label: "Full Time", color: "#5a5a7a" },
    AET: { label: "After Extra Time", color: "#5a5a7a" },
    PEN: { label: "Penalties", color: "#5a5a7a" },
    TBD: { label: "TBD", color: "#9898b8" },
  };
  return map[status] || { label: status, color: "#9898b8" };
}
