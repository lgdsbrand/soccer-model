import { api } from "@/lib/api";
import type { Fixture } from "@/lib/api";
import FixtureRow from "@/components/FixtureRow";
import DateNav from "@/components/DateNav";

export const revalidate = 60;

function formatDayHeader(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", timeZone: "UTC",
  });
}

export default async function MatchesPage() {
  let fixtures: Fixture[] = [];
  try {
    fixtures = await api.fixtures("limit=200");
  } catch {
    fixtures = [];
  }

  const byDate: Record<string, Fixture[]> = {};
  for (const f of fixtures) {
    const date = new Date(f.date_utc * 1000).toISOString().slice(0, 10);
    if (!byDate[date]) byDate[date] = [];
    byDate[date].push(f);
  }
  const dates = Object.keys(byDate).sort();
  const todayStr = new Date().toISOString().slice(0, 10);

  return (
    <div>
      <div style={{ marginBottom: "16px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>Schedule</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
          {fixtures.length} matches · {dates.length} matchdays
        </p>
      </div>

      <DateNav todayStr={todayStr} dates={dates} />

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
              {dayFixtures.map(f => <FixtureRow key={f.id} fixture={f} />)}
            </div>
          );
        })
      )}
    </div>
  );
}
