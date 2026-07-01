"use client";
import type { Fixture } from "@/lib/api";
import { formatDate } from "@/lib/api";
import Link from "next/link";

const ROUND_SHORT: Record<string, string> = {
  "Round of 32": "R32",
  "Round of 16": "R16",
  "Quarter-finals": "QF",
  "Semi-finals": "SF",
  "Final": "Final",
};

const COL_W = 152;
const CON_W = 28;
const CARD_H = 74;
const LINE = "rgba(255,255,255,0.14)";
const GOLD = "rgba(255,180,0,0.4)";
const CARD_BG = "#1a1a30";
const CARD_BORDER = "rgba(255,255,255,0.3)";
const ROW_SEP = "rgba(255,255,255,0.18)";

function cy(i: number, n: number, H: number): number {
  return n > 0 ? ((2 * i + 1) / (2 * n)) * H : H / 2;
}

// Two adjacent matches in left col converge to one match in right col
function StandardConnector({ lc, rc, H }: { lc: number; rc: number; H: number }) {
  const mx = CON_W / 2;
  return (
    <svg width={CON_W} height={H} style={{ flexShrink: 0 }}>
      {Array.from({ length: rc }, (_, nmi) => {
        const i1 = nmi * 2, i2 = nmi * 2 + 1;
        const y1 = cy(i1, lc, H);
        const y2 = i2 < lc ? cy(i2, lc, H) : y1;
        const toY = cy(nmi, rc, H);
        return (
          <g key={nmi}>
            <line x1={0} y1={y1} x2={mx} y2={y1} stroke={LINE} strokeWidth={1} />
            {i2 < lc && <line x1={0} y1={y2} x2={mx} y2={y2} stroke={LINE} strokeWidth={1} />}
            {i2 < lc && <line x1={mx} y1={y1} x2={mx} y2={y2} stroke={LINE} strokeWidth={1} />}
            <line x1={mx} y1={toY} x2={CON_W} y2={toY} stroke={LINE} strokeWidth={1} />
          </g>
        );
      })}
    </svg>
  );
}

// One match in left col fans out to two matches in right col (right-side of bracket)
function ExpandingConnector({ lc, rc, H }: { lc: number; rc: number; H: number }) {
  const mx = CON_W / 2;
  return (
    <svg width={CON_W} height={H} style={{ flexShrink: 0 }}>
      {Array.from({ length: lc }, (_, mi) => {
        const fromY = cy(mi, lc, H);
        const r1 = mi * 2, r2 = mi * 2 + 1;
        const yr1 = cy(r1, rc, H);
        const yr2 = r2 < rc ? cy(r2, rc, H) : yr1;
        return (
          <g key={mi}>
            <line x1={0} y1={fromY} x2={mx} y2={fromY} stroke={LINE} strokeWidth={1} />
            {r2 < rc && <line x1={mx} y1={yr1} x2={mx} y2={yr2} stroke={LINE} strokeWidth={1} />}
            <line x1={mx} y1={yr1} x2={CON_W} y2={yr1} stroke={LINE} strokeWidth={1} />
            {r2 < rc && <line x1={mx} y1={yr2} x2={CON_W} y2={yr2} stroke={LINE} strokeWidth={1} />}
          </g>
        );
      })}
    </svg>
  );
}

// Straight horizontal connector (SF → Final, 1-to-1)
function StraightConnector({ n, H }: { n: number; H: number }) {
  const y = cy(0, Math.max(n, 1), H);
  return (
    <svg width={CON_W} height={H} style={{ flexShrink: 0 }}>
      <line x1={0} y1={y} x2={CON_W} y2={y} stroke={GOLD} strokeWidth={1.5} />
    </svg>
  );
}

function MatchCol({ matches, H, isFinal }: { matches: Fixture[]; H: number; isFinal?: boolean }) {
  return (
    <div style={{ width: COL_W, height: H, display: "flex", flexDirection: "column", justifyContent: "space-around" }}>
      {matches.map(f => <BracketMatch key={f.id} fixture={f} isFinal={isFinal} />)}
    </div>
  );
}

