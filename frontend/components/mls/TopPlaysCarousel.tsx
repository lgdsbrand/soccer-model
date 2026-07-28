"use client";

import { useState } from "react";
import Link from "next/link";
import type { MlsTopPlaysDay } from "@/lib/mlsApi";

// Day-switcher for the dashboard's Top Plays section. Previously this only
// ever showed *today's* plays and hid the whole section if today had no MLS
// games — on a slow/off day that meant a demo would show nothing at all.
// The backend now scans forward and returns the next few days that actually
// have plays; this renders a MatchDayNav-style pill per day (defaulting to
// the first one, which is guaranteed to have data) so there's always
// something to show.
export default function TopPlaysCarousel({ days, todayStr }: { days: MlsTopPlaysDay[]; todayStr: string }) {
  const [selected, setSelected] = useState(days[0]?.date);
  if (days.length === 0) return null;

  const active = days.find(d => d.date === selected) ?? days[0];
  const cards: { key: string; label: string; play: MlsTopPlaysDay["btts"] }[] = [
    { key: "btts", label: "Best BTTS Play", play: active.btts },
    { key: "over_1_5", label: "Best Over 1.5 Play", play: active.over_1_5 },
    { key: "over_2_5", label: "Best Over 2.5 Play", play: active.over_2_5 },
  ];

  return (
    <div style={{ marginBottom: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
        <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
          Top Plays
        </div>
        {days.length > 1 && (
          <div style={{ display: "flex", gap: "6px", overflowX: "auto" }}>
            {days.map(d => (
              <button
                key={d.date}
                onClick={() => setSelected(d.date)}
                style={{
                  fontSize: "11px", fontWeight: 700, padding: "5px 10px", borderRadius: "999px",
                  border: `1px solid ${d.date === active.date ? "var(--accent-purple)" : "var(--border)"}`,
                  backgroundColor: d.date === active.date ? "rgba(124,92,252,0.15)" : "transparent",
                  color: d.date === active.date ? "var(--accent-purple)" : "var(--text-muted)",
                  cursor: "pointer", flexShrink: 0, whiteSpace: "nowrap",
                }}
              >
                {relativeLabel(d.date, todayStr)}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="top-plays-scroll" style={{ display: "flex", gap: "16px", overflowX: "auto", paddingBottom: "6px", scrollSnapType: "x mandatory" }}>
        {cards.map(({ key, label, play }) => (
          <div key={key} className="card" style={{ padding: "16px", minWidth: "220px", flexShrink: 0, scrollSnapAlign: "start" }}>
            <div style={{ fontSize: "11px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "10px" }}>
              {label}
            </div>
            {play ? (
              <Link href={`/mls/matches/${play.fixture_id}`} style={{ textDecoration: "none", color: "inherit", display: "block" }}>
                <div style={{ fontSize: "28px", fontWeight: 900, color: "var(--accent-green)", marginBottom: "8px" }}>
                  {play.value.toFixed(1)}%
                </div>
                <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>
                  {play.home_name} vs {play.away_name}
                </div>
              </Link>
            ) : (
              <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>No data yet</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function daysBetween(fromStr: string, toStr: string): number {
  const [fy, fm, fd] = fromStr.split("-").map(Number);
  const [ty, tm, td] = toStr.split("-").map(Number);
  const from = Date.UTC(fy, fm - 1, fd);
  const to = Date.UTC(ty, tm - 1, td);
  return Math.round((to - from) / 86400000);
}

function relativeLabel(dateStr: string, todayStr: string): string {
  const diff = daysBetween(todayStr, dateStr);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff > 1) return `In ${diff} Days`;
  return dateStr;
}
