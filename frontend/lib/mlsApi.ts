import { apiFetch } from "./api";
import type { Fixture, FixtureDetail } from "./api";

// Must match backend/app/config.py's `mls_season` — `mls_fixtures` also holds
// 3 backfilled historical seasons (2023-2025, for head-to-head), so callers
// that want "current" fixtures need to scope to this season explicitly
// rather than relying on ORDER BY date_utc ASC LIMIT n, which otherwise
// returns 2023 season openers first.
export const MLS_CURRENT_SEASON = 2026;

export const mlsApi = {
  fixtures: (params?: string) => apiFetch<Fixture[]>(`/mls/fixtures/${params ? "?" + params : ""}`),
  fixture: (id: number) => apiFetch<FixtureDetail>(`/mls/fixtures/${id}`),
  standings: () => apiFetch<Record<string, MlsStanding[]>>("/mls/standings/"),
  topPlays: () => apiFetch<MlsTopPlaysResponse>("/mls/fixtures/top-plays"),
};

export interface MlsTopPlay {
  fixture_id: number;
  date_utc: number;
  home_name: string;
  home_logo?: string;
  away_name: string;
  away_logo?: string;
  value: number;
}

export interface MlsTopPlays {
  btts: MlsTopPlay | null;
  over_1_5: MlsTopPlay | null;
  over_2_5: MlsTopPlay | null;
}

// One day's worth of Top Plays — `date` is an ET date string (YYYY-MM-DD).
export interface MlsTopPlaysDay extends MlsTopPlays {
  date: string;
}

// The backend scans forward across the next couple weeks and returns one
// entry per day that actually has plays (empty days skipped), up to 5 days —
// so the dashboard always has something to show even on a day with no games.
export interface MlsTopPlaysResponse {
  days: MlsTopPlaysDay[];
}

// MLS-only type: conference-based standings, not the group-stage-shaped
// `Standing` type (group_letter, top-2-qualify framing) used for the World Cup.
export interface MlsStanding {
  rank: number;
  team_id: number;
  team_name: string;
  team_logo?: string;
  team_code?: string;
  conference: string;
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
