import { computeFatigueBudget } from "../fatigueBudget";
import type { WorkingSetLite } from "../fatigueBudget";

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

function ws(overrides: Partial<WorkingSetLite> = {}): WorkingSetLite {
  return {
    setType: "working",
    weight: 135,
    reps: 5,
    rir: 2,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Strength budget (= 3)
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — strength budget", () => {
  it("budget is 3 for strength goal", () => {
    const result = computeFatigueBudget({ goal: "strength", sets: [] });
    expect(result.budget).toBe(3);
  });

  it("caps on 2 sets at RIR 1 (2+2 = 4 >= 3)", () => {
    const sets = [ws({ rir: 1 }), ws({ rir: 1 })];
    const result = computeFatigueBudget({ goal: "strength", sets });
    expect(result.isCapped).toBe(true);
    expect(result.fatigueScore).toBe(4);
  });

  it("stays under budget with easy sets (RIR ≥ 4 → 0 pts each)", () => {
    const sets = [ws({ rir: 4 }), ws({ rir: 5 }), ws({ rir: 4 })];
    const result = computeFatigueBudget({ goal: "strength", sets });
    expect(result.isCapped).toBe(false);
    expect(result.fatigueScore).toBe(0);
  });

  // B: cap floor — 1 hard set must NOT cap strength
  it("B: single hard set (RIR 1) does NOT cap strength (cap floor)", () => {
    const sets = [ws({ rir: 1 })]; // 2 pts, rawCapped=false (2 < 3), no issue
    const result = computeFatigueBudget({ goal: "strength", sets });
    expect(result.isCapped).toBe(false);
  });

  it("B: 1 very hard set (RIR 0) does NOT hit budget (3 pts = 3, exception: true failure caps)", () => {
    // RIR 0 → 3 pts, budget 3 → rawCapped = true, but isTrueFailure=true so cap floor passes
    const sets = [ws({ rir: 0 })];
    const result = computeFatigueBudget({ goal: "strength", sets });
    expect(result.isCapped).toBe(true); // failure exception overrides floor
  });

  it("B: 2 hard sets can cap strength even with cap floor", () => {
    const sets = [ws({ rir: 1 }), ws({ rir: 1 })]; // 4 pts >= 3 AND 2 sets
    const result = computeFatigueBudget({ goal: "strength", sets });
    expect(result.isCapped).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Hypertrophy budget (= 5)
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — hypertrophy budget", () => {
  it("budget is 5 for hypertrophy goal", () => {
    const result = computeFatigueBudget({ goal: "hypertrophy", sets: [] });
    expect(result.budget).toBe(5);
  });

  it("allows 3 sets at RIR 2 (3 pts total < 5)", () => {
    const sets = [ws({ rir: 2 }), ws({ rir: 2 }), ws({ rir: 2 })];
    const result = computeFatigueBudget({ goal: "hypertrophy", sets });
    expect(result.isCapped).toBe(false);
    expect(result.fatigueScore).toBe(3);
  });

  it("caps on 2 consecutive failures (3+3 = 6 >= 5)", () => {
    const sets = [ws({ rir: 0 }), ws({ rir: 0 })];
    const result = computeFatigueBudget({ goal: "hypertrophy", sets });
    expect(result.isCapped).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// General budget (= 4)
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — general budget", () => {
  it("budget is 4 for general goal", () => {
    const result = computeFatigueBudget({ goal: "general", sets: [] });
    expect(result.budget).toBe(4);
  });

  it("slightly more flexible than strength: 2 sets RIR 1 (4 pts) caps general (4 >= 4)", () => {
    const sets = [ws({ rir: 1 }), ws({ rir: 1 })];
    const result = computeFatigueBudget({ goal: "general", sets });
    expect(result.isCapped).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Trend add-ons
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — reps drop add-on", () => {
  it("adds +1 when reps drop ≥ 2 at similar load", () => {
    const withoutDrop = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 135, reps: 8 })],
    });
    const withDrop = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 135, reps: 5 })],
    });
    expect(withDrop.fatigueScore).toBe(withoutDrop.fatigueScore + 1);
  });

  it("does NOT add +1 when reps drop < 2", () => {
    const a = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 135, reps: 7 })],
    });
    const b = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 135, reps: 8 })],
    });
    expect(a.fatigueScore).toBe(b.fatigueScore);
  });

  it("does NOT add reps_drop when load differs by > 5 lb (default tolerance)", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 145, reps: 5 })],
    });
    // load diff = 10 lb > default 5 → not similar load → reps_drop not triggered
    const baseline = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 145, reps: 8 })],
    });
    expect(result.fatigueScore).toBe(baseline.fatigueScore);
  });

  // C: incrementLb controls the "similar load" tolerance
  it("C: reps_drop triggers when weight diff <= incrementLb", () => {
    // weight diff = 10 lb; with incrementLb = 10, it IS similar load
    const withDrop = computeFatigueBudget({
      goal: "hypertrophy",
      incrementLb: 10,
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 145, reps: 5 })],
    });
    const noDrop = computeFatigueBudget({
      goal: "hypertrophy",
      incrementLb: 10,
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 145, reps: 8 })],
    });
    expect(withDrop.fatigueScore).toBe(noDrop.fatigueScore + 1);
  });

  it("C: reps_drop does NOT trigger when weight diff > incrementLb", () => {
    // weight diff = 10 lb; with incrementLb = 5, it is NOT similar load
    const withDrop = computeFatigueBudget({
      goal: "hypertrophy",
      incrementLb: 5,
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 145, reps: 5 })],
    });
    const noDrop = computeFatigueBudget({
      goal: "hypertrophy",
      incrementLb: 5,
      sets: [ws({ rir: 2, weight: 135, reps: 8 }), ws({ rir: 2, weight: 145, reps: 8 })],
    });
    expect(withDrop.fatigueScore).toBe(noDrop.fatigueScore);
  });
});

