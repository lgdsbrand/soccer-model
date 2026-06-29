"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { AdvancementProb } from "@/lib/api";

const ROUNDS = [
  { key: "r32_pct", label: "R32", color: "#3d9df3" },
  { key: "r16_pct", label: "R16", color: "#7c5cfc" },
  { key: "qf_pct", label: "QF", color: "#f5a623" },
  { key: "sf_pct", label: "SF", color: "#ff6b35" },
  { key: "final_pct", label: "Final", color: "#ff4757" },
  { key: "winner_pct", label: "Win 🏆", color: "#00d084" },
];

interface Props {
  data: AdvancementProb[];
  highlightRound?: string;
}

export default function AdvancementChart({ data, highlightRound = "winner_pct" }: Props) {
  const sorted = [...data].sort((a, b) => (b as any)[highlightRound] - (a as any)[highlightRound]).slice(0, 16);
  const round = ROUNDS.find(r => r.key === highlightRound) || ROUNDS[5];

  const chartData = sorted.map(t => ({
    name: t.team_name.length > 10 ? t.team_name.slice(0, 10) + "…" : t.team_name,
    fullName: t.team_name,
    value: (t as any)[highlightRound],
    logo: t.logo,
  }));

  return (
    <div className="card" style={{ padding: "20px" }}>
      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontSize: "14px", fontWeight: 700 }}>Tournament Advancement Probabilities</div>
        <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>Based on {"{10,000}"} Monte Carlo simulations</div>
      </div>

      {/* Round selector */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        {ROUNDS.map(r => (
          <a key={r.key} href={`?round=${r.key}`} style={{
            padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 600,
            textDecoration: "none",
            backgroundColor: r.key === highlightRound ? r.color + "22" : "transparent",
            color: r.key === highlightRound ? r.color : "var(--text-muted)",
            border: `1px solid ${r.key === highlightRound ? r.color + "55" : "var(--border)"}`,
          }}>
            {r.label}
          </a>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 60 }}>
          <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 11 }} angle={-45} textAnchor="end" interval={0} />
          <YAxis tick={{ fill: "var(--text-secondary)", fontSize: 11 }} tickFormatter={v => `${v}%`} />
          <Tooltip
            contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: "8px" }}
            labelStyle={{ color: "var(--text-primary)", fontWeight: 600 }}
            formatter={(value: any, name: any, props: any) => [
              `${value}%`, props.payload.fullName
            ]}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={i === 0 ? round.color : round.color + "88"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
