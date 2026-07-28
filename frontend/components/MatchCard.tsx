"use client";
import { useState } from "react";
import Link from "next/link";
import type { Fixture, FixtureDetail, Prediction, TeamSeasonStats, KeyPlayer, LineupEntry, MatchStat, TeamRecord, RecordSplit } from "@/lib/api";
import { getStatusLabel } from "@/lib/api";
import { LocalDate, LocalTime } from "@/components/LocalTime";

interface Props {
  fixture: FixtureDetail;
  compact?: boolean;
  basePath?: string;
  showRecommendedPlay?: boolean;
  showXg?: boolean;
  weatherStyle?: "icon" | "emoji";
}

const KNOCKOUT_ROUNDS = new Set([
  "Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final", "3rd Place",
]);

const FORM_COLORS: Record<"W" | "D" | "L", string> = { W: "#00d084", D: "#f5a623", L: "#ff4757" };

export default function MatchCard({ fixture, compact, basePath = "/matches", showRecommendedPlay = true, showXg = true, weatherStyle = "icon" }: Props) {
  const status = getStatusLabel(fixture.status);
  const pred = fixture.prediction;
  const isLive = ["1H", "2H", "HT", "ET", "P"].includes(fixture.status);
  const isFinished = ["FT", "AET", "PEN"].includes(fixture.status);
  // Explicit allowlist rather than "anything not Group Stage" — a blacklist
  // heuristic silently mis-tags any other competition's round label (e.g.
  // MLS's "Regular Season") as a draw-less knockout match, which would hide
  // a real draw_pct the odds-derived MLS predictions actually have.
  const isKnockout = KNOCKOUT_ROUNDS.has(fixture.round);

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      {/* Header: round + status */}
      <div style={{
        padding: "12px 20px",
        borderBottom: "1px solid var(--border)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        backgroundColor: "rgba(124, 92, 252, 0.06)",
      }}>
        <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {fixture.round}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {isLive && <div className="live-dot" style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "var(--accent-green)" }} />}
          <span style={{ fontSize: "12px", color: status.color, fontWeight: 600 }}>{status.label}</span>
        </div>
      </div>

      {/* Region — only shown separately when it isn't already embedded in
          venue_name (WC's venue_name already includes the city, e.g. "New
          York/New Jersey (East Rutherford)"; MLS's venue_name/venue_city are
          genuinely separate, "GEODIS Park" / "Nashville, Tennessee") */}
      {fixture.venue_city && !(fixture.venue_name && fixture.venue_name.includes(fixture.venue_city)) && (
        <div style={{ padding: "10px 20px 0", textAlign: "center", fontSize: "11px", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {fixture.venue_city}
        </div>
      )}

      {/* Teams + Score */}
      <div style={{ padding: "20px", display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Home */}
        <div style={{ flex: 1, minWidth: 0, textAlign: "center" }}>
          {fixture.home_logo && (
            <div style={{ position: "relative", width: "52px", margin: "0 auto 8px" }}>
              <img src={fixture.home_logo} alt={fixture.home_name}
                style={{ width: "52px", height: "52px", objectFit: "contain" }} />
              {fixture.home_fifa_rank != null && <FifaRankBadge rank={fixture.home_fifa_rank} />}
            </div>
          )}
          <div style={{ fontWeight: 700, fontSize: "16px" }}>{fixture.home_name}</div>
          {fixture.home_last5 && fixture.home_last5.length > 0 && (
            <FormBadges results={fixture.home_last5} teamId={fixture.home_team_id} />
          )}
          {fixture.home_group && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>Group {fixture.home_group}</div>
          )}
          {fixture.home_power_rank != null && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>Power Rank #{fixture.home_power_rank}</div>
          )}
        </div>

        {/* Score / VS */}
        <div style={{ textAlign: "center", minWidth: "80px" }}>
          {isFinished || isLive ? (
            <div style={{ fontSize: "32px", fontWeight: 800, fontVariantNumeric: "tabular-nums", letterSpacing: "-1px" }}>
              {fixture.home_score ?? 0} <span style={{ color: "var(--text-muted)" }}>-</span> {fixture.away_score ?? 0}
            </div>
          ) : (
            <>
              <div style={{ fontSize: "22px", fontWeight: 700, color: "var(--text-muted)" }}>VS</div>
              <div style={{ fontSize: "13px", color: "var(--accent-green)", marginTop: "4px" }}><LocalTime ts={fixture.date_utc} /></div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}><LocalDate ts={fixture.date_utc} /></div>
            </>
          )}
        </div>

        {/* Away */}
        <div style={{ flex: 1, minWidth: 0, textAlign: "center" }}>
          {fixture.away_logo && (
            <div style={{ position: "relative", width: "52px", margin: "0 auto 8px" }}>
              <img src={fixture.away_logo} alt={fixture.away_name}
                style={{ width: "52px", height: "52px", objectFit: "contain" }} />
              {fixture.away_fifa_rank != null && <FifaRankBadge rank={fixture.away_fifa_rank} />}
            </div>
          )}
          <div style={{ fontWeight: 700, fontSize: "16px" }}>{fixture.away_name}</div>
          {fixture.away_last5 && fixture.away_last5.length > 0 && (
            <FormBadges results={fixture.away_last5} teamId={fixture.away_team_id} />
          )}
          {fixture.away_power_rank != null && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>Power Rank #{fixture.away_power_rank}</div>
          )}
          {fixture.away_group && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>Group {fixture.away_group}</div>
          )}
        </div>
      </div>

      {/* Location + Weather */}
      {(fixture.venue_name || fixture.venue_city || fixture.weather) && (
        <div className="weather-row" style={{ padding: "0 20px 12px", display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          {(fixture.venue_name || fixture.venue_city) && (
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              📍 {fixture.venue_name || fixture.venue_city}
            </span>
          )}
          {fixture.weather && (
            <>
              {(fixture.venue_name || fixture.venue_city) && <span style={{ color: "var(--border)" }}>·</span>}
              {weatherStyle === "emoji" ? (
                <span className="weather-emoji" style={{ fontSize: "18px", lineHeight: 1 }}>{fixture.weather.emoji}</span>
              ) : (
                <img
                  src={`https://openweathermap.org/img/wn/${fixture.weather.icon}.png`}
                  alt={fixture.weather.description}
                  style={{ width: "18px", height: "18px", verticalAlign: "middle" }}
                />
              )}
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                {fixture.weather.temperature_c.toFixed(1)}°C, {fixture.weather.description}
              </span>
              <span style={{ color: "var(--border)" }}>·</span>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>💧 {fixture.weather.humidity}%</span>
              <span style={{ color: "var(--border)" }}>·</span>
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>💨 {fixture.weather.wind_speed_ms.toFixed(1)} m/s</span>
            </>
          )}
        </div>
      )}

      {compact && (
        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", textAlign: "center" }}>
          <Link href={`${basePath}/${fixture.id}`} style={{
            fontSize: "13px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600
          }}>View Full Analysis →</Link>
        </div>
      )}

      {!compact && (
        <>
          {/* Win % Bars */}
          {pred && (
            <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "10px", fontWeight: 600 }}>WIN PROBABILITY</div>
              <WinProbBar
                homeName={fixture.home_name}
                homeWin={pred.home_win_pct}
                draw={pred.draw_pct}
                awayWin={pred.away_win_pct}
                awayName={fixture.away_name}
                knockout={isKnockout}
              />
              {/* WC (Dixon-Coles) always has O1.5/O2.5/xG, never O3.5. MLS (odds-derived) has
                  O1.5/O2.5/O3.5 from The Odds API's alternate_totals market (see odds_api.py),
                  never xG (not derivable from odds markets) — each gated on presence rather
                  than assumed, and the grid sizes itself to however many actually render. */}
              {(() => {
                const chips: { label: string; value: string; color: string }[] = [
                  { label: "BTTS", value: `${pred.btts_pct}%`, color: "var(--accent-purple)" },
                ];
                if (pred.over_1_5_pct != null) chips.push({ label: "O1.5 Goals", value: `${pred.over_1_5_pct}%`, color: "var(--accent-blue, #3d9df3)" });
                if (pred.over_2_5_pct != null) chips.push({ label: "O2.5 Goals", value: `${pred.over_2_5_pct}%`, color: "var(--accent-gold)" });
                if (pred.over_3_5_pct != null) chips.push({ label: "O3.5 Goals", value: `${pred.over_3_5_pct}%`, color: "var(--accent-teal, #2dd4bf)" });
                if (pred.expected_home_goals != null) chips.push({ label: "xG Home", value: pred.expected_home_goals.toFixed(2), color: "var(--accent-green)" });
                return (
                  <div style={{ display: "grid", gridTemplateColumns: `repeat(${chips.length}, 1fr)`, gap: "8px", marginTop: "16px" }}>
                    {chips.map(c => <StatChip key={c.label} label={c.label} value={c.value} color={c.color} />)}
                  </div>
                );
              })()}
            </div>
          )}

          {/* Important Stats: Attack Strength, Goals/xG, Goals Allowed/xGA, and/or
              season stats (corners/shots/fouls) — AttackRatingSection itself already
              filters out any row with no data on both sides, so this only needs to
              gate on "is there anything at all to show" rather than specifically the
              Dixon-Coles-derived fields (MLS matches have team stats but no
              Dixon-Coles rating, since MLS predictions are odds-market-derived). */}
          {(fixture.home_attack_rating != null || fixture.away_attack_rating != null ||
            fixture.home_team_stats != null || fixture.away_team_stats != null) && (
            <AttackRatingSection
              homeName={fixture.home_name}
              awayName={fixture.away_name}
              homeAttack={fixture.home_attack_rating}
              awayAttack={fixture.away_attack_rating}
              homeGoals={fixture.home_goals_per_game}
              awayGoals={fixture.away_goals_per_game}
              // WC's Dixon-Coles xg_rating takes priority; falls back to MLS's
              // real per-game xG (fixture.home_team_stats.xg) when absent —
              // the two never both exist for the same fixture, so this is
              // just "use whichever league actually set one."
              homeXg={fixture.home_xg_rating ?? fixture.home_team_stats?.xg}
              awayXg={fixture.away_xg_rating ?? fixture.away_team_stats?.xg}
              homeGoalsAllowed={fixture.home_goals_allowed_per_game}
              awayGoalsAllowed={fixture.away_goals_allowed_per_game}
              homeXga={fixture.home_xga_rating ?? fixture.home_team_stats?.xga}
              awayXga={fixture.away_xga_rating ?? fixture.away_team_stats?.xga}
              homeTeamStats={fixture.home_team_stats}
              awayTeamStats={fixture.away_team_stats}
              showXg={showXg}
            />
          )}

          {/* Last 10 (or Last 5 for WC) / Head to Head — unified tabbed section.
              H2H tab only appears when fixture.head_to_head is set (MLS only). */}
          {(fixture.home_last5?.length > 0 || fixture.away_last5?.length > 0 || (fixture.head_to_head?.length ?? 0) > 0) && (
            <GameHistorySection
              homeTeamId={fixture.home_team_id}
              homeName={fixture.home_name}
              homeGames={fixture.home_last5 ?? []}
              awayTeamId={fixture.away_team_id}
              awayName={fixture.away_name}
              awayGames={fixture.away_last5 ?? []}
              headToHead={fixture.head_to_head}
            />
          )}

          {/* Team Records — MLS only; fixture.home_team_record/away_team_record undefined for WC */}
          {fixture.home_team_record && fixture.away_team_record && (
            <TeamRecordsSection
              homeName={fixture.home_name}
              awayName={fixture.away_name}
              homeRecord={fixture.home_team_record}
              awayRecord={fixture.away_team_record}
            />
          )}

          {/* Match Stats (for finished matches) */}
          {isFinished && (fixture.home_match_stats || fixture.away_match_stats) ? (
            <MatchStatsSection
              home={fixture.home_match_stats}
              away={fixture.away_match_stats}
              homeName={fixture.home_name}
              awayName={fixture.away_name}
            />
          ) : isFinished ? (
            <div style={{ padding: "14px 20px", borderTop: "1px solid var(--border)", display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>📊</span>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Detailed match stats not yet available for this match</span>
            </div>
          ) : null}

          {/* Lineups */}
          {fixture.lineups && fixture.lineups.length > 0 && (
            <LineupSection
              lineups={fixture.lineups}
              homeId={fixture.home_team_id}
              awayId={fixture.away_team_id}
              homeName={fixture.home_name}
              awayName={fixture.away_name}
              homeFormation={fixture.home_formation}
              awayFormation={fixture.away_formation}
              confirmed={fixture.lineups_confirmed}
            />
          )}

          {/* Key Players */}
          {(fixture.home_key_players?.length || fixture.away_key_players?.length) ? (
            <KeyPlayersSection
              homePlayers={fixture.home_key_players || []}
              awayPlayers={fixture.away_key_players || []}
              homeName={fixture.home_name}
              awayName={fixture.away_name}
            />
          ) : null}

          {/* Style of Play */}
          {(fixture.home_style_of_play || fixture.away_style_of_play) && (
            <StyleOfPlaySection
              homeStyle={fixture.home_style_of_play}
              awayStyle={fixture.away_style_of_play}
              homeName={fixture.home_name}
              awayName={fixture.away_name}
            />
          )}

          {/* AI Analysis */}
          {fixture.ai_analysis && (
            <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "10px", fontWeight: 600 }}>🤖 AI ANALYSIS</div>
              <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
                {fixture.ai_analysis}
              </p>
            </div>
          )}

          {/* Recommended Play — suppressed entirely (not just "no data yet")
              where the caller knows nothing will ever generate one, e.g. MLS,
              which doesn't have this feature. Showing the "generating..."
              placeholder there would be misleading — it implies a background
              job is running when none is. */}
          {showRecommendedPlay && (fixture.recommended_play
            ? <RecommendedPlaySection play={fixture.recommended_play} />
            : (
              <div style={{ borderTop: "1px solid var(--border)", paddingTop: "16px", marginTop: "8px" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
                  Recommended Play
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 14px", borderRadius: "8px", border: "1px solid var(--border)", backgroundColor: "rgba(255,255,255,0.02)" }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: "var(--accent-purple)", flexShrink: 0, animation: "pulse-green 1.5s ease-in-out infinite" }} />
                  <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>Generating recommendation — refresh in a few seconds</span>
                </div>
              </div>
            )
          )}
        </>
      )}
    </div>
  );
}

