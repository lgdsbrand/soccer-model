import { api } from "@/lib/api";
import Link from "next/link";

export const revalidate = 3600;

export default async function TeamsPage() {
  let teams: any[] = [];
  try {
    teams = await api.teams();
  } catch {
    teams = [];
  }

  const byGroup: Record<string, typeof teams> = {};
  for (const t of teams) {
    const g = t.group_letter || "?";
    if (!byGroup[g]) byGroup[g] = [];
    byGroup[g].push(t);
  }

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>Teams</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>{teams.length} teams</p>
      </div>

      {Object.keys(byGroup).sort().map(group => (
        <div key={group} style={{ marginBottom: "24px" }}>
          <div style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
            Group {group}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
            {byGroup[group].map(team => (
              <Link key={team.id} href={`/teams/${team.id}`} style={{ textDecoration: "none" }}>
                <div className="card team-card" style={{ padding: "16px", textAlign: "center", cursor: "pointer" }}>
                  {team.logo ? (
                    <img src={team.logo} alt={team.name} style={{ width: "48px", height: "48px", objectFit: "contain", margin: "0 auto 10px", display: "block" }} />
                  ) : (
                    <div style={{ width: "48px", height: "48px", borderRadius: "50%", backgroundColor: "var(--bg-hover)", margin: "0 auto 10px" }} />
                  )}
                  <div style={{ fontSize: "13px", fontWeight: 700 }}>{team.name}</div>
                  {team.points != null && (
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
                      {team.points} pts · {team.played ?? 0} played
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
