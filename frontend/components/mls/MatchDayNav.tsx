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
export default function MatchDayNav({ dates, activeDate }: { dates: string[]; activeDate?: string }) {
  if (dates.length === 0) return null;

  return (
    <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap" }}>
      {dates.map(dateStr => (
        <a key={dateStr} href={`#date-${dateStr}`} style={pill(dateStr === activeDate)}>
          {formatShort(dateStr)}
        </a>
      ))}
    </div>
  );
}

function formatShort(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", {
    weekday: "short", month: "short", day: "numeric", timeZone: "UTC",
  });
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
