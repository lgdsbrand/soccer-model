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
      {/* showXg temporarily forced false again: the live backend was rolled
          back (2026-07-28 incident) to a commit before xg/xga were added to
          home/away_team_stats, so showing this row right now would render
          "1.62 / —" (data missing) instead of a real number. Safe to flip
          back to the default (true) once the backend is redeployed past
          35f9e19 and confirmed stable — see MLS_BUILD_STATUS.md. */}
      <MatchCard fixture={fixture} basePath="/mls/matches" showRecommendedPlay={false} showXg={false} weatherStyle="emoji" />
    </div>
  );
}
