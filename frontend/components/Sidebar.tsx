"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import LeagueSwitcher from "./mls/LeagueSwitcher";

const wcNav = [
  { href: "/", label: "Dashboard", icon: "⚡" },
  { href: "/matches", label: "Matches", icon: "⚽" },
  { href: "/predictions", label: "Predictions", icon: "📊" },
  { href: "/groups", label: "Group Stage", icon: "🏆" },
  { href: "/bracket", label: "Knockout Bracket", icon: "🔗" },
  { href: "/teams", label: "Teams", icon: "🌍" },
];

const mlsNav = [
  { href: "/mls", label: "Dashboard", icon: "⚡" },
  { href: "/mls/matches", label: "Matches", icon: "⚽" },
  { href: "/mls/standings", label: "Standings", icon: "🏆" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const isMls = pathname.startsWith("/mls");
  const nav = isMls ? mlsNav : wcNav;

  // Close the mobile menu automatically whenever the route changes
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <>
      {/* Mobile menu toggle */}
      <button
        onClick={() => setOpen(v => !v)}
        aria-label="Toggle menu"
        className="md:hidden"
        style={{
          position: "fixed", top: "16px", left: "16px", zIndex: 60,
          width: "40px", height: "40px", borderRadius: "8px",
          backgroundColor: "var(--bg-sidebar)", border: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "18px", color: "var(--text-primary)", cursor: "pointer",
        }}
      >
        {open ? "✕" : "☰"}
      </button>

      {/* Mobile backdrop */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          className="md:hidden"
          style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", zIndex: 40 }}
        />
      )}

      <aside
        className={`${open ? "translate-x-0" : "-translate-x-full"} md:translate-x-0`}
        style={{
          width: "256px",
          position: "fixed",
          top: 0, left: 0, bottom: 0,
          backgroundColor: "var(--bg-sidebar)",
          borderRight: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          zIndex: 50,
          transition: "transform 0.2s ease",
        }}>
      {/* Logo */}
      <div style={{ padding: "20px 20px 16px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "36px", height: "36px", borderRadius: "8px",
            background: "linear-gradient(135deg, var(--accent-purple), #5a42d4)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "18px",
          }}>🏆</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--text-primary)" }}>
              {isMls ? "MLS Predictor" : "WC Predictor"}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              {isMls ? "MLS 2026" : "World Cup 2026"}
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: "14px" }}>
        <LeagueSwitcher isMls={isMls} />
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "12px 12px", overflowY: "auto" }}>
        {nav.map(({ href, label, icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link key={href} href={href} style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "10px 12px",
              borderRadius: "8px",
              marginBottom: "2px",
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: active ? 600 : 400,
              color: active ? "var(--text-primary)" : "var(--text-secondary)",
              backgroundColor: active ? "var(--bg-hover)" : "transparent",
              borderLeft: active ? "3px solid var(--accent-purple)" : "3px solid transparent",
              transition: "all 0.15s",
            }}>
              <span style={{ fontSize: "16px" }}>{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      </aside>
    </>
  );
}