function WinProbBar({ homeName, homeWin, draw, awayWin, awayName, knockout }: {
  homeName: string; homeWin: number; draw: number; awayWin: number; awayName: string; knockout?: boolean;
}) {
  const total = knockout ? homeWin + awayWin : homeWin + draw + awayWin;
  const h = Math.round((homeWin / total) * 100);
  const a = knockout ? 100 - h : Math.round((awayWin / total) * 100);
  const d = knockout ? 0 : 100 - h - a;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "8px" }}>
        <span style={{ color: "var(--accent-green)", fontWeight: 700 }}>{h}%</span>
        {!knockout && <span style={{ color: "var(--text-muted)" }}>Draw {d}%</span>}
        <span style={{ color: "var(--accent-purple)", fontWeight: 700 }}>{a}%</span>
      </div>
      <div style={{ height: "10px", borderRadius: "5px", overflow: "hidden", display: "flex" }}>
        <div style={{ width: `${h}%`, backgroundColor: "var(--accent-green)" }} />
        {!knockout && <div style={{ width: `${d}%`, backgroundColor: "var(--border)" }} />}
        <div style={{ width: `${a}%`, backgroundColor: "var(--accent-purple)" }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--text-muted)", marginTop: "4px" }}>
        <span>{homeName}</span>
        <span>{awayName}</span>
      </div>
    </div>
  );
}

