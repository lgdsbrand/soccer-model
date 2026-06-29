"use client";
import { useEffect } from "react";

function offsetDate(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function DateNav({ todayStr, dates }: { todayStr: string; dates: string[] }) {
  useEffect(() => {
    const el = document.getElementById(`date-${todayStr}`);
    if (el) el.scrollIntoView({ behavior: "instant", block: "start" });
  }, [todayStr]);

  const yesterday = offsetDate(todayStr, -1);
  const tomorrow = offsetDate(todayStr, 1);
  const hasYesterday = dates.includes(yesterday);
  const hasToday = dates.includes(todayStr);
  const hasTomorrow = dates.includes(tomorrow);

  if (!hasYesterday && !hasToday && !hasTomorrow) return null;

  return (
    <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap" }}>
      {hasYesterday && (
        <a href={`#date-${yesterday}`} style={pill(false)}>← Yesterday</a>
      )}
      {hasToday && (
        <a href={`#date-${todayStr}`} style={pill(true)}>Today</a>
      )}
      {hasTomorrow && (
        <a href={`#date-${tomorrow}`} style={pill(false)}>Tomorrow →</a>
      )}
    </div>
  );
}

function pill(active: boolean): React.CSSProperties {
  return {
    display: "inline-block",
    padding: "6px 16px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: 700,
    textDecoration: "none",
    border: `1px solid ${active ? "rgba(0,208,132,0.5)" : "var(--border)"}`,
    backgroundColor: active ? "rgba(0,208,132,0.1)" : "transparent",
    color: active ? "var(--accent-green)" : "var(--text-secondary)",
  };
}
