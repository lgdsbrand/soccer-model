import { mlsApi } from "@/lib/mlsApi";
import MatchCard from "@/components/MatchCard";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 30;

export default async function MlsMatchDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let fixture;
  try {
    fixture = await mlsApi.fixture(parseInt(id));
  } catch {
    notFound();
  }

  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <Link href="/mls/matches" style={{ fontSize: "13px", color: "var(--text-muted)", textDecoration: "none", display: "flex", alignItems: "center", gap: "4px" }}>
          ← Back to Matches
        </Link>
      </div>
      {/* showXg forced false: reverted 2026-07-28 after the xg/xga backend
          change (35f9e19) was implicated in a production incident (never
          confirmed as the actual root cause — no server logs were available
          to verify). MLS's home/away_team_stats no longer includes xg/xga
          (reverted in fixtures.py) so this now matches what the backend
          actually returns. Re-enable only alongside re-adding that backend
          SELECT, and only after finding the real root cause. */}
      <MatchCard fixture={fixture} basePath="/mls/matches" showRecommendedPlay={false} showXg={false} weatherStyle="emoji" />
    </div>
  );
}