function FifaRankBadge({ rank }: { rank: number }) {
  return (
    <span
      title={`FIFA Rank #${rank}`}
      style={{
        position: "absolute", bottom: "-4px", right: "-10px",
        fontSize: "9px", fontWeight: 800, color: "var(--text-primary)",
        backgroundColor: "var(--accent-gold)", padding: "2px 5px", borderRadius: "8px",
        border: "2px solid var(--bg-card)", lineHeight: 1, whiteSpace: "nowrap",
      }}>
      FIFA #{rank}
    </span>
  );
}

function StatChip({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ textAlign: "center", padding: "10px", backgroundColor: "rgba(255,255,255,0.03)", borderRadius: "8px", border: "1px solid var(--border)" }}>
      <div style={{ fontSize: "15px", fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px", textTransform: "uppercase", letterSpacing: "0.3px" }}>{label}</div>
    </div>
  );
}

function FormBadges({ results, teamId }: { results: any[]; teamId: number }) {
  const shown = results.slice(0, 5);
  return (
    <div style={{ display: "flex", justifyContent: "center", gap: "3px", marginTop: "6px" }}>
      {shown.map((r, i) => {
        const isHome = r.home_team_id === teamId;
        const gs = isHome ? r.home_score : r.away_score;
        const gc = isHome ? r.away_score : r.home_score;
        const outcome = gs > gc ? "W" : gs === gc ? "D" : "L";
        return (
          <span key={i} style={{
            width: "17px", height: "17px", borderRadius: "3px", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "9px", fontWeight: 800, color: "#fff",
            backgroundColor: FORM_COLORS[outcome],
          }}>{outcome}</span>
        );
      })}
    </div>
  );
}

