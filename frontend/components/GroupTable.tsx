import type { Standing } from "@/lib/api";

export default function GroupTable({ group, standings }: { group: string; standings: Standing[] }) {
  return (
    <div className="card" style={{ overflow: "hidden" }}>
      <div style={{
        padding: "12px 16px",
        borderBottom: "1px solid var(--border)",
        backgroundColor: "rgba(124, 92, 252, 0.06)",
        display: "flex", alignItems: "center", gap: "8px",
      }}>
        <div style={{
          width: "28px", height: "28px", borderRadius: "6px",
          backgroundColor: "var(--accent-purple)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "13px", fontWeight: 700,
        }}>
          {group}
        </div>
        <span style={{ fontWeight: 700, fontSize: "14px" }}>Group {group}</span>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            {["#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"].map(h => (
              <th key={h} style={{ padding: "8px 10px", fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textAlign: h === "Team" ? "left" : "center", letterSpacing: "0.3px" }}>
                {h}
              </th>
            ))}
            <th style={{ padding: "8px 10px", fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textAlign: "center" }}>Form</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((s, i) => (
            <tr key={s.team_id} style={{
              borderBottom: i < standings.length - 1 ? "1px solid rgba(255,255,255,0.03)" : "none",
              backgroundColor: i < 2 ? "rgba(0, 208, 132, 0.03)" : "transparent",
            }}>
              <td style={{ padding: "10px", textAlign: "center", fontSize: "12px", color: i < 2 ? "var(--accent-green)" : "var(--text-muted)", fontWeight: 700 }}>
                {s.rank}
              </td>
              <td style={{ padding: "10px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {s.team_logo && <img src={s.team_logo} alt={s.team_name} style={{ width: "20px", height: "20px", objectFit: "contain" }} />}
                  <span style={{ fontSize: "13px", fontWeight: 600 }}>{s.team_name}</span>
                </div>
              </td>
              {[s.played, s.won, s.drawn, s.lost, s.goals_for, s.goals_against, s.goal_diff > 0 ? `+${s.goal_diff}` : s.goal_diff].map((v, j) => (
                <td key={j} style={{ padding: "10px", textAlign: "center", fontSize: "13px", color: j === 6 && s.goal_diff > 0 ? "var(--accent-green)" : s.goal_diff < 0 && j === 6 ? "var(--accent-red, #ff4757)" : "var(--text-secondary)" }}>
                  {v}
                </td>
              ))}
              <td style={{ padding: "10px", textAlign: "center", fontSize: "14px", fontWeight: 800, color: i < 2 ? "var(--accent-green)" : "var(--text-secondary)" }}>
                {s.points}
              </td>
              <td style={{ padding: "10px", textAlign: "center" }}>
                <div style={{ display: "flex", gap: "3px", justifyContent: "center" }}>
                  {(s.form || "").split("").slice(-5).map((r, fi) => {
                    const c = r === "W" ? "#00d084" : r === "D" ? "#f5a623" : "#ff4757";
                    return (
                      <div key={fi} style={{ width: "14px", height: "14px", borderRadius: "3px", backgroundColor: c + "33", border: `1px solid ${c}66`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "9px", fontWeight: 700, color: c }}>
                        {r}
                      </div>
                    );
                  })}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ padding: "8px 16px", backgroundColor: "rgba(0,208,132,0.04)", borderTop: "1px solid var(--border)" }}>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
          <span style={{ color: "var(--accent-green)" }}>●</span> Top 2 qualify automatically · 3rd place may qualify as best 3rd
        </span>
      </div>
    </div>
  );
}
