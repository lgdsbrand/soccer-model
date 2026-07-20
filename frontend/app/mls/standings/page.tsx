import { mlsApi } from "@/lib/mlsApi";
import StandingsTable from "@/components/mls/StandingsTable";

export const revalidate = 300;

export default async function MlsStandingsPage() {
  let conferences: Record<string, any[]> = {};
  try {
    conferences = await mlsApi.standings();
  } catch {
    conferences = {};
  }

  // Eastern before Western, consistent regardless of API key order
  const sortedConferences = Object.keys(conferences).sort((a, b) => (a === "Eastern" ? -1 : b === "Eastern" ? 1 : 0));

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>MLS Standings</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
          Eastern &amp; Western Conference
        </p>
      </div>

      {sortedConferences.length === 0 ? (
        <div className="card" style={{ padding: "60px", textAlign: "center" }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>📊</div>
          <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Standings loading — check backend connection</div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "20px" }}>
          {sortedConferences.map(conference => (
            <StandingsTable key={conference} conference={conference} standings={conferences[conference]} />
          ))}
        </div>
      )}
    </div>
  );
}