function ColHeader({ label, isCenter }: { label: string; isCenter?: boolean }) {
  return (
    <div style={{
      width: COL_W, height: 36,
      display: "flex", alignItems: "center", justifyContent: "center", gap: "5px",
    }}>
      {isCenter && <span style={{ fontSize: "15px" }}>🏆</span>}
      <span style={{
        fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.6px",
        color: isCenter ? "var(--accent-gold)" : "var(--text-muted)",
      }}>{label}</span>
    </div>
  );
}

const SEMI_ROUNDS = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals"] as const;

// Given the already-fixed order of a later round, place each earlier-round match
// directly behind its true parent slot by tracing team IDs (a team can only have
// come from the one earlier-round fixture it actually played in). This replaces
// naive "split in half, pair by index" — which silently assumes fixture order
// reflects real bracket adjacency, and produces visually wrong connector lines
// whenever it doesn't (e.g. a knockout draw isn't simply date-ordered pairs).
// Falls back to original order for legs that are still fully TBD on both sides,
// since there's no lineage to trace yet and any order is equally provisional.
function reorderByLineage(laterOrdered: Fixture[], earlierMatches: Fixture[]): Fixture[] {
  const used = new Set<number>();
  const result: Fixture[] = [];
  for (const laterMatch of laterOrdered) {
    for (const teamId of [laterMatch.home_team_id, laterMatch.away_team_id]) {
      let parent = teamId != null
        ? earlierMatches.find(m => !used.has(m.id) && (m.home_team_id === teamId || m.away_team_id === teamId))
        : undefined;
      if (!parent) {
        parent = earlierMatches.find(m => !used.has(m.id));
      }
      if (parent) {
        used.add(parent.id);
        result.push(parent);
      }
    }
  }
  for (const m of earlierMatches) {
    if (!used.has(m.id)) result.push(m);
  }
  return result;
}