// Unified Last-N / Head-to-Head section: 3 tabs (home team / away team / H2H,
// H2H only present when the caller passes headToHead — MLS only) switch which
// game list the record-summary and table below are computed from. Replaces
// the old always-both-columns FormRow/HeadToHeadSection card-list layout with
// a single compact Date/Matchup/Score table per Tyler's reference screenshot
// (an existing MLB product of his). Spread/Total columns from that reference
// are deliberately omitted: odds_api.py only ever stores odds for upcoming
// (status='NS') fixtures, so there's no real historical spread/total data for
// any finished game — showing those columns would mean fabricating numbers.
function GameHistorySection({ homeTeamId, homeName, homeGames, awayTeamId, awayName, awayGames, headToHead }: {
  homeTeamId: number; homeName: string; homeGames: Fixture[];
  awayTeamId: number; awayName: string; awayGames: Fixture[];
  headToHead?: Fixture[];
}) {
  const hasH2h = (headToHead?.length ?? 0) > 0;
  const [tab, setTab] = useState<"home" | "away" | "h2h">("home");
  const activeTab = tab === "h2h" && !hasH2h ? "home" : tab;

  const gameCount = Math.max(homeGames.length, awayGames.length, headToHead?.length ?? 0);
  const activeGames = activeTab === "home" ? homeGames : activeTab === "away" ? awayGames : (headToHead ?? []);
  const perspectiveTeamId = activeTab === "home" ? homeTeamId : activeTab === "away" ? awayTeamId : null;

  let recordChips: { label: string; value: string; color: string }[];
  if (activeTab === "h2h") {
    let homeWins = 0, awayWins = 0, draws = 0;
    for (const r of headToHead ?? []) {
      const homeSideIsHomeTeam = r.home_team_id === homeTeamId;
      const refGoals = homeSideIsHomeTeam ? r.home_score : r.away_score;
      const oppGoals = homeSideIsHomeTeam ? r.away_score : r.home_score;
      if ((refGoals ?? 0) > (oppGoals ?? 0)) homeWins++;
      else if (refGoals === oppGoals) draws++;
      else awayWins++;
    }
    recordChips = [
      { label: `${homeName} Wins`, value: String(homeWins), color: "var(--accent-green)" },
      { label: "Draws", value: String(draws), color: "var(--accent-gold)" },
      { label: `${awayName} Wins`, value: String(awayWins), color: "var(--accent-purple)" },
    ];
  } else {
    let w = 0, d = 0, l = 0;
    for (const r of activeGames) {
      const isHome = r.home_team_id === perspectiveTeamId;
      const gs = isHome ? r.home_score : r.away_score;
      const gc = isHome ? r.away_score : r.home_score;
      if ((gs ?? 0) > (gc ?? 0)) w++; else if (gs === gc) d++; else l++;
    }
    recordChips = [
      { label: "Won", value: String(w), color: FORM_COLORS.W },
      { label: "Drawn", value: String(d), color: FORM_COLORS.D },
      { label: "Lost", value: String(l), color: FORM_COLORS.L },
    ];
  }

  const tabs: { key: "home" | "away" | "h2h"; label: string }[] = [
    { key: "home", label: homeName },
    { key: "away", label: awayName },
    ...(hasH2h ? [{ key: "h2h" as const, label: "H2H" }] : []),
  ];

  return (
    <div style={{ borderTop: "1px solid var(--border)" }}>
      <div style={{ padding: "16px 20px 0", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px" }}>
          {gameCount > 0 ? `Last ${gameCount} Games` : "Game History"}
        </div>
        <div className="game-history-tabs" style={{ display: "flex", gap: "6px", overflowX: "auto" }}>
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                fontSize: "11px", fontWeight: 700, padding: "5px 10px", borderRadius: "999px",
                border: `1px solid ${activeTab === t.key ? "var(--accent-purple)" : "var(--border)"}`,
                backgroundColor: activeTab === t.key ? "rgba(124,92,252,0.15)" : "transparent",
                color: activeTab === t.key ? "var(--accent-purple)" : "var(--text-muted)",
                cursor: "pointer", flexShrink: 0, maxWidth: "130px",
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "14px 20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px", marginBottom: "14px" }}>
          {recordChips.map(c => <StatChip key={c.label} label={c.label} value={c.value} color={c.color} />)}
        </div>

        {activeGames.length === 0 ? (
          <div style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "center", padding: "12px 0" }}>No games yet</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ ...thStyle, textAlign: "left" }}>Date</th>
                  <th style={{ ...thStyle, textAlign: "left" }}>Matchup</th>
                  <th style={{ ...thStyle, textAlign: "right" }}>Score</th>
                </tr>
              </thead>
              <tbody>
                {activeGames.map((r, i) => {
                  let homeColor = "var(--text-secondary)", awayColor = "var(--text-secondary)";
                  let homeWeight = 500, awayWeight = 500;
                  if (activeTab === "h2h") {
                    homeColor = r.home_team_id === homeTeamId ? "var(--accent-green)" : "var(--accent-purple)";
                    awayColor = r.away_team_id === homeTeamId ? "var(--accent-green)" : "var(--accent-purple)";
                    homeWeight = (r.home_score ?? 0) > (r.away_score ?? 0) ? 800 : 500;
                    awayWeight = (r.away_score ?? 0) > (r.home_score ?? 0) ? 800 : 500;
                  } else {
                    const isHome = r.home_team_id === perspectiveTeamId;
                    const gs = isHome ? r.home_score : r.away_score;
                    const gc = isHome ? r.away_score : r.home_score;
                    const outcome = (gs ?? 0) > (gc ?? 0) ? "W" : gs === gc ? "D" : "L";
                    const color = FORM_COLORS[outcome];
                    if (isHome) { homeColor = color; homeWeight = 800; } else { awayColor = color; awayWeight = 800; }
                  }
                  return (
                    <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                      <td style={{ ...tdStyle, color: "var(--text-muted)", fontSize: "11px", whiteSpace: "nowrap" }}>
                        {r.date_utc ? <LocalDate ts={r.date_utc} short /> : ""}
                      </td>
                      <td style={{ ...tdStyle, whiteSpace: "nowrap" }} title={`${r.home_name ?? "?"} @ ${r.away_name ?? "?"}`}>
                        <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                          {r.home_logo && <img src={r.home_logo} alt="" style={{ width: 14, height: 14, objectFit: "contain", flexShrink: 0 }} />}
                          <span style={{ color: homeColor, fontWeight: homeWeight, fontSize: "12px" }}>{r.home_code ?? r.home_name ?? "?"}</span>
                          <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>@</span>
                          {r.away_logo && <img src={r.away_logo} alt="" style={{ width: 14, height: 14, objectFit: "contain", flexShrink: 0 }} />}
                          <span style={{ color: awayColor, fontWeight: awayWeight, fontSize: "12px" }}>{r.away_code ?? r.away_name ?? "?"}</span>
                        </div>
                      </td>
                      <td style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums", fontWeight: 800, fontSize: "13px", whiteSpace: "nowrap" }}>
                        {r.home_score ?? "?"}-{r.away_score ?? "?"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const thStyle = { fontSize: "10px", color: "var(--text-muted)", textTransform: "uppercase" as const, letterSpacing: "0.5px", padding: "0 6px 8px", fontWeight: 700 as const };
const tdStyle = { padding: "8px 6px" };

function TeamRecordsSection({ homeName, awayName, homeRecord, awayRecord }: {
  homeName: string; awayName: string; homeRecord: TeamRecord; awayRecord: TeamRecord;
}) {
  const fmt = (r: RecordSplit) => `${r.won}-${r.drawn}-${r.lost}`;

  const recordRows = [
    { label: "Record (All)", homeText: fmt(homeRecord.all), awayText: fmt(awayRecord.all) },
    { label: "Record (Home)", homeText: fmt(homeRecord.home), awayText: fmt(awayRecord.home) },
    { label: "Record (Away)", homeText: fmt(homeRecord.away), awayText: fmt(awayRecord.away) },
  ];

  const pointsRows = [
    { label: "Points (All)", homeVal: homeRecord.all.points, awayVal: awayRecord.all.points },
    { label: "Points (Home)", homeVal: homeRecord.home.points, awayVal: awayRecord.home.points },
    { label: "Points (Away)", homeVal: homeRecord.away.points, awayVal: awayRecord.away.points },
  ];

  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 600 }}>TEAM RECORDS</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
        <span style={{ fontSize: "12px", fontWeight: 700 }}>{homeName}</span>
        <span style={{ fontSize: "12px", fontWeight: 700 }}>{awayName}</span>
      </div>
      {recordRows.map(({ label, homeText, awayText }) => (
        <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-green)" }}>{homeText}</span>
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{label}</span>
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-purple)" }}>{awayText}</span>
        </div>
      ))}
      {pointsRows.map(({ label, homeVal, awayVal }) => {
        const total = homeVal + awayVal;
        const hPct = total > 0 ? (homeVal / total) * 100 : 50;
        const aPct = 100 - hPct;
        return (
          <div key={label} style={{ marginBottom: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-green)" }}>{homeVal}</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{label}</span>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-purple)" }}>{awayVal}</span>
            </div>
            <div style={{ height: "6px", borderRadius: "3px", overflow: "hidden", display: "flex" }}>
              <div style={{ width: `${hPct}%`, backgroundColor: "var(--accent-green)" }} />
              <div style={{ width: `${aPct}%`, backgroundColor: "var(--accent-purple)" }} />
            </div>
          </div>
        );
      })}
      <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--text-muted)", textAlign: "center" }}>
        Record shown as Won-Drawn-Lost
      </div>
    </div>
  );
}

