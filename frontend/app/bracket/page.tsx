import { api } from "@/lib/api";
import BracketView from "@/components/BracketView";
import type { Fixture } from "@/lib/api";

export const revalidate = 300;

export default async function BracketPage() {
  let fixtures: Awaited<ReturnType<typeof api.bracket>> = [];
  try {
    fixtures = await api.bracket();
  } catch {
    fixtures = [];
  }

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 style={{ fontSize: "22px", fontWeight: 800, margin: 0 }}>Knockout Bracket</h1>
        <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "4px" }}>
          R32 · R16 · QF · SF · Final — all rounds shown, scroll right if needed
        </p>
      </div>
      <BracketView fixtures={fixtures} />
    </div>
  );
}