export default function BracketView({ fixtures }: { fixtures: Fixture[] }) {
  const byRound: Record<string, Fixture[]> = {};
  for (const f of fixtures) {
    const r = f.round || "Unknown";
    if (!byRound[r]) byRound[r] = [];
    byRound[r].push(f);
  }

  const hasAny = [...SEMI_ROUNDS, "Final"].some(r => byRound[r]?.length);
  if (!hasAny) {
    return (
      <div className="card" style={{ padding: "64px", textAlign: "center" }}>
        <div style={{ fontSize: "56px", marginBottom: "16px" }}>🏆</div>
        <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "8px" }}>Knockout Bracket</div>
        <div style={{ fontSize: "14px", color: "var(--text-muted)" }}>Fixtures will appear once the group stage is complete</div>
      </div>
    );
  }

  // Correct each round's order (bottom-up isn't right either — the ground truth
  // flows from whichever round already has real teams in it, so we anchor on
  // the Final and work backward; any leg with no confirmed teams yet is a no-op
  // and keeps its original order).
  const REORDER_CHAIN = ["Final", "Semi-finals", "Quarter-finals", "Round of 16", "Round of 32"] as const;
  const orderedByRound: Record<string, Fixture[]> = { Final: byRound["Final"] || [] };
  for (let i = 1; i < REORDER_CHAIN.length; i++) {
    const round = REORDER_CHAIN[i];
    orderedByRound[round] = reorderByLineage(orderedByRound[REORDER_CHAIN[i - 1]] || [], byRound[round] || []);
  }

  // Split each pre-final round into left (first half) and right (second half)
  const L: Record<string, Fixture[]> = {};
  const R: Record<string, Fixture[]> = {};
  for (const r of SEMI_ROUNDS) {
    const all = orderedByRound[r] || [];
    const half = Math.ceil(all.length / 2);
    L[r] = all.slice(0, half);
    R[r] = all.slice(half);
  }
  const finalMatches = byRound["Final"] || [];
  const thirdPlace = byRound["3rd Place"] || [];

  const hasR32 = (L["Round of 32"].length + R["Round of 32"].length) > 0;
  const firstColCount = hasR32 ? (L["Round of 32"].length || 1) : (L["Round of 16"].length || 1);
  const H = Math.max(400, firstColCount * (CARD_H + 4));

  const lR32 = L["Round of 32"].length, lR16 = L["Round of 16"].length;
  const lQF = L["Quarter-finals"].length, lSF = L["Semi-finals"].length;
  const rSF = R["Semi-finals"].length, rQF = R["Quarter-finals"].length;
  const rR16 = R["Round of 16"].length, rR32 = R["Round of 32"].length;

  return (
    <div style={{ overflowX: "auto" }}>
      {/* Column headers */}
      <div style={{ display: "flex" }}>
        {hasR32 && <><ColHeader label="R32" /><div style={{ width: CON_W }} /></>}
        <ColHeader label="R16" /><div style={{ width: CON_W }} />
        <ColHeader label="QF" /><div style={{ width: CON_W }} />
        <ColHeader label="SF" /><div style={{ width: CON_W }} />
        <ColHeader label="Final" isCenter />
        <div style={{ width: CON_W }} /><ColHeader label="SF" />
        <div style={{ width: CON_W }} /><ColHeader label="QF" />
        <div style={{ width: CON_W }} /><ColHeader label="R16" />
        {hasR32 && <><div style={{ width: CON_W }} /><ColHeader label="R32" /></>}
      </div>

      {/* Bracket body */}
      <div style={{ display: "flex" }}>
        {/* LEFT side */}
        {hasR32 && (
          <>
            <MatchCol matches={L["Round of 32"]} H={H} />
            <StandardConnector lc={lR32} rc={lR16} H={H} />
          </>
        )}
        <MatchCol matches={L["Round of 16"]} H={H} />
        <StandardConnector lc={lR16} rc={lQF} H={H} />
        <MatchCol matches={L["Quarter-finals"]} H={H} />
        <StandardConnector lc={lQF} rc={lSF} H={H} />
        <MatchCol matches={L["Semi-finals"]} H={H} />
        <StraightConnector n={lSF} H={H} />

        {/* FINAL (center) */}
        <div style={{ width: COL_W, height: H, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {finalMatches[0]
            ? <div style={{ width: "100%" }}><BracketMatch fixture={finalMatches[0]} isFinal /></div>
            : (
              <div style={{
                border: `1px solid ${GOLD}`, borderRadius: "8px",
                padding: "14px 12px", backgroundColor: "rgba(255,180,0,0.04)",
                textAlign: "center", width: "100%",
              }}>
                <div style={{ fontSize: "18px", marginBottom: "4px" }}>🏆</div>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>TBD</div>
              </div>
            )
          }
        </div>

        {/* RIGHT side */}
        <StraightConnector n={rSF} H={H} />
        <MatchCol matches={R["Semi-finals"]} H={H} />
        <ExpandingConnector lc={rSF} rc={rQF} H={H} />
        <MatchCol matches={R["Quarter-finals"]} H={H} />
        <ExpandingConnector lc={rQF} rc={rR16} H={H} />
        <MatchCol matches={R["Round of 16"]} H={H} />
        {hasR32 && (
          <>
            <ExpandingConnector lc={rR16} rc={rR32} H={H} />
            <MatchCol matches={R["Round of 32"]} H={H} />
          </>
        )}
      </div>

      {/* 3rd Place — below the Final column */}
      {thirdPlace.length > 0 && (
        <div style={{ marginTop: "14px", paddingLeft: `${(hasR32 ? 4 : 3) * (COL_W + CON_W)}px` }}>
          <div style={{ width: COL_W }}>
            <div style={{ textAlign: "center", fontSize: "10px", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.6px", marginBottom: "8px" }}>
              🥉 3rd Place Match
            </div>
            <BracketMatch fixture={thirdPlace[0]} />
          </div>
        </div>
      )}
    </div>
  );
}

function BracketMatch({ fixture, isFinal }: { fixture: Fixture; isFinal?: boolean }) {
  const isFinished = ["FT", "AET", "PEN"].includes(fixture.status);
  const isLive = ["1H", "2H", "HT", "ET", "P"].includes(fixture.status);
  const homeWin = isFinished && (fixture.home_score ?? 0) > (fixture.away_score ?? 0);
  const awayWin = isFinished && (fixture.away_score ?? 0) > (fixture.home_score ?? 0);
  const isTbd = (name?: string) => !name || name === "TBD";

  return (
    <Link href={`/matches/${fixture.id}`} style={{ textDecoration: "none", display: "block", margin: "0 3px" }}>
      <div
        style={{
          border: `1px solid ${isFinal ? GOLD : CARD_BORDER}`,
          borderRadius: "8px", overflow: "hidden",
          backgroundColor: isFinal ? "rgba(255,180,0,0.06)" : CARD_BG,
          cursor: "pointer", transition: "border-color 0.15s, box-shadow 0.15s",
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = "rgba(124,92,252,0.7)";
          e.currentTarget.style.boxShadow = "0 0 0 1px rgba(124,92,252,0.3)";
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = isFinal ? GOLD : CARD_BORDER;
          e.currentTarget.style.boxShadow = "none";
        }}
      >
        <div style={{ height: CARD_H, display: "flex", flexDirection: "column" }}>
          <TeamRow name={fixture.home_name} logo={fixture.home_logo}
            score={isFinished || isLive ? (fixture.home_score ?? 0) : undefined}
            isWinner={homeWin} isTbd={isTbd(fixture.home_name)} showBorder />
          <TeamRow name={fixture.away_name} logo={fixture.away_logo}
            score={isFinished || isLive ? (fixture.away_score ?? 0) : undefined}
            isWinner={awayWin} isTbd={isTbd(fixture.away_name)} showBorder={false} />
        </div>
        {isLive && (
          <div style={{ padding: "3px 10px", borderTop: "1px solid rgba(0,208,132,0.2)", backgroundColor: "rgba(0,208,132,0.08)", display: "flex", gap: "5px", alignItems: "center" }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", backgroundColor: "var(--accent-green)" }} />
            <span style={{ fontSize: "9px", fontWeight: 700, color: "var(--accent-green)", letterSpacing: "0.5px" }}>LIVE</span>
          </div>
        )}
      </div>
    </Link>
  );
}

function TeamRow({ name, logo, score, isWinner, isTbd, showBorder }: {
  name?: string; logo?: string; score?: number; isWinner: boolean; isTbd: boolean; showBorder: boolean;
}) {
  return (
    <div style={{
      flex: "1 1 0", minHeight: 0, boxSizing: "border-box",
      display: "flex", alignItems: "center", gap: "7px", padding: "0 10px",
      borderBottom: showBorder ? `1px solid ${ROW_SEP}` : "none",
      backgroundColor: isWinner ? "rgba(0,208,132,0.07)" : "transparent",
    }}>
      {logo
        ? <img src={logo} alt="" style={{ width: 18, height: 18, objectFit: "contain", flexShrink: 0 }} />
        : <div style={{ width: 18, height: 18, borderRadius: "50%", backgroundColor: "rgba(255,255,255,0.08)", flexShrink: 0 }} />
      }
      <span style={{
        flex: 1, fontSize: "12px",
        fontWeight: isWinner ? 700 : 500,
        color: isWinner ? "var(--accent-green)" : isTbd ? "var(--text-muted)" : "var(--text-primary)",
        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {name || "TBD"}
      </span>
      {score !== undefined && (
        <span style={{ fontSize: "14px", fontWeight: 800, minWidth: "18px", textAlign: "right", color: isWinner ? "var(--accent-green)" : "var(--text-secondary)" }}>
          {score}
        </span>
      )}
    </div>
  );
}
