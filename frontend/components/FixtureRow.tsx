"use client";

import Link from "next/link";
import type { Fixture } from "@/lib/api";
import { formatDate, formatTime, getStatusLabel } from "@/lib/api";

export default function FixtureRow({ fixture }: { fixture: Fixture }) {
  const status = getStatusLabel(fixture.status);
  const isLive = ["1H", "2H", "HT", "ET", "P"].includes(fixture.status);
  const isFinished = ["FT", "AET", "PEN"].includes(fixture.status);

  return (
    <Link href={`/matches/${fixture.id}`} style={{ textDecoration: "none" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: "12px",
        padding: "12px 16px", borderRadius: "8px",
        border: "1px solid var(--border)",
        backgroundColor: "var(--bg-card)",
        marginBottom: "6px",
        transition: "border-color 0.15s",
        cursor: "pointer",
      }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--accent-purple)")}
        onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
      >
        {/* Status */}
        <div style={{ minWidth: "90px", textAlign: "center" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "4px" }}>
            {isLive && <div className="live-dot" style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: "var(--accent-green)" }} />}
            <span style={{ fontSize: "11px", color: status.color, fontWeight: 600 }}>{status.label}</span>
          </div>
          <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
            {formatTime(fixture.date_utc)}
          </div>
        </div>

        {/* Home */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px", justifyContent: "flex-end" }}>
          <span style={{ fontSize: "14px", fontWeight: 600 }}>{fixture.home_name}</span>
          {fixture.home_logo && <img src={fixture.home_logo} alt="" style={{ width: "24px", height: "24px", objectFit: "contain" }} />}
        </div>

        {/* Score */}
        <div style={{ textAlign: "center", minWidth: "60px" }}>
          {(isFinished || isLive) ? (
            <span style={{ fontSize: "18px", fontWeight: 800, letterSpacing: "-0.5px" }}>
              {fixture.home_score ?? 0} – {fixture.away_score ?? 0}
            </span>
          ) : (
            <span style={{ fontSize: "14px", color: "var(--text-muted)", fontWeight: 600 }}>vs</span>
          )}
        </div>

        {/* Away */}
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "8px" }}>
          {fixture.away_logo && <img src={fixture.away_logo} alt="" style={{ width: "24px", height: "24px", objectFit: "contain" }} />}
          <span style={{ fontSize: "14px", fontWeight: 600 }}>{fixture.away_name}</span>
        </div>

        {/* Win % */}
        {fixture.home_win_pct != null && (
          <div style={{ textAlign: "right", minWidth: "80px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Prob</div>
            <div style={{ fontSize: "12px", fontWeight: 600 }}>
              <span style={{ color: "var(--accent-green)" }}>{fixture.home_win_pct}%</span>
              <span style={{ color: "var(--text-muted)", margin: "0 4px" }}>·</span>
              <span style={{ color: "var(--accent-purple)" }}>{fixture.away_win_pct}%</span>
            </div>
          </div>
        )}

        <div style={{ color: "var(--text-muted)", fontSize: "12px" }}>→</div>
      </div>
    </Link>
  );
}
