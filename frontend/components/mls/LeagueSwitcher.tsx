"use client";
import Link from "next/link";

export default function LeagueSwitcher({ isMls }: { isMls: boolean }) {
  return (
    <div style={{
      display: "flex", gap: "4px", padding: "4px",
      backgroundColor: "var(--bg-primary)", borderRadius: "8px",
      border: "1px solid var(--border)", margin: "0 20px 12px",
    }}>
      <SwitchPill href="/" label="World Cup" active={!isMls} />
      <SwitchPill href="/mls" label="MLS" active={isMls} />
    </div>
  );
}

function SwitchPill({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link href={href} style={{
      flex: 1, textAlign: "center", padding: "6px 0", borderRadius: "6px",
      fontSize: "12px", fontWeight: 700, textDecoration: "none",
      color: active ? "var(--text-primary)" : "var(--text-muted)",
      backgroundColor: active ? "var(--bg-hover)" : "transparent",
      transition: "all 0.15s",
    }}>
      {label}
    </Link>
  );
}
