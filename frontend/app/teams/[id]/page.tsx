import { api } from "@/lib/api";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 3600;

export default async function TeamDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let team;
  try {
    team = await api.team(parseInt(id));
  } catch {
    notFound();
  }

  const adv = team.advancement;

  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <Link href="/teams" style={{ fontSize: "13px", color: "var(--text-muted)", textDecoration: "none" }}>← Back to Teams</Link>
      </div>

      {/* Team Header */}
      <div className="card" style={{ padding: "24px", marginBottom: "20px", display: "flex", gap: "20px", alignItems: "flex-start" }}>
        {team.logo && <img src={team.logo} alt={team.name} style={{ width: "72px", height: "72px", objectFit: "contain" }} />}
        <div style={{ flex: 1 }}>
          <h1 style={{ fontSize: "24px", fontWeight: 800, margin: "0 0 4px" }}>{team.name}</h1>
          {team.group_letter && <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>Group {team.group_letter}</div>}
          {team.coach && <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>Coach: <strong>{team.coach}</strong></div>}
          {team.formation_default && <div style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "2px" }}>Formation: <strong>{team.formation_default}</strong></div>}
        </div>
        {team.standing && (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "32px", fontWeight: 800, color: "var(--accent-green)" }}>{team.standing.points}</div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Points</div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>
              {team.standing.won}W {team.standing.drawn}D {team.standing.lost}L
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "20px" }}>
        {/* Style of Play */}
        {team.style_of_play && (
          <div className="card" style={{ padding: "20px" }}>
            <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "10px", textTransform: "uppercase" }}>Style of Play</div>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>{team.style_of_play}</p>
          </div>
        )}

        {/* Advancement */}
        {adv && (
          <div className="card" style={{ padding: "20px" }}>
            <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "12px", textTransform: "uppercase" }}>Advancement Probability</div>
            {[
              { label: "Round of 32", value: adv.r32_pct, color: "var(--accent-blue, #3d9df3)" },
              { label: "Round of 16", value: adv.r16_pct, color: "var(--accent-purple)" },
              { label: "Quarter-Final", value: adv.qf_pct, color: "var(--accent-gold)" },
              { label: "Semi-Final", value: adv.sf_pct, color: "#ff6b35" },
              { label: "Final", value: adv.final_pct, color: "#ff4757" },
              { label: "Champion 🏆", value: adv.winner_pct, color: "var(--accent-green)" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ marginBottom: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{label}</span>
                  <span style={{ fontSize: "12px", fontWeight: 700, color }}>{value}%</span>
                </div>
                <div className="stat-bar">
                  <div className="stat-bar-fill" style={{ width: `${value}%`, backgroundColor: color }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Key Players */}
      {team.key_players && team.key_players.length > 0 && (
        <div className="card" style={{ padding: "20px", marginBottom: "20px" }}>
          <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", marginBottom: "12px", textTransform: "uppercase" }}>Key Players</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "12px" }}>
            {team.key_players.map((p: any, i: number) => (
              <div key={i} style={{ padding: "12px", backgroundColor: "rgba(255,255,255,0.02)", borderRadius: "8px", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <span style={{ fontSize: "14px", fontWeight: 700 }}>{p.name}</span>
                  <span style={{ fontSize: "10px", color: "var(--accent-purple)", backgroundColor: "rgba(124,92,252,0.15)", padding: "2px 6px", borderRadius: "4px" }}>{p.position}</span>
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>{p.role}</div>
                {p.club && <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>{p.club}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Squad */}
      {team.players && team.players.length > 0 && (
        <div className="card" style={{ padding: "0", overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Squad ({team.players.length})</span>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["#", "Player", "Pos", "Age"].map(h => (
                  <th key={h} style={{ padding: "8px 14px", fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textAlign: h === "Player" ? "left" : "center" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {team.players.map((p: any, i: number) => (
                <tr key={p.id} style={{ borderBottom: i < team.players.length - 1 ? "1px solid rgba(255,255,255,0.03)" : "none" }}>
                  <td style={{ padding: "10px 14px", textAlign: "center", fontSize: "12px", color: "var(--text-muted)" }}>{p.number ?? "—"}</td>
                  <td style={{ padding: "10px 14px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {p.photo && <img src={p.photo} alt={p.name} style={{ width: "28px", height: "28px", borderRadius: "50%", objectFit: "cover" }} />}
                      <span style={{ fontSize: "13px", fontWeight: 600 }}>{p.name}</span>
                    </div>
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "center" }}>
                    <span style={{ fontSize: "11px", color: "var(--accent-purple)", backgroundColor: "rgba(124,92,252,0.15)", padding: "2px 6px", borderRadius: "3px" }}>
                      {p.position || "—"}
                    </span>
                  </td>
                  <td style={{ padding: "10px 14px", textAlign: "center", fontSize: "13px", color: "var(--text-secondary)" }}>{p.age || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
