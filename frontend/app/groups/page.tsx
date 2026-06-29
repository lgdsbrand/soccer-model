import { api } from "@/lib/api";
import GroupTable from "@/components/GroupTable";

export const revalidate = 300;

export default async function GroupsPage() {
  let groups: Record<string, any[]> = {};
  try {
    groups = await api.standings();
  } catch {
    groups = {};
  }

  const sortedGroups = Object.keys(groups).sort();

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>Group Stage</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
          {sortedGroups.length} groups · Top 2 qualify + 8 best 3rd-place teams
        </p>
      </div>

      {sortedGroups.length === 0 ? (
        <div className="card" style={{ padding: "60px", textAlign: "center" }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>📊</div>
          <div style={{ color: "var(--text-muted)", fontSize: "14px" }}>Group data loading — check backend connection</div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "20px" }}>
          {sortedGroups.map(group => (
            <GroupTable key={group} group={group} standings={groups[group]} />
          ))}
        </div>
      )}
    </div>
  );
}
