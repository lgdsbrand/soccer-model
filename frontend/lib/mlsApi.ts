import { apiFetch } from "./api";
import type { Fixture, FixtureDetail } from "./api";

export const mlsApi = {
  fixtures: (params?: string) => apiFetch<Fixture[]>(`/mls/fixtures/${params ? "?" + params : ""}`),
  fixture: (id: number) => apiFetch<FixtureDetail>(`/mls/fixtures/${id}`),
  standings: () => apiFetch<Record<string, MlsStanding[]>>("/mls/standings/"),
};

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
