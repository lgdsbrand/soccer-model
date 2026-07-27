import { mlsApi, MLS_CURRENT_SEASON } from "@/lib/mlsApi";
import type { Fixture } from "@/lib/api";
import FixtureRow from "@/components/FixtureRow";
import MatchDayNav from "@/components/mls/MatchDayNav";

export const revalidate = 60;

const MAX_MATCH_DAYS = 5;

function formatDayHeader(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", timeZone: "UTC",
  });
}

// MLS clubs are all North-America-based (unlike the WC's multi-host-country
// spread this helper was originally written for) — Eastern Time day
// boundaries are still the right call, so the same convention applies.
function toEasternDateStr(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

export default async function MlsMatchesPage() {
  let fixtures: Fixture[] = [];
  try {
    fixtures = await mlsApi.fixtures(`status=NS&season=${MLS_CURRENT_SEASON}&limit=300`);
  } catch {
    fixtures = [];
  }

  const byDate: Record<string, Fixture[]> = {};
  for (const f of fixtures) {
    const date = toEasternDateStr(f.date_utc);
    if (!byDate[date]) byDate[date] = [];
    byDate[date].push(f);
  }
  // Next 3-5 upcoming match days only — MLS's regular season runs for
  // months, so (unlike the World Cup's short tournament) showing every
  // fixture date at once would bury the schedule in irrelevant future noise.
  const dates = Object.keys(byDate).sort().slice(0, MAX_MATCH_DAYS);
  const todayStr = toEasternDateStr(Date.now() / 1000);

  return (
    <div>
      <div style={{ marginBottom: "16px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>MLS Schedule</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
          Next {dates.length} match {dates.length === 1 ? "day" : "days"}
        </p>
      </div>

      <MatchDayNav dates={dates} activeDate={dates[0]} todayStr={todayStr} />

      {dates.length === 0 ? (
        <div className="card" style={{ padding: "60px", textAlign: "center" }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>⚽</div>
          <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Fixtures loading — check backend connection</div>
        </div>
      ) : (
        dates.map(dateStr => {
          const isToday = dateStr === todayStr;
          const dayFixtures = byDate[dateStr];
          return (
            <div key={dateStr} id={`date-${dateStr}`} style={{ marginBottom: "32px", scrollMarginTop: "16px" }}>
              <div style={{
                display: "flex", alignItems: "center", gap: "10px",
                marginBottom: "10px", paddingBottom: "10px",
                borderBottom: `1px solid ${isToday ? "rgba(0,208,132,0.25)" : "var(--border)"}`,
              }}>
                <span style={{
                  fontSize: "15px", fontWeight: 800,
                  color: isToday ? "var(--accent-green)" : "var(--text-primary)",
                }}>
                  {formatDayHeader(dateStr)}
                </span>
                {isToday && (
                  <span style={{
                    fontSize: "10px", fontWeight: 700,
                    backgroundColor: "rgba(0,208,132,0.15)",
                    color: "var(--accent-green)",
                    padding: "2px 8px", borderRadius: "4px",
                    textTransform: "uppercase", letterSpacing: "0.5px",
                  }}>Today</span>
                )}
                <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--text-muted)" }}>
                  {dayFixtures.length} {dayFixtures.length === 1 ? "match" : "matches"}
                </span>
              </div>
              {dayFixtures.map(f => <FixtureRow key={f.id} fixture={f} basePath="/mls/matches" />)}
            </div>
          );
        })
      )}
    </div>
  );
}
