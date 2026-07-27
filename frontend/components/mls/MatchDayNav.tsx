"use client";

// Unlike DateNav (a Yesterday/Today/Tomorrow relative quick-jump, built for
// the World Cup's near-daily schedule), MLS only plays 1-2x/week — "today"
// and "tomorrow" are very often empty, which would make DateNav render
// nothing. This instead shows a pill for every one of the next N match
// days themselves, which is what "date selector showing the next N match
// days" actually needs for a sparse weekly schedule.
//
// Note: unlike DateNav, this deliberately does NOT scrollIntoView the
// active date on mount. DateNav's target (today) can be far down a
// multi-week full-season list, so jumping to it on load is the point.
// Here activeDate is always dates[0] — the first section on the page
// already — so scrolling to it just shoves the heading and this pill
// row up off-screen underneath the fixed mobile menu button.
//
// Each pill shows a relative label (Today/Tomorrow/"In N Days") above the
// actual date, styled per Tyler's reference (MLS_fromPicsFromTyler/IMG_5026.jpeg)
// — a small caps label over a bold date, with the active day filled solid.
export default function MatchDayNav({ dates, activeDate, todayStr }: { dates: string[]; activeDate?: string; todayStr: string }) {
  if (dates.length === 0) return null;

  return (
    <div className="match-day-nav" style={{ display: "flex", gap: "8px", marginBottom: "20px" }}>
      {dates.map(dateStr => {
        const active = dateStr === activeDate;
        return (
          <a key={dateStr} href={`#date-${dateStr}`} style={pill(active)}>
            <div style={labelStyle(active)}>{relativeLabel(dateStr, todayStr)}</div>
            <div style={dateStyle(active)}>{formatShort(dateStr)}</div>
          </a>
        );
      })}
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
  if (diff === -1) return "Yesterday";
  if (diff > 1) return `In ${diff} Days`;
  return `${-diff} Days Ago`;
}

function formatShort(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    month: "short", day: "numeric", timeZone: "UTC",
  });
}

function pill(active: boolean): React.CSSProperties {
  return {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "2px",
    flexShrink: 0,
    padding: "8px 14px",
    borderRadius: "12px",
    textDecoration: "none",
    border: `1px solid ${active ? "var(--accent-purple)" : "var(--border)"}`,
    backgroundColor: active ? "var(--accent-purple)" : "transparent",
  };
}

function labelStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: "9px",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.4px",
    whiteSpace: "nowrap",
    color: active ? "rgba(255,255,255,0.85)" : "var(--text-muted)",
  };
}

function dateStyle(active: boolean): React.CSSProperties {
  return {
    fontSize: "14px",
    fontWeight: 800,
    whiteSpace: "nowrap",
    color: active ? "#fff" : "var(--text-primary)",
  };
}