function AttackRatingSection({
  homeName, awayName, homeAttack, awayAttack,
  homeGoals, awayGoals, homeXg, awayXg,
  homeGoalsAllowed, awayGoalsAllowed, homeXga, awayXga,
  homeTeamStats, awayTeamStats, showXg = true,
}: {
  homeName: string; awayName: string;
  homeAttack?: number; awayAttack?: number;
  homeGoals?: number; awayGoals?: number; homeXg?: number; awayXg?: number;
  homeGoalsAllowed?: number; awayGoalsAllowed?: number; homeXga?: number; awayXga?: number;
  homeTeamStats?: TeamSeasonStats; awayTeamStats?: TeamSeasonStats;
  showXg?: boolean;
}) {
  const fmt = (v?: number) => v != null ? v.toFixed(2) : "—";
  const fmtRating = (v?: number, rank?: number) => v != null ? `${v.toFixed(2)}${rank != null ? ` (#${rank})` : ""}` : "—";

  const rows = [
    {
      label: "Attack Strength", homeVal: homeAttack, awayVal: awayAttack,
      homeText: homeAttack ?? "—", awayText: awayAttack ?? "—",
    },
    // MLS only — opponent-adjusted strength rating derived from real xG data
    // (see mls_team_stats.py's _compute_ratings), distinct from WC's Attack
    // Strength above (Dixon-Coles derived, 0-100 scale) which MLS doesn't
    // have. Labeled the same as WC's row per the client's own wording ("attack
    // and defense strength and ranking") — the two never appear on the same
    // page (WC never sets attack_rating/defense_rating, MLS never sets
    // homeAttack/awayAttack), but see hasAttackStrength/hasMlsRating below:
    // they're told apart by which *data* is present, not by this shared label
    // text, so the two captions can't cross-fire.
    {
      label: "Attack Strength", homeVal: homeTeamStats?.attack_rating, awayVal: awayTeamStats?.attack_rating,
      homeText: fmtRating(homeTeamStats?.attack_rating, homeTeamStats?.attack_rank),
      awayText: fmtRating(awayTeamStats?.attack_rating, awayTeamStats?.attack_rank),
    },
    {
      label: "Defense Strength", homeVal: homeTeamStats?.defense_rating, awayVal: awayTeamStats?.defense_rating,
      homeText: fmtRating(homeTeamStats?.defense_rating, homeTeamStats?.defense_rank),
      awayText: fmtRating(awayTeamStats?.defense_rating, awayTeamStats?.defense_rank),
    },
    showXg ? {
      label: "Goals / xG", homeVal: homeGoals, awayVal: awayGoals,
      homeText: `${fmt(homeGoals)} / ${fmt(homeXg)}`, awayText: `${fmt(awayGoals)} / ${fmt(awayXg)}`,
    } : {
      label: "Goals", homeVal: homeGoals, awayVal: awayGoals,
      homeText: fmt(homeGoals), awayText: fmt(awayGoals),
    },
    showXg ? {
      label: "Goals Allowed / xGA", homeVal: homeGoalsAllowed, awayVal: awayGoalsAllowed,
      homeText: `${fmt(homeGoalsAllowed)} / ${fmt(homeXga)}`, awayText: `${fmt(awayGoalsAllowed)} / ${fmt(awayXga)}`,
    } : {
      label: "Goals Allowed", homeVal: homeGoalsAllowed, awayVal: awayGoalsAllowed,
      homeText: fmt(homeGoalsAllowed), awayText: fmt(awayGoalsAllowed),
    },
    {
      label: "Corners per Game", homeVal: homeTeamStats?.corners, awayVal: awayTeamStats?.corners,
      homeText: homeTeamStats?.corners ?? "—", awayText: awayTeamStats?.corners ?? "—",
    },
    {
      label: "Shots on Target per Game", homeVal: homeTeamStats?.shots, awayVal: awayTeamStats?.shots,
      homeText: homeTeamStats?.shots ?? "—", awayText: awayTeamStats?.shots ?? "—",
    },
    {
      label: "Fouls per Game", homeVal: homeTeamStats?.fouls, awayVal: awayTeamStats?.fouls,
      homeText: homeTeamStats?.fouls ?? "—", awayText: awayTeamStats?.fouls ?? "—",
    },
  ].filter(r => r.homeVal != null || r.awayVal != null);

  if (!rows.length) return null;

  // Keyed off the actual data (not the rendered label, which both WC and MLS
  // now share as "Attack/Defense Strength") so the two captions below can't
  // cross-fire onto the wrong league's row.
  const hasAttackStrength = homeAttack != null || awayAttack != null;
  const hasMlsRating = homeTeamStats?.attack_rating != null || awayTeamStats?.attack_rating != null ||
    homeTeamStats?.defense_rating != null || awayTeamStats?.defense_rating != null;

  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 600 }}>IMPORTANT STATS</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
        <span style={{ fontSize: "12px", fontWeight: 700 }}>{homeName}</span>
        <span style={{ fontSize: "12px", fontWeight: 700 }}>{awayName}</span>
      </div>
      {rows.map(({ label, homeVal, awayVal, homeText, awayText }) => {
        // Single contiguous bar split proportionally between the two values
        // (same approach as WinProbBar above), so the side with the bigger
        // number visibly claims more of the bar — two independently
        // max-scaled halves (the old approach) made both sides look
        // nearly full whenever the two values were close, hiding which
        // side was actually bigger.
        const total = (homeVal || 0) + (awayVal || 0);
        const hPct = total > 0 ? ((homeVal || 0) / total) * 100 : 50;
        const aPct = 100 - hPct;
        return (
          <div key={label} style={{ marginBottom: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-green)" }}>{homeText}</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{label}</span>
              <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-purple)" }}>{awayText}</span>
            </div>
            <div style={{ height: "6px", borderRadius: "3px", overflow: "hidden", display: "flex" }}>
              <div style={{ width: `${hPct}%`, backgroundColor: "var(--accent-green)" }} />
              <div style={{ width: `${aPct}%`, backgroundColor: "var(--accent-purple)" }} />
            </div>
          </div>
        );
      })}
      {hasAttackStrength && (
        <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--text-muted)", textAlign: "center" }}>
          Attack Strength on a 0-100 scale
        </div>
      )}
      {hasMlsRating && (
        <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--text-muted)", textAlign: "center" }}>
          Attack/Defense Strength: xG adjusted for the strength of opponents actually played this season (1.00 = average; lower is better for Defense) — rank out of 30
        </div>
      )}
    </div>
  );
}

