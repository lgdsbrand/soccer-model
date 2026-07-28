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
      {/* showXg: MLS has real xG/xGA (FotMob, same data behind Attack/Defense
          Strength). Re-attempted 2026-07-28 after a prior try was implicated
          (never confirmed) in a production incident — see
          MLS_BUILD_STATUS.md's incident section for what's known. */}
      <MatchCard fixture={fixture} basePath="/mls/matches" showRecommendedPlay={false} weatherStyle="emoji" />
    </div>
  );
}