describe("computeFatigueBudget — overshoot add-on", () => {
  it("adds +1 when load increases AND RIR drops ≥ 2", () => {
    // same RIR drop but same weight (no overshoot)
    const withoutOvershoot = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 4, weight: 135, reps: 6 }), ws({ rir: 1, weight: 135, reps: 6 })],
    });
    // load increased, same RIR drop (overshoot)
    const withOvershoot = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 4, weight: 135, reps: 6 }), ws({ rir: 1, weight: 145, reps: 6 })],
    });
    expect(withOvershoot.fatigueScore).toBe(withoutOvershoot.fatigueScore + 1);
  });

  it("does NOT add +1 when load increases but RIR drop < 2", () => {
    const without = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 3, weight: 135, reps: 6 }), ws({ rir: 2, weight: 145, reps: 6 })],
    });
    const withSame = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 3, weight: 135, reps: 6 }), ws({ rir: 2, weight: 135, reps: 6 })],
    });
    expect(without.fatigueScore).toBe(withSame.fatigueScore);
  });
});

// ---------------------------------------------------------------------------
// fatigueSignal
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — fatigueSignal", () => {
  it("'normal' with no sets", () => {
    const result = computeFatigueBudget({ goal: "hypertrophy", sets: [] });
    expect(result.fatigueSignal).toBe("normal");
  });

  it("'high' when last RIR = 0 (single set)", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 0 })],
    });
    expect(result.fatigueSignal).toBe("high");
  });

  it("'high' when RIR drop ≥ 2 AND reps drop ≥ 2 simultaneously", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: 4, reps: 8, weight: 135 }),
        ws({ rir: 1, reps: 5, weight: 135 }), // RIR drop = 3, reps drop = 3
      ],
    });
    expect(result.fatigueSignal).toBe("high");
  });

  it("'rising' when RIR drops ≥ 2 but reps are stable", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: 4, reps: 8, weight: 135 }),
        ws({ rir: 2, reps: 8, weight: 135 }), // RIR drop = 2, no reps drop
      ],
    });
    expect(result.fatigueSignal).toBe("rising");
  });

  it("'normal' when RIR is steady", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 3 }), ws({ rir: 3 })],
    });
    expect(result.fatigueSignal).toBe("normal");
  });
});

