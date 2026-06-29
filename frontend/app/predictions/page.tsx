import { api } from "@/lib/api";
import AdvancementChart from "@/components/AdvancementChart";

export const revalidate = 600;

export default async function PredictionsPage({
  searchParams,
}: {
  searchParams: Promise<{ round?: string }>;
}) {
  const { round } = await searchParams;
  const highlightRound = round || "winner_pct";

  let advancement: any[] = [];
  let winners: any[] = [];

  try {
    [advancement, winners] = await Promise.all([api.advancement(), api.tournamentWinners()]);
  } catch {
    advancement = [];
    winners = [];
  }

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>Predictions</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
          Dixon-Coles Poisson model · 10,000 Monte Carlo simulations
        </p>
      </div>

      {advancement.length === 0 ? (
        <div className="card" style={{ padding: "60px", textAlign: "center" }}>
          <div style={{ fontSize: "40px", marginBottom: "12px" }}>📈</div>
          <div style={{ color: "var(--text-secondary)", fontSize: "14px", marginBottom: "16px" }}>
            No prediction data yet. Run the Monte Carlo simulation via the API:
          </div>
          <code style={{ color: "var(--accent-green)", fontSize: "13px", display: "block" }}>
            POST /predictions/run-monte-carlo
          </code>
          <div style={{ marginTop: "12px", color: "var(--text-muted)", fontSize: "12px" }}>
            Or run: <code style={{ color: "var(--accent-purple)" }}>python scripts/seed_historical.py --api</code>
          </div>
        </div>
      ) : (
        <>
          <AdvancementChart data={advancement} highlightRound={highlightRound} />

          {/* Tabular view */}
          <div className="card" style={{ padding: "0", overflow: "hidden", marginTop: "20px" }}>
            <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>All Teams — Advancement Probabilities</span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    {["Team", "Grp", "R32", "R16", "QF", "SF", "Final", "🏆 Win"].map(h => (
                      <th key={h} style={{ padding: "10px 14px", fontSize: "11px", color: "var(--text-muted)", fontWeight: 600, textAlign: h === "Team" ? "left" : "center", letterSpacing: "0.3px" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {advancement.sort((a, b) => b.winner_pct - a.winner_pct).map((t, i) => (
                    <tr key={t.team_id} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                      <td style={{ padding: "10px 14px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {t.logo && <img src={t.logo} alt={t.team_name} style={{ width: "20px", height: "20px", objectFit: "contain" }} />}
                          <span style={{ fontSize: "13px", fontWeight: 600 }}>{t.team_name}</span>
                        </div>
                      </td>
                      <td style={{ padding: "10px 14px", textAlign: "center", fontSize: "12px", color: "var(--text-muted)", fontWeight: 700 }}>{t.group_letter}</td>
                      {[t.r32_pct, t.r16_pct, t.qf_pct, t.sf_pct, t.final_pct].map((v, j) => (
                        <td key={j} style={{ padding: "10px 14px", textAlign: "center" }}>
                          <PctCell value={v} />
                        </td>
                      ))}
                      <td style={{ padding: "10px 14px", textAlign: "center" }}>
                        <span style={{ fontSize: "14px", fontWeight: 800, color: "var(--accent-gold)" }}>{t.winner_pct}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function PctCell({ value }: { value: number }) {
  const color = value >= 60 ? "var(--accent-green)" : value >= 30 ? "var(--accent-purple)" : value >= 10 ? "var(--accent-gold)" : "var(--text-muted)";
  return <span style={{ fontSize: "13px", fontWeight: value >= 30 ? 700 : 400, color }}>{value}%</span>;
}