function LineupSection({ lineups, homeId, awayId, homeName, awayName, homeFormation, awayFormation, confirmed }: {
  lineups: LineupEntry[]; homeId: number; awayId: number;
  homeName: string; awayName: string;
  homeFormation?: string; awayFormation?: string;
  confirmed: boolean;
}) {
  const homeStarters = lineups.filter(l => l.team_id === homeId && !l.is_substitute);
  const awayStarters = lineups.filter(l => l.team_id === awayId && !l.is_substitute);

  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: 600 }}>STARTING LINEUPS</div>
        {!confirmed && (
          <span style={{ fontSize: "11px", color: "var(--accent-gold)", backgroundColor: "rgba(245, 166, 35, 0.1)", padding: "2px 8px", borderRadius: "4px", border: "1px solid rgba(245,166,35,0.3)" }}>
            PREDICTED — Unconfirmed
          </span>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        <LineupColumn name={homeName} players={homeStarters} formation={homeFormation} />
        <LineupColumn name={awayName} players={awayStarters} formation={awayFormation} />
      </div>
    </div>
  );
}

function LineupColumn({ name, players, formation }: { name: string; players: LineupEntry[]; formation?: string }) {
  return (
    <div>
      <div style={{ fontSize: "13px", fontWeight: 700, marginBottom: "8px" }}>
        {name} {formation && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>({formation})</span>}
      </div>
      {players.map((p, i) => (
        <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.04)", fontSize: "13px" }}>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            {p.player_number && <span style={{ color: "var(--text-muted)", minWidth: "20px", fontSize: "11px" }}>{p.player_number}</span>}
            <span>{p.player_name}</span>
          </div>
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            {p.player_pos && <span style={{ fontSize: "10px", color: "var(--accent-purple)", backgroundColor: "rgba(124,92,252,0.15)", padding: "1px 6px", borderRadius: "3px" }}>{p.player_pos}</span>}
            {p.club && <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{p.club}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

function StyleOfPlaySection({ homeStyle, awayStyle, homeName, awayName }: {
  homeStyle?: string; awayStyle?: string; homeName: string; awayName: string;
}) {
  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 600 }}>STYLE OF PLAY</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {[{ name: homeName, style: homeStyle }, { name: awayName, style: awayStyle }].map(({ name, style }) => (
          <div key={name}>
            <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "8px", color: "var(--text-secondary)" }}>{name}</div>
            {style
              ? <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>{style}</p>
              : <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: 0, fontStyle: "italic" }}>Not available</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

function KeyPlayersSection({ homePlayers, awayPlayers, homeName, awayName }: {
  homePlayers: KeyPlayer[]; awayPlayers: KeyPlayer[]; homeName: string; awayName: string;
}) {
  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 600 }}>KEY PLAYERS</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        {[{ name: homeName, players: homePlayers }, { name: awayName, players: awayPlayers }].map(({ name, players }) => (
          <div key={name}>
            <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "8px", color: "var(--text-secondary)" }}>{name}</div>
            {players.map((p, i) => (
              <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "13px", fontWeight: 600 }}>{p.name}</span>
                  <span style={{ fontSize: "10px", color: "var(--accent-purple)", backgroundColor: "rgba(124,92,252,0.15)", padding: "1px 6px", borderRadius: "3px" }}>{p.position}</span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>{p.role}</div>
                {p.club && <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "1px" }}>{p.club}</div>}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchStatsSection({ home, away, homeName, awayName }: {
  home?: MatchStat; away?: MatchStat; homeName: string; awayName: string;
}) {
  const rows: { label: string; homeVal: string | number | null; awayVal: string | number | null; higherIsBetter?: boolean }[] = [
    { label: "Possession", homeVal: home?.possession ?? null, awayVal: away?.possession ?? null },
    { label: "Shots", homeVal: home?.shots_total ?? null, awayVal: away?.shots_total ?? null, higherIsBetter: true },
    { label: "Shots on Target", homeVal: home?.shots_on_target ?? null, awayVal: away?.shots_on_target ?? null, higherIsBetter: true },
    { label: "Corners", homeVal: home?.corners ?? null, awayVal: away?.corners ?? null, higherIsBetter: true },
    { label: "Fouls", homeVal: home?.fouls ?? null, awayVal: away?.fouls ?? null, higherIsBetter: false },
    { label: "Yellow Cards", homeVal: home?.yellow_cards ?? null, awayVal: away?.yellow_cards ?? null, higherIsBetter: false },
    { label: "Offsides", homeVal: home?.offsides ?? null, awayVal: away?.offsides ?? null },
    { label: "Passes", homeVal: home?.passes_total ?? null, awayVal: away?.passes_total ?? null, higherIsBetter: true },
    { label: "Pass Accuracy", homeVal: home?.passes_accuracy ?? null, awayVal: away?.passes_accuracy ?? null, higherIsBetter: true },
  ].filter(r => r.homeVal != null || r.awayVal != null);

  if (!rows.length) return null;

  const parseNum = (v: string | number | null): number => {
    if (v == null) return 0;
    if (typeof v === "number") return v;
    return parseFloat(v.replace("%", "")) || 0;
  };

  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 600 }}>MATCH STATS</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
        <span style={{ fontSize: "12px", fontWeight: 700 }}>{homeName}</span>
        <span style={{ fontSize: "12px", fontWeight: 700 }}>{awayName}</span>
      </div>
      {rows.map(({ label, homeVal, awayVal, higherIsBetter }) => {
        const hNum = parseNum(homeVal);
        const aNum = parseNum(awayVal);
        const total = hNum + aNum;
        const hPct = total > 0 ? (hNum / total) * 100 : 50;
        const aPct = 100 - hPct;
        const homeLeads = hNum > aNum;
        const awayLeads = aNum > hNum;
        const homeColor = higherIsBetter === undefined ? "var(--accent-green)"
          : homeLeads === (higherIsBetter !== false) ? "var(--accent-green)" : "var(--text-secondary)";
        const awayColor = higherIsBetter === undefined ? "var(--accent-purple)"
          : awayLeads === (higherIsBetter !== false) ? "var(--accent-purple)" : "var(--text-secondary)";
        return (
          <div key={label} style={{ marginBottom: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "13px", fontWeight: 700, color: homeColor }}>{homeVal ?? "—"}</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{label}</span>
              <span style={{ fontSize: "13px", fontWeight: 700, color: awayColor }}>{awayVal ?? "—"}</span>
            </div>
            <div style={{ height: "5px", borderRadius: "3px", overflow: "hidden", display: "flex" }}>
              <div style={{ width: `${hPct}%`, backgroundColor: "var(--accent-green)", opacity: 0.7 }} />
              <div style={{ width: `${aPct}%`, backgroundColor: "var(--accent-purple)", opacity: 0.7 }} />
            </div>
          </div>
        );
      })}
      <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--text-muted)", textAlign: "center" }}>
        Source: API-Football · Available from Jun 28, 2026 onward
      </div>
    </div>
  );
}

function RecommendedPlaySection({ play }: {
  play: import("@/lib/api").RecommendedPlay;
}) {
  const confidenceColor = { High: "var(--accent-green)", Medium: "var(--accent-gold)", Low: "#ff4757" }[play.confidence] || "var(--text-muted)";

  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)", backgroundColor: "rgba(124, 92, 252, 0.04)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "10px", fontWeight: 600 }}>🎯 RECOMMENDED PLAY</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
        <div>
          <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>{play.primary_bet}</div>
          <p style={{ fontSize: "13px", color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>{play.reasoning}</p>
          {play.alternative && (
            <div style={{ marginTop: "8px", fontSize: "12px", color: "var(--text-muted)" }}>
              Alt: <span style={{ color: "var(--text-secondary)" }}>{play.alternative}</span>
            </div>
          )}
        </div>
        <div style={{ textAlign: "center", flexShrink: 0 }}>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "2px" }}>CONFIDENCE</div>
          <div style={{ fontSize: "14px", fontWeight: 700, color: confidenceColor }}>{play.confidence}</div>
        </div>
      </div>
    </div>
  );
}