// ---------------------------------------------------------------------------
// Missing RIR handling
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — missing RIR (A)", () => {
  it("A: treats missing RIR as +1 pt (neutral, not punitive)", () => {
    const withRir23 = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 2 })], // RIR 2–3 → +1 pt
    });
    const withMissing = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: undefined })], // should also be +1 pt
    });
    expect(withMissing.fatigueScore).toBe(1);
    expect(withMissing.fatigueScore).toBe(withRir23.fatigueScore);
  });

  it("A: missing RIR scores 1 pt (not 2 pt as before)", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: undefined })],
    });
    expect(result.fatigueScore).toBe(1);
  });

  it("adds coaching reason when RIR is missing", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: undefined })],
    });
    expect(result.reasons.some((r) => /RIR/i.test(r))).toBe(true);
  });

  it("A: missing RIR on prev set does NOT trigger overshoot trend (requires both RIRs)", () => {
    // Use last RIR = 0 (failure) so the per-set RIR drop is unambiguous.
    // Prev RIR defined as 2 (1 pt): overshoot = prevRir(2) - lastRir(0) = 2 ≥ 2, load up → +1
    const withDefinedPrev = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: 2, weight: 135, reps: 6 }), // 1 pt
        ws({ rir: 0, weight: 145, reps: 6 }), // 3 pts + overshoot (+1) = 5 total
      ],
    });
    // Prev RIR missing (1 pt neutral): overshoot add-on must NOT fire
    const withMissingPrev = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: undefined, weight: 135, reps: 6 }), // 1 pt (neutral)
        ws({ rir: 0, weight: 145, reps: 6 }),          // 3 pts, no overshoot = 4 total
      ],
    });
    // withDefinedPrev = 5 (1+3+1), withMissingPrev = 4 (1+3)
    expect(withMissingPrev.fatigueScore).toBeLessThan(withDefinedPrev.fatigueScore);
  });
});

// ---------------------------------------------------------------------------
// isHighFatigue flag (E: gates back-off suggestion)
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — isHighFatigue", () => {
  it("isHighFatigue = false when no sets", () => {
    const result = computeFatigueBudget({ goal: "strength", sets: [] });
    expect(result.isHighFatigue).toBe(false);
  });

  it("isHighFatigue = true when last RIR = 0 (failure)", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [ws({ rir: 0 })],
    });
    expect(result.isHighFatigue).toBe(true);
  });

  it("isHighFatigue = true when fatigueSignal = 'high' (RIR drop+reps drop)", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: 4, reps: 8, weight: 135 }),
        ws({ rir: 1, reps: 5, weight: 135 }), // high signal
      ],
    });
    expect(result.isHighFatigue).toBe(true);
  });

  it("isHighFatigue = false when fatigueSignal = 'rising' only", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: 4, reps: 8, weight: 135 }),
        ws({ rir: 2, reps: 8, weight: 135 }), // rising, no reps drop
      ],
    });
    expect(result.isHighFatigue).toBe(false);
  });

  it("isHighFatigue = true when repsDrop fired AND lastRIR <= 1", () => {
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets: [
        ws({ rir: 2, reps: 8, weight: 135 }),
        ws({ rir: 1, reps: 5, weight: 135 }), // reps_drop + RIR 1
      ],
    });
    // reps_drop add-on fires (reps dropped 3 at similar load)
    expect(result.isHighFatigue).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// lookbackWorkingSets parameter
// ---------------------------------------------------------------------------

describe("computeFatigueBudget — lookbackWorkingSets", () => {
  it("only scores the last N working sets", () => {
    // 5 sets: first 2 are hard (RIR 0), last 3 are easy (RIR 4)
    const sets = [
      ws({ rir: 0 }), ws({ rir: 0 }),
      ws({ rir: 4 }), ws({ rir: 4 }), ws({ rir: 4 }),
    ];
    const result = computeFatigueBudget({
      goal: "hypertrophy",
      sets,
      lookbackWorkingSets: 3,
    });
    // Only last 3 scored: RIR 4+4+4 = 0 pts
    expect(result.fatigueScore).toBe(0);
    expect(result.isCapped).toBe(false);
  });

  it("ignores warmup and backoff sets when counting", () => {
    const sets = [
      { setType: "warmup" as const, weight: 95, reps: 8, rir: 0 },
      ws({ rir: 2 }),
      { setType: "backoff" as const, weight: 115, reps: 8, rir: 0 },
    ];
    const result = computeFatigueBudget({ goal: "hypertrophy", sets });
    // Only the 1 working set scored: RIR 2 → 1 pt
    expect(result.fatigueScore).toBe(1);
  });
});
