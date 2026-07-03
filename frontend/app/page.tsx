import { api } from "@/lib/api";
import type { Fixture } from "@/lib/api";
import Link from "next/link";
import BracketView from "@/components/BracketView";
import { LocalDate, LocalTime } from "@/components/LocalTime";

export const revalidate = 60;

export default async function HomePage() {
  const [data, bracketFixtures] = await Promise.all([
    api.home().catch(() => null),
    api.bracket().catch(() => [] as Fixture[]),
  ]);
  if (!data) return <ErrorState />;

  const { next_match, today_matches, recent_results, winner_probabilities, top_players } = data;

  return (
    <div>
      {/* Header */}
      <div className="hero-banner">
        <div className="hero-banner-content">
          <div>
            <div style={{ fontSize: "13px", fontWeight: 800, letterSpacing: "2px", color: "var(--text-primary)", textTransform: "uppercase" }}>
              FIFA World Cup
            </div>
            <div style={{ fontSize: "clamp(32px, 6vw, 56px)", fontWeight: 900, color: "var(--accent-gold)", lineHeight: 1.05, margin: "2px 0" }}>
              2026
            </div>
            <div style={{ fontSize: "12px", fontWeight: 600, letterSpacing: "1.5px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
              USA · Canada · Mexico
            </div>
          </div>
          <div className="hero-trophy-wrap">
            <div className="hero-trophy">🏆</div>
          </div>
        </div>
      </div>

      {/* Today's Schedule */}
      <div className="card" style={{ padding: "0", overflow: "hidden", marginBottom: "24px" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Today&apos;s Schedule</span>
          <Link href="/matches" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>Full Schedule →</Link>
        </div>
        <div style={{ padding: "16px" }}>
          {!today_matches || today_matches.length === 0 ? (
            <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>No matches scheduled today</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4" style={{ gap: "12px" }}>
              {today_matches.map((m: any) => <ScheduleMatchCard key={m.id} fixture={m} />)}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4" style={{ gap: "20px", marginBottom: "24px" }}>
        {/* Next Match */}
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", backgroundColor: "rgba(0,208,132,0.05)" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Next Match</span>
          </div>
          {next_match ? (
            <Link href={`/matches/${next_match.id}`} style={{ textDecoration: "none" }}>
              <div style={{ padding: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
                  <TeamBadge name={next_match.home_name} logo={next_match.home_logo} fifaRank={next_match.home_fifa_rank} />
                  <div style={{ flex: 1, textAlign: "center" }}>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px" }}>{next_match.round}</div>
                    <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--accent-green)" }}><LocalTime ts={next_match.date_utc} /></div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)" }}><LocalDate ts={next_match.date_utc} /></div>
                  </div>
                  <TeamBadge name={next_match.away_name} logo={next_match.away_logo} fifaRank={next_match.away_fifa_rank} />
                </div>
                {next_match.home_win_pct != null && next_match.draw_pct != null && next_match.away_win_pct != null && (() => {
                  const { home_win_pct, draw_pct, away_win_pct } = next_match;
                  const isKO = !next_match.round?.startsWith("Group Stage");
                  const total = isKO ? home_win_pct + away_win_pct : home_win_pct + draw_pct + away_win_pct;
                  const h = Math.round((home_win_pct / total) * 100);
                  const a = isKO ? 100 - h : Math.round((away_win_pct / total) * 100);
                  const d = isKO ? 0 : 100 - h - a;
                  return (
                    <div>
                      <div style={{ height: "8px", borderRadius: "4px", overflow: "hidden", display: "flex", marginBottom: "6px" }}>
                        <div style={{ width: `${h}%`, backgroundColor: "var(--accent-green)" }} />
                        {!isKO && <div style={{ width: `${d}%`, backgroundColor: "var(--border)" }} />}
                        <div style={{ width: `${a}%`, backgroundColor: "var(--accent-purple)" }} />
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
                        <span style={{ color: "var(--accent-green)", fontWeight: 700 }}>{h}%</span>
                        {!isKO && <span style={{ color: "var(--text-muted)" }}>Draw {d}%</span>}
                        <span style={{ color: "var(--accent-purple)", fontWeight: 700 }}>{a}%</span>
                      </div>
                    </div>
                  );
                })()}
                {next_match.venue_city && (
                  <div style={{ marginTop: "10px", fontSize: "12px", color: "var(--text-muted)" }}>📍 {next_match.venue_city}</div>
                )}
              </div>
            </Link>
          ) : (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>No upcoming matches</div>
          )}
        </div>

        {/* AI Match Insight */}
        <AiInsightPanel analysis={next_match?.ai_analysis} matchId={next_match?.id} homeName={next_match?.home_name} awayName={next_match?.away_name} />

        {/* Tournament Winner Predictions */}
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", backgroundColor: "rgba(124,92,252,0.05)" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Tournament Winner Prediction</span>
          </div>
          <div style={{ padding: "16px 20px" }}>
            {winner_probabilities.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "13px", padding: "20px 0", textAlign: "center" }}>
                Run Monte Carlo simulation to see predictions
              </div>
            ) : (
              winner_probabilities.slice(0, 7).map((team, i) => (
                <div key={team.team_id ?? team.team_name ?? i} style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", minWidth: "18px" }}>{i + 1}</span>
                  {team.logo && <img src={team.logo} alt={team.team_name} style={{ width: "20px", height: "20px", objectFit: "contain" }} />}
                  <span style={{ flex: 1, fontSize: "13px", fontWeight: 600 }}>{team.team_name}</span>
                  <div style={{ width: "120px" }}>
                    <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "3px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent-purple)" }}>{team.winner_pct}%</span>
                    </div>
                    <div className="stat-bar">
                      <div className="stat-bar-fill" style={{ width: `${(team.winner_pct / (winner_probabilities[0]?.winner_pct || 1)) * 100}%`, backgroundColor: i === 0 ? "var(--accent-gold)" : "var(--accent-purple)" }} />
                    </div>
                  </div>
                </div>
              ))
            )}
            <div style={{ marginTop: "12px", textAlign: "center" }}>
              <Link href="/predictions" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>View Full Predictions →</Link>
            </div>
          </div>
        </div>
        {/* Top Players */}
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Top Players</span>
          </div>
          <div style={{ padding: "8px 0" }}>
            {top_players.length === 0 ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>Player data loading...</div>
            ) : (
              top_players.map((p, i) => (
                <div key={p.id} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 16px", borderBottom: i < top_players.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)", minWidth: "18px" }}>{i + 1}</span>
                  {p.photo && <img src={p.photo} alt={p.name} style={{ width: "32px", height: "32px", borderRadius: "50%", objectFit: "cover" }} />}
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: "13px", fontWeight: 600 }}>{p.name}</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{p.team_name}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "14px", fontWeight: 800, color: "var(--accent-gold)" }}>{p.goals_intl}</div>
                    <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>goals</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Bracket Preview */}
      {bracketFixtures.length > 0 && (
        <div className="card" style={{ padding: "0", overflow: "hidden", marginBottom: "24px" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              🏆 Knockout Bracket
            </span>
            <Link href="/bracket" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>Full Bracket →</Link>
          </div>
          <div style={{ padding: "16px 20px", overflowX: "auto" }}>
            <BracketView fixtures={bracketFixtures.filter(f => f.round !== "Round of 32")} />
          </div>
        </div>
      )}

      {/* Recent Matches — full-width horizontal grid */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Recent Matches</span>
          <Link href="/matches" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>View All Matches →</Link>
        </div>
        <div style={{ padding: "16px" }}>
          {recent_results.length === 0 ? (
            <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>No completed matches yet</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4" style={{ gap: "12px" }}>
              {recent_results.slice(0, 4).map(f => <RecentMatchCard key={f.id} fixture={f} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TeamBadge({ name, logo, fifaRank }: { name: string; logo?: string; fifaRank?: number }) {
  return (
    <div style={{ flex: 1, textAlign: "center" }}>
      <div style={{ position: "relative", width: "48px", margin: "0 auto 6px" }}>
        {logo ? (
          <img src={logo} alt={name} style={{ width: "48px", height: "48px", objectFit: "contain", display: "block" }} />
        ) : (
          <div style={{ width: "48px", height: "48px", borderRadius: "50%", backgroundColor: "var(--bg-hover)" }} />
        )}
        {fifaRank != null && (
          <span
            title={`FIFA Rank #${fifaRank}`}
            style={{
              position: "absolute", bottom: "-4px", right: "-10px",
              fontSize: "9px", fontWeight: 800, color: "var(--text-primary)",
              backgroundColor: "var(--accent-gold)", padding: "2px 5px", borderRadius: "8px",
              border: "2px solid var(--bg-card)", lineHeight: 1, whiteSpace: "nowrap",
            }}>
            FIFA #{fifaRank}
          </span>
        )}
      </div>
      <div style={{ fontSize: "13px", fontWeight: 700 }}>{name}</div>
    </div>
  );
}

function RecentMatchCard({ fixture }: { fixture: any }) {
  return (
    <Link href={`/matches/${fixture.id}`} style={{ textDecoration: "none" }}>
      <div style={{
        padding: "10px 12px",
        borderRadius: "8px",
        border: "1px solid var(--border)",
        backgroundColor: "rgba(255,255,255,0.02)",
        cursor: "pointer",
      }}>
        {/* Teams + Score */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
          {/* Home */}
          <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: "5px", justifyContent: "flex-end" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{fixture.home_name}</span>
            {fixture.home_logo && <img src={fixture.home_logo} alt="" style={{ width: "18px", height: "18px", objectFit: "contain", flexShrink: 0 }} />}
          </div>
          {/* Score */}
          <div style={{ minWidth: "44px", textAlign: "center", padding: "2px 6px", backgroundColor: "rgba(255,255,255,0.06)", borderRadius: "5px", flexShrink: 0 }}>
            <span style={{ fontSize: "13px", fontWeight: 800, letterSpacing: "-0.5px" }}>
              {fixture.home_score ?? 0}–{fixture.away_score ?? 0}
            </span>
          </div>
          {/* Away */}
          <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: "5px" }}>
            {fixture.away_logo && <img src={fixture.away_logo} alt="" style={{ width: "18px", height: "18px", objectFit: "contain", flexShrink: 0 }} />}
            <span style={{ fontSize: "12px", fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{fixture.away_name}</span>
          </div>
        </div>
        {/* Date + Round */}
        <div style={{ fontSize: "10px", color: "var(--text-muted)", textAlign: "center" }}>
          <LocalDate ts={fixture.date_utc} />
          {fixture.round && <span style={{ marginLeft: "5px", opacity: 0.7 }}>· {fixture.round.replace("Group Stage - ", "")}</span>}
        </div>
      </div>
    </Link>
  );
}

function ScheduleMatchCard({ fixture }: { fixture: any }) {
  const isLive = ["1H", "2H", "HT", "ET", "P"].includes(fixture.status);
  const isDone = ["FT", "AET", "PEN"].includes(fixture.status);

  return (
    <Link href={`/matches/${fixture.id}`} style={{ textDecoration: "none" }}>
      <div style={{
        padding: "10px 12px",
        borderRadius: "8px",
        border: `1px solid ${isLive ? "rgba(0,208,132,0.35)" : "var(--border)"}`,
        backgroundColor: isLive ? "rgba(0,208,132,0.05)" : "rgba(255,255,255,0.02)",
        cursor: "pointer",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
          <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: "5px", justifyContent: "flex-end" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{fixture.home_name}</span>
            {fixture.home_logo && <img src={fixture.home_logo} alt="" style={{ width: "18px", height: "18px", objectFit: "contain", flexShrink: 0 }} />}
          </div>
          <div style={{ minWidth: "48px", textAlign: "center", padding: "2px 6px", backgroundColor: isLive ? "rgba(0,208,132,0.15)" : "rgba(255,255,255,0.06)", borderRadius: "5px", flexShrink: 0 }}>
            {isDone || isLive ? (
              <span style={{ fontSize: "13px", fontWeight: 800, letterSpacing: "-0.5px", color: isLive ? "var(--accent-green)" : "var(--text-primary)" }}>
                {fixture.home_score ?? 0}–{fixture.away_score ?? 0}
              </span>
            ) : (
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)" }}><LocalTime ts={fixture.date_utc} /></span>
            )}
          </div>
          <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", gap: "5px" }}>
            {fixture.away_logo && <img src={fixture.away_logo} alt="" style={{ width: "18px", height: "18px", objectFit: "contain", flexShrink: 0 }} />}
            <span style={{ fontSize: "12px", fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{fixture.away_name}</span>
          </div>
        </div>
        <div style={{ fontSize: "10px", color: isLive ? "var(--accent-green)" : "var(--text-muted)", textAlign: "center", fontWeight: isLive ? 700 : 400 }}>
          {isLive ? "● LIVE" : isDone ? "Full Time" : fixture.round?.replace("Group Stage - ", "")}
        </div>
      </div>
    </Link>
  );
}

function AiInsightPanel({ analysis, matchId, homeName, awayName }: {
  analysis?: string;
  matchId?: number;
  homeName?: string;
  awayName?: string;
}) {
  const MAX = 320;
  let preview = "";
  let truncated = false;
  if (analysis) {
    if (analysis.length > MAX) {
      const cut = analysis.lastIndexOf(". ", MAX);
      preview = cut > 80 ? analysis.slice(0, cut + 1) : analysis.slice(0, MAX);
      truncated = true;
    } else {
      preview = analysis;
    }
  }

  return (
    <div className="card" style={{ padding: "0", overflow: "hidden" }}>
      <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", backgroundColor: "rgba(0,208,132,0.04)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          ⚡ AI Match Insight
        </span>
        {matchId && (
          <Link href={`/matches/${matchId}`} style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>
            Full Analysis →
          </Link>
        )}
      </div>
      <div style={{ padding: "16px 20px" }}>
        {homeName && awayName && (
          <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent-green)", marginBottom: "10px", textTransform: "uppercase", letterSpacing: "0.4px" }}>
            {homeName} vs {awayName}
          </div>
        )}
        {preview ? (
          <>
            <p style={{ fontSize: "13px", lineHeight: 1.6, color: "var(--text-secondary)", margin: 0 }}>
              {preview}{truncated && <span style={{ color: "var(--text-muted)" }}>…</span>}
            </p>
            {truncated && matchId && (
              <Link href={`/matches/${matchId}`} style={{ display: "inline-block", marginTop: "12px", fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>
                Read more →
              </Link>
            )}
          </>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: "13px", padding: "20px 0", textAlign: "center" }}>
            <div style={{ fontSize: "28px", marginBottom: "8px" }}>⚡</div>
            Analysis generating — visit the{" "}
            {matchId ? (
              <Link href={`/matches/${matchId}`} style={{ color: "var(--accent-purple)", textDecoration: "none" }}>match page</Link>
            ) : "match page"}
            {" "}to trigger it
          </div>
        )}
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="card" style={{ padding: "60px", textAlign: "center" }}>
      <div style={{ fontSize: "48px", marginBottom: "16px" }}>⚙️</div>
      <h2 style={{ fontSize: "20px", fontWeight: 700, marginBottom: "8px" }}>Backend not connected</h2>
      <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
        Start the FastAPI backend at <code style={{ color: "var(--accent-green)" }}>http://localhost:8000</code>
      </p>
      <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "8px" }}>
        Run: <code style={{ color: "var(--accent-purple)" }}>cd backend && uvicorn app.main:app --reload</code>
      </p>
    </div>
  );
}
