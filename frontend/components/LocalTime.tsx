"use client";
import { useEffect, useState } from "react";
import { formatDate, formatTime } from "@/lib/api";

// page.tsx is a server component, so formatDate/formatTime called directly
// there run on whatever machine renders the page (locally: dev machine's OS
// clock; on Vercel: the server's timezone, almost always UTC) — not the
// visitor's own timezone. Being "use client" alone isn't enough to fix that:
// Next.js still server-renders client components for the initial HTML, so a
// component that immediately calls formatDate/formatTime would render one
// value on the server and a different one once the browser hydrates it,
// which React treats as a hydration mismatch (visible console error, and can
// cause the mismatched DOM node to flicker/reset). Deferring the real value
// to after mount (via useEffect) means the server render and the browser's
// first render are both empty, so they match — the real local value appears
// a moment later as a normal client-side update, not part of hydration.

export function LocalDate({ ts }: { ts: number }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <>{formatDate(ts)}</> : null;
}

export function LocalTime({ ts }: { ts: number }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <>{formatTime(ts)}</> : null;
}
