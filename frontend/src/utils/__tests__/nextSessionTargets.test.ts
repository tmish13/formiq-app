import { computeNextSessionTarget } from "../nextSessionTargets";
import type { SetForTarget } from "../nextSessionTargets";

const CLAMP_STRENGTH    = { min: 5, max: 8 };
const CLAMP_HYPERTROPHY = { min: 6, max: 12 };
const CLAMP_GENERAL     = { min: 6, max: 20 };

// Helper to build a working set
function working(weightLb: number, reps: number, rir?: number): SetForTarget {
  return { setType: "working", weightLb, reps, rir };
}
function warmup(weightLb: number, reps: number): SetForTarget {
  return { setType: "warmup", weightLb, reps };
}
function backoff(weightLb: number, reps: number, rir?: number): SetForTarget {
  return { setType: "backoff", weightLb, reps, rir };
}

// ---------------------------------------------------------------------------
// FIX 2 — set-type filtering
// ---------------------------------------------------------------------------

describe("computeNextSessionTarget — set-type filtering (FIX 2)", () => {
  it("returns null when sets array is empty", () => {
    expect(
      computeNextSessionTarget({ goal: "strength", sets: [], incrementLb: 5, repClampRange: CLAMP_STRENGTH }),
    ).toBeNull();
  });

  it("returns null when only warmup sets exist", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      sets: [warmup(95, 8), warmup(115, 5)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    expect(result).toBeNull();
  });

  it("returns null when only backoff sets exist", () => {
    const result = computeNextSessionTarget({
      goal: "hypertrophy",
      sets: [backoff(100, 12, 4)],
      incrementLb: 5,
      repClampRange: CLAMP_HYPERTROPHY,
    });
    expect(result).toBeNull();
  });

  it("ignores warmup/backoff; uses working set for weight decision", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      // warmup at 200 lb should NOT drive a 205 lb target — only the working set counts
      sets: [warmup(200, 5), working(135, 5, 3), backoff(115, 8, 4)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    expect(result).not.toBeNull();
    // RIR 3 on working set (135 lb) → increase to 140, not 205
    expect(result!.targetWeightLb).toBe(140);
  });
});

// ---------------------------------------------------------------------------
// FIX 2 — best-set selection (highest weight → highest reps)
// ---------------------------------------------------------------------------

describe("computeNextSessionTarget — best-set selection (FIX 2)", () => {
  it("picks heaviest working set when weights differ", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      sets: [working(135, 5, 2), working(145, 5, 1), working(125, 8, 3)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    // Best = 145 lb (heaviest), RIR 1 → hold
    expect(result!.targetWeightLb).toBe(145);
    expect(result!.rationale).toMatch(/hold/i);
  });

  it("tiebreaks by highest reps when weights are equal", () => {
    const result = computeNextSessionTarget({
      goal: "hypertrophy",
      sets: [working(100, 8, 3), working(100, 12, 2), working(100, 6, 4)],
      incrementLb: 5,
      repClampRange: CLAMP_HYPERTROPHY,
    });
    // Best = 100 lb × 12 reps (most reps), RIR 2 → hold
    expect(result!.targetWeightLb).toBe(100);
    expect(result!.rationale).toMatch(/hold/i);
  });
});

// ---------------------------------------------------------------------------
// Weight decision rules
// ---------------------------------------------------------------------------

describe("computeNextSessionTarget — weight decisions", () => {
  it("RIR ≥ 3 → increases weight by incrementLb", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      sets: [working(135, 5, 4)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    expect(result!.targetWeightLb).toBe(140);
    expect(result!.rationale).toMatch(/increase/i);
  });

  it("RIR exactly 3 → increases weight", () => {
    const result = computeNextSessionTarget({
      goal: "hypertrophy",
      sets: [working(100, 8, 3)],
      incrementLb: 10,
      repClampRange: CLAMP_HYPERTROPHY,
    });
    expect(result!.targetWeightLb).toBe(110);
  });

  it("RIR 2 → holds weight", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      sets: [working(135, 5, 2)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    expect(result!.targetWeightLb).toBe(135);
    expect(result!.rationale).toMatch(/hold/i);
  });

  it("RIR 1 → holds weight", () => {
    const result = computeNextSessionTarget({
      goal: "general",
      sets: [working(80, 10, 1)],
      incrementLb: 5,
      repClampRange: CLAMP_GENERAL,
    });
    expect(result!.targetWeightLb).toBe(80);
  });

  it("RIR 0 → reduces weight by incrementLb", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      sets: [working(135, 5, 0)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    expect(result!.targetWeightLb).toBe(130);
    expect(result!.rationale).toMatch(/reduce/i);
  });

  it("RIR 0 + weight at 0 → stays at 0 (never negative)", () => {
    const result = computeNextSessionTarget({
      goal: "general",
      sets: [working(0, 10, 0)],
      incrementLb: 5,
      repClampRange: CLAMP_GENERAL,
    });
    expect(result!.targetWeightLb).toBe(0);
  });

  it("RIR undefined → holds weight and rationale mentions logging RIR", () => {
    const result = computeNextSessionTarget({
      goal: "hypertrophy",
      sets: [working(120, 8)], // no rir field
      incrementLb: 5,
      repClampRange: CLAMP_HYPERTROPHY,
    });
    expect(result!.targetWeightLb).toBe(120);
    expect(result!.rationale).toMatch(/log RIR/i);
  });
});

// ---------------------------------------------------------------------------
// Bodyweight
// ---------------------------------------------------------------------------

describe("computeNextSessionTarget — bodyweight", () => {
  it("bodyweight (weight=0, increment=0) stays at 0 regardless of RIR", () => {
    const result = computeNextSessionTarget({
      goal: "general",
      sets: [working(0, 12, 4)],
      incrementLb: 0,
      repClampRange: CLAMP_GENERAL,
    });
    expect(result!.targetWeightLb).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Output fields
// ---------------------------------------------------------------------------

describe("computeNextSessionTarget — output fields", () => {
  it("passes repClampRange through to targetRepsRange", () => {
    const result = computeNextSessionTarget({
      goal: "hypertrophy",
      sets: [working(100, 8, 2)],
      incrementLb: 5,
      repClampRange: { min: 6, max: 12 },
    });
    expect(result!.targetRepsRange).toEqual({ min: 6, max: 12 });
  });

  it("targetRir is 2 for strength", () => {
    const result = computeNextSessionTarget({
      goal: "strength",
      sets: [working(200, 5, 2)],
      incrementLb: 5,
      repClampRange: CLAMP_STRENGTH,
    });
    expect(result!.targetRir).toBe(2);
  });

  it("targetRir is 2 for hypertrophy", () => {
    const result = computeNextSessionTarget({
      goal: "hypertrophy",
      sets: [working(100, 8, 2)],
      incrementLb: 5,
      repClampRange: CLAMP_HYPERTROPHY,
    });
    expect(result!.targetRir).toBe(2);
  });

  it("targetRir is 2 for general", () => {
    const result = computeNextSessionTarget({
      goal: "general",
      sets: [working(100, 12, 2)],
      incrementLb: 5,
      repClampRange: CLAMP_GENERAL,
    });
    expect(result!.targetRir).toBe(2);
  });
});
