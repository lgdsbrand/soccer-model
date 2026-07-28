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
      {/* showXg: MLS has real xG/xGA (from FotMob, same data behind
          Attack/Defense Strength). Was forced false 2026-07-28 while the
          backend was rolled back post-incident and didn't yet serve xg/xga —
          re-enabled now that the backend is being redeployed past 35f9e19. */}
      <MatchCard fixture={fixture} basePath="/mls/matches" showRecommendedPlay={false} weatherStyle="emoji" />
    </div>
  );
}
