import { api } from "@/lib/api";
import MatchCard from "@/components/MatchCard";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 30;

export default async function MatchDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let fixture;
  try {
    fixture = await api.fixture(parseInt(id));
  } catch {
    notFound();
  }

  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <Link href="/matches" style={{ fontSize: "13px", color: "var(--text-muted)", textDecoration: "none", display: "flex", alignItems: "center", gap: "4px" }}>
          ← Back to Matches
        </Link>
      </div>
      <MatchCard fixture={fixture} />
    </div>
  );
}
