"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const nav = [
  { href: "/", label: "Dashboard", icon: "⚡" },
  { href: "/matches", label: "Matches", icon: "⚽" },
  { href: "/predictions", label: "Predictions", icon: "📊" },
  { href: "/groups", label: "Group Stage", icon: "🏆" },
  { href: "/bracket", label: "Knockout Bracket", icon: "🔗" },
  { href: "/teams", label: "Teams", icon: "🌍" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside style={{
      width: "256px",
      position: "fixed",
      top: 0, left: 0, bottom: 0,
      backgroundColor: "var(--bg-sidebar)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      zIndex: 50,
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
            <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--text-primary)" }}>WC Predictor</div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>World Cup 2026</div>
          </div>
        </div>
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
  );
}
