"use client";
import Link from "next/link";
import type { Fixture, FixtureDetail, Prediction, TeamStats, KeyPlayer, LineupEntry, MatchStat } from "@/lib/api";
import { formatDate, formatTime, getStatusLabel } from "@/lib/api";

interface Props {
  fixture: FixtureDetail;
  compact?: boolean;
}

export default function MatchCard({ fixture, compact }: Props) {
  const status = getStatusLabel(fixture.status);
  const pred = fixture.prediction;
  const isLive = ["1H", "2H", "HT", "ET", "P"].includes(fixture.status);
  const isFinished = ["FT", "AET", "PEN"].includes(fixture.status);
  const isKnockout = !fixture.round?.startsWith("Group Stage");

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

      {/* Teams + Score */}
      <div style={{ padding: "20px", display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Home */}
        <div style={{ flex: 1, textAlign: "center" }}>
          {fixture.home_logo && (
            <div style={{ position: "relative", width: "52px", margin: "0 auto 8px" }}>
              <img src={fixture.home_logo} alt={fixture.home_name}
                style={{ width: "52px", height: "52px", objectFit: "contain" }} />
              {fixture.home_fifa_rank != null && <FifaRankBadge rank={fixture.home_fifa_rank} />}
            </div>
          )}
          <div style={{ fontWeight: 700, fontSize: "16px" }}>{fixture.home_name}</div>
          {fixture.home_group && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>Group {fixture.home_group}</div>
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
              <div style={{ fontSize: "13px", color: "var(--accent-green)", marginTop: "4px" }}>{formatTime(fixture.date_utc)}</div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{formatDate(fixture.date_utc)}</div>
            </>
          )}
        </div>

        {/* Away */}
        <div style={{ flex: 1, textAlign: "center" }}>
          {fixture.away_logo && (
            <div style={{ position: "relative", width: "52px", margin: "0 auto 8px" }}>
              <img src={fixture.away_logo} alt={fixture.away_name}
                style={{ width: "52px", height: "52px", objectFit: "contain" }} />
              {fixture.away_fifa_rank != null && <FifaRankBadge rank={fixture.away_fifa_rank} />}
            </div>
          )}
          <div style={{ fontWeight: 700, fontSize: "16px" }}>{fixture.away_name}</div>
          {fixture.away_group && (
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>Group {fixture.away_group}</div>
          )}
        </div>
      </div>

      {/* Location + Weather */}
      {(fixture.venue_name || fixture.venue_city || fixture.weather) && (
        <div style={{ padding: "0 20px 12px", display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          {(fixture.venue_name || fixture.venue_city) && (
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              📍 {fixture.venue_name || fixture.venue_city}
            </span>
          )}
          {fixture.weather && (
            <>
              {(fixture.venue_name || fixture.venue_city) && <span style={{ color: "var(--border)" }}>·</span>}
              <img
                src={`https://openweathermap.org/img/wn/${fixture.weather.icon}.png`}
                alt={fixture.weather.description}
                style={{ width: "18px", height: "18px", verticalAlign: "middle" }}
              />
              <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                {fixture.weather.temperature_c.toFixed(1)}°C, {fixture.weather.description}
              </span>
              <span style={{ color: "var(--border)" }}>·</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontStyle: "italic" }}>Now</span>
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
          <Link href={`/matches/${fixture.id}`} style={{
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
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "8px", marginTop: "16px" }}>
                <StatChip label="BTTS" value={`${pred.btts_pct}%`} color="var(--accent-purple)" />
                <StatChip label="O1.5 Goals" value={`${pred.over_1_5_pct}%`} color="var(--accent-blue, #3d9df3)" />
                <StatChip label="O2.5 Goals" value={`${pred.over_2_5_pct}%`} color="var(--accent-gold)" />
                <StatChip label="xG Home" value={pred.expected_home_goals.toFixed(2)} color="var(--accent-green)" />
              </div>
            </div>
          )}

          {/* Last 5 Form */}
          {(fixture.home_last5?.length > 0 || fixture.away_last5?.length > 0) && (
            <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <FormRow label={`${fixture.home_name} Last 5`} results={fixture.home_last5 ?? []} teamId={fixture.home_team_id} />
                <FormRow label={`${fixture.away_name} Last 5`} results={fixture.away_last5 ?? []} teamId={fixture.away_team_id} />
              </div>
            </div>
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
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Detailed match stats available from <strong style={{ color: "var(--text-secondary)" }}>June 28, 2026</strong> onward
              </span>
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

          {/* Recommended Play */}
          {fixture.recommended_play
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
          }
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

function FormRow({ label, results, teamId }: { label: string; results: any[]; teamId: number }) {
  const colors = { W: "#00d084", D: "#f5a623", L: "#ff4757" };
  return (
    <div>
      <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px" }}>{label}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {results.slice(0, 5).map((r, i) => {
          const isHome = r.home_team_id === teamId;
          const gs = isHome ? r.home_score : r.away_score;
          const gc = isHome ? r.away_score : r.home_score;
          const outcome = gs > gc ? "W" : gs === gc ? "D" : "L";
          const color = colors[outcome as keyof typeof colors];
          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "6px 8px", borderRadius: "6px",
              backgroundColor: "rgba(255,255,255,0.03)",
              border: `1px solid ${color}22`,
            }}>
              {/* W/D/L badge */}
              <span style={{
                width: "16px", height: "16px", borderRadius: "3px", flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "9px", fontWeight: 800,
                backgroundColor: color + "22", color, border: `1px solid ${color}55`,
              }}>{outcome}</span>

              {/* Home team */}
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "4px", minWidth: 0, justifyContent: "flex-end" }}>
                <span style={{ fontSize: "11px", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.home_name ?? "?"}</span>
                {r.home_logo && <img src={r.home_logo} alt="" style={{ width: 16, height: 16, objectFit: "contain", flexShrink: 0 }} />}
              </div>

              {/* Score */}
              <span style={{ fontSize: "13px", fontWeight: 800, color: "var(--text-primary)", flexShrink: 0, minWidth: "36px", textAlign: "center", fontVariantNumeric: "tabular-nums" }}>
                {r.home_score ?? "?"}-{r.away_score ?? "?"}
              </span>

              {/* Away team */}
              <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "4px", minWidth: 0 }}>
                {r.away_logo && <img src={r.away_logo} alt="" style={{ width: 16, height: 16, objectFit: "contain", flexShrink: 0 }} />}
                <span style={{ fontSize: "11px", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.away_name ?? "?"}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatComparison({ home, away, homeName, awayName }: { home?: TeamStats; away?: TeamStats; homeName: string; awayName: string }) {
  if (!home && !away) return null;

  const stats = [
    { label: "Avg Shots", homeVal: home?.shots_total, awayVal: away?.shots_total },
    { label: "Shots on Target", homeVal: home?.shots_on_target, awayVal: away?.shots_on_target },
    { label: "Avg Corners", homeVal: home?.corners, awayVal: away?.corners },
    { label: "Avg Fouls", homeVal: home?.fouls, awayVal: away?.fouls },
  ].filter(s => s.homeVal != null || s.awayVal != null);

  if (!stats.length) return null;

  return (
    <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px", fontWeight: 600 }}>AVG LAST 5 GAMES</div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
        <span style={{ fontSize: "12px", fontWeight: 600 }}>{homeName}</span>
        <span style={{ fontSize: "12px", fontWeight: 600 }}>{awayName}</span>
      </div>
      {stats.map(({ label, homeVal, awayVal }) => {
        const max = Math.max(homeVal || 0, awayVal || 0, 1);
        return (
          <div key={label} style={{ marginBottom: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent-green)" }}>{homeVal ?? "—"}</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{label}</span>
              <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent-purple)" }}>{awayVal ?? "—"}</span>
            </div>
            <div style={{ height: "6px", borderRadius: "3px", overflow: "hidden", display: "flex", gap: "4px" }}>
              <div style={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
                <div style={{ width: `${((homeVal || 0) / max) * 100}%`, backgroundColor: "var(--accent-green)", borderRadius: "3px" }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ width: `${((awayVal || 0) / max) * 100}%`, backgroundColor: "var(--accent-purple)", borderRadius: "3px" }} />
              </div>
            </div>
          </div>
        );
      })}
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
        const max = Math.max(hNum, aNum, 1);
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
            <div style={{ height: "5px", borderRadius: "3px", overflow: "hidden", display: "flex", gap: "3px" }}>
              <div style={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
                <div style={{ width: `${(hNum / max) * 100}%`, backgroundColor: "var(--accent-green)", borderRadius: "3px", opacity: 0.7 }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ width: `${(aNum / max) * 100}%`, backgroundColor: "var(--accent-purple)", borderRadius: "3px", opacity: 0.7 }} />
              </div>
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
