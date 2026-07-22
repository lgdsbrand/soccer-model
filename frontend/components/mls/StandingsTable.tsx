import type { MlsStanding } from "@/lib/mlsApi";

export default function StandingsTable({ conference, standings }: { conference: string; standings: MlsStanding[] }) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border)",
        backgroundColor: "rgba(124, 92, 252, 0.06)",
      }}>
        <span style={{ fontWeight: 700, fontSize: "14px" }}>{conference} Conference</span>
      </div>

      <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {["#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"].map(h => (
              <th key={h} style={{ padding: h === "Team" ? "8px 10px" : "8px 5px", fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textAlign: h === "Team" ? "left" : "center", letterSpacing: "0.3px" }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {standings.map((s, i) => (
            <tr key={s.team_id} style={{
              borderBottom: i < standings.length - 1 ? "1px solid rgba(255,255,255,0.03)" : "none",
            }}>
              <td style={{ padding: "10px 5px", textAlign: "center", fontSize: "12px", color: "var(--text-muted)", fontWeight: 700 }}>
                {s.rank}
              </td>
              <td style={{ padding: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {s.team_logo && <img src={s.team_logo} alt={s.team_name} style={{ width: "20px", height: "20px", objectFit: "contain" }} />}
                  <span style={{ fontSize: "13px", fontWeight: 600 }}>{s.team_name}</span>
                </div>
              </td>
              {[s.played, s.won, s.drawn, s.lost, s.goals_for, s.goals_against, s.goal_diff > 0 ? `+${s.goal_diff}` : s.goal_diff].map((v, j) => (
                <td key={j} style={{ padding: "10px 5px", textAlign: "center", fontSize: "13px", color: j === 6 && s.goal_diff > 0 ? "var(--accent-green)" : s.goal_diff < 0 && j === 6 ? "var(--accent-red, #ff4757)" : "var(--text-secondary)" }}>
                  {v}
                </td>
              ))}
              <td style={{ padding: "10px 5px", textAlign: "center", fontSize: "14px", fontWeight: 800, color: "var(--text-secondary)" }}>
                {s.points}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}
