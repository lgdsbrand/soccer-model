import { mlsApi, MLS_CURRENT_SEASON } from "@/lib/mlsApi";
import type { MlsStanding, MlsTopPlay, MlsTopPlays } from "@/lib/mlsApi";
import type { Fixture } from "@/lib/api";
import Link from "next/link";
import FixtureRow from "@/components/FixtureRow";
import StandingsTable from "@/components/mls/StandingsTable";

export const revalidate = 60;

function toEasternDateStr(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

export default async function MlsHomePage() {
  const [allFixtures, conferences, topPlays] = await Promise.all([
    mlsApi.fixtures(`season=${MLS_CURRENT_SEASON}&limit=300`).catch(() => [] as Fixture[]),
    mlsApi.standings().catch(() => ({} as Record<string, MlsStanding[]>)),
    mlsApi.topPlays().catch(() => null as MlsTopPlays | null),
  ]);

  const todayStr = toEasternDateStr(Date.now() / 1000);
  const todayMatches = allFixtures.filter(f => toEasternDateStr(f.date_utc) === todayStr);
  const recentResults = allFixtures
    .filter(f => f.status === "FT")
    .sort((a, b) => b.date_utc - a.date_utc)
    .slice(0, 4);
  const upcoming = allFixtures
    .filter(f => f.status === "NS")
    .sort((a, b) => a.date_utc - b.date_utc)
    .slice(0, 5);

  const sortedConferences = Object.keys(conferences).sort((a, b) => (a === "Eastern" ? -1 : b === "Eastern" ? 1 : 0));

  const topPlayCards: { key: string; label: string; play: MlsTopPlay | null }[] = [
    { key: "btts", label: "Best BTTS Play", play: topPlays?.btts ?? null },
    { key: "over_1_5", label: "Best Over 1.5 Play", play: topPlays?.over_1_5 ?? null },
    { key: "over_2_5", label: "Best Over 2.5 Play", play: topPlays?.over_2_5 ?? null },
  ];
  const hasTopPlays = topPlayCards.some(c => c.play !== null);

  return (
    <div>
      {/* Header */}
      <div className="hero-banner">
        <div className="hero-banner-content">
          <div>
            <div style={{ fontSize: "13px", fontWeight: 800, letterSpacing: "2px", color: "var(--text-primary)", textTransform: "uppercase" }}>
              Major League Soccer
            </div>
            <div style={{ fontSize: "clamp(32px, 6vw, 56px)", fontWeight: 900, color: "var(--accent-gold)", lineHeight: 1.05, margin: "2px 0" }}>
              2026
            </div>
            <div style={{ fontSize: "12px", fontWeight: 600, letterSpacing: "1.5px", color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Eastern &amp; Western Conference
            </div>
          </div>
          <div className="hero-trophy-wrap">
            <div className="hero-trophy">⚽</div>
          </div>
        </div>
      </div>

      {/* Top Plays */}
      {hasTopPlays && (
        <div style={{ marginBottom: "24px" }}>
          <div style={{ marginBottom: "12px", fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Top Plays Today
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3" style={{ gap: "20px" }}>
            {topPlayCards.map(({ key, label, play }) => (
              <div key={key} className="card" style={{ padding: "16px" }}>
                <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
                  {label}
                </div>
                {play ? (
                  <Link href={`/mls/matches/${play.fixture_id}`} style={{ textDecoration: "none", color: "inherit", display: "block" }}>
                    <div style={{ fontSize: "28px", fontWeight: 900, color: "var(--accent-green)", marginBottom: "8px" }}>
                      {play.value.toFixed(1)}%
                    </div>
                    <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                      {play.home_name} vs {play.away_name}
                    </div>
                  </Link>
                ) : (
                  <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>No data yet</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Today's Schedule */}
      {todayMatches.length > 0 && (
        <div className="card" style={{ padding: "0", overflow: "hidden", marginBottom: "24px" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Today&apos;s Schedule</span>
            <Link href="/mls/matches" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>Full Schedule →</Link>
          </div>
          <div style={{ padding: "16px" }}>
            {todayMatches.map(f => <FixtureRow key={f.id} fixture={f} basePath="/mls/matches" />)}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2" style={{ gap: "20px", marginBottom: "24px" }}>
        {/* Upcoming Matches */}
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", backgroundColor: "rgba(0,208,132,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Upcoming Matches</span>
            <Link href="/mls/matches" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>Full Schedule →</Link>
          </div>
          <div style={{ padding: "16px" }}>
            {upcoming.length === 0 ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>No upcoming matches</div>
            ) : (
              upcoming.map(f => <FixtureRow key={f.id} fixture={f} basePath="/mls/matches" />)
            )}
          </div>
        </div>

        {/* Recent Results */}
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Recent Results</span>
            <Link href="/mls/matches" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>View All →</Link>
          </div>
          <div style={{ padding: "16px" }}>
            {recentResults.length === 0 ? (
              <div style={{ padding: "20px", textAlign: "center", color: "var(--text-muted)", fontSize: "14px" }}>No completed matches yet</div>
            ) : (
              recentResults.map(f => <FixtureRow key={f.id} fixture={f} basePath="/mls/matches" />)
            )}
          </div>
        </div>
      </div>

      {/* Standings Preview */}
      <div style={{ marginBottom: "12px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>Standings</span>
        <Link href="/mls/standings" style={{ fontSize: "12px", color: "var(--accent-purple)", textDecoration: "none", fontWeight: 600 }}>Full Standings →</Link>
      </div>
      {sortedConferences.length === 0 ? (
        <div className="card" style={{ padding: "60px", textAlign: "center" }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>📊</div>
          <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Standings loading — check backend connection</div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "20px" }}>
          {sortedConferences.map(conference => (
            <StandingsTable key={conference} conference={conference} standings={conferences[conference].slice(0, 5)} />
          ))}
        </div>
      )}
    </div>
  );
}
