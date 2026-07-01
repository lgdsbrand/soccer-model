"use client";
import { formatDate, formatTime } from "@/lib/api";

// page.tsx is a server component, so formatDate/formatTime called directly
// there run on whatever machine renders the page (locally: dev machine's OS
// clock; on Vercel: the server's timezone, almost always UTC) — not the
// visitor's own timezone. Wrapping the same formatters in a client component
// makes them execute in the visitor's browser instead, so everyone sees
// match times in their own local time, consistent with MatchCard.tsx (which
// is already a client component and doesn't have this issue).

export function LocalDate({ ts }: { ts: number }) {
  return <>{formatDate(ts)}</>;
}

export function LocalTime({ ts }: { ts: number }) {
  return <>{formatTime(ts)}</>;
}
