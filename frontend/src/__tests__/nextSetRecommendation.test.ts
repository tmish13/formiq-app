/**
 * Unit tests for getNextSetRecommendation (features/training/progressionEngine.ts).
 * Pure logic — no DOM, no localStorage.
 */
import { getNextSetRecommendation } from "../features/training/progressionEngine";
import type {
  Exercise,
  EquipmentProfile,
  SetLog,
  Goal,
} from "../features/training/types";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SQUAT: Exercise = {
  id: "barbell_back_squat",
  name: "Back Squat",
  primaryMuscles: ["quadriceps", "glutes"],
  movementPattern: "squat",
  defaultLoadType: "barbell_plates",
  defaultIncrementLb: 5,
  defaultRepIntent: { min: 4, max: 8 },
};

const PULLUP: Exercise = {
  id: "pull_up",
  name: "Pull-Up",
  primaryMuscles: ["lats", "biceps"],
  movementPattern: "vertical_pull",
  defaultLoadType: "fixed",
  defaultIncrementLb: 0,
  defaultRepIntent: { min: 5, max: 12 },
};

function makeSet(overrides: Partial<SetLog> = {}): SetLog {
  return {
    id: "s1",
    sessionId: "sess1",
    exerciseId: "barbell_back_squat",
    setIndex: 0,
    setType: "working",
    weightLb: 135,
    reps: 5,
    rir: 2,
    createdAt: new Date().toISOString(),
    ...overrides,
  };
}

function makeSets(count: number, base: Partial<SetLog> = {}): SetLog[] {
  return Array.from({ length: count }, (_, i) =>
    makeSet({ id: `s${i}`, setIndex: i, ...base }),
  );
}

// ---------------------------------------------------------------------------
// Guard cases: no sets
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — no sets", () => {
  it("returns hold with starter weight when no sets logged", () => {
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.action).toBe("hold");
    expect(rec.reasons[0]).toMatch(/first working set/i);
  });

  it("starter weight is at least 45 lb for barbell exercises", () => {
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.nextWeightLb).toBeGreaterThanOrEqual(45);
  });

  it("starter weight is 0 for bodyweight exercise (increment=0)", () => {
    const rec = getNextSetRecommendation({
      goal: "general",
      exercise: PULLUP,
      equipment: null,
      recentSets: [],
    });
    expect(rec.nextWeightLb).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Guard: last working set has no RIR
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — missing RIR", () => {
  it("returns hold with 'add RIR' reason when last working set has no rir", () => {
    const sets = [makeSet({ rir: undefined })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("hold");
    expect(rec.reasons[0]).toMatch(/rir/i);
  });
});

// ---------------------------------------------------------------------------
// RIR ≥ 4 → increase
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — RIR ≥ 4 (increase)", () => {
  it("recommends increase when last working set rir = 4", () => {
    const sets = [makeSet({ rir: 4, weightLb: 100 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("increase");
    expect(rec.nextWeightLb).toBe(105); // 100 + 5 lb increment
  });

  it("increase weight uses equipment profile increment when provided", () => {
    const profile: EquipmentProfile = {
      id: "p1",
      chainId: "other",
      exerciseId: "barbell_back_squat",
      loadType: "machine_stack",
      incrementLb: 10,
    };
    const sets = [makeSet({ rir: 5, weightLb: 100 })];
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: profile,
      recentSets: sets,
    });
    expect(rec.action).toBe("increase");
    expect(rec.nextWeightLb).toBe(110); // 100 + 10 lb equipment increment
  });

  it("holds instead of increasing when fatigue is rising despite rir ≥ 4", () => {
    // Two sets at same weight, but rir dropped: 5 → 4
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 5, weightLb: 100 }),
      makeSet({ id: "s2", setIndex: 1, rir: 4, weightLb: 100 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("hold");
    expect(rec.reasons[0]).toMatch(/fatigue/i);
  });
});

// ---------------------------------------------------------------------------
// RIR 2–3 → hold
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — RIR 2-3 (hold)", () => {
  it("holds at rir = 2", () => {
    const sets = [makeSet({ rir: 2, weightLb: 135 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("hold");
    expect(rec.nextWeightLb).toBe(135);
  });

  it("holds at rir = 3", () => {
    const sets = [makeSet({ rir: 3, weightLb: 135 })];
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("hold");
  });
});

// ---------------------------------------------------------------------------
// RIR 1 — goal-dependent
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — RIR 1", () => {
  it("holds at rir = 1 for strength goal", () => {
    const sets = [makeSet({ rir: 1, weightLb: 185 })];
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("hold");
    expect(rec.reasons[0]).toMatch(/near-maximal|strength/i);
  });

  it("reduces at rir = 1 with rising fatigue for hypertrophy", () => {
    // Previous set at same weight had rir = 3, current is rir = 1 → fatigue rising
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 3, weightLb: 135 }),
      makeSet({ id: "s2", setIndex: 1, rir: 1, weightLb: 135 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("reduce");
    expect(rec.nextWeightLb).toBe(130); // 135 - 5
  });

  it("holds at rir = 1 without fatigue for hypertrophy", () => {
    const sets = [makeSet({ rir: 1, weightLb: 135 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("hold");
  });
});

// ---------------------------------------------------------------------------
// RIR ≤ 0 → reduce
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — RIR 0 (reduce)", () => {
  it("reduces by 1 step on single rir = 0 set", () => {
    const sets = [makeSet({ rir: 0, weightLb: 135 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("reduce");
    expect(rec.nextWeightLb).toBe(130); // 135 - 5
  });

  it("reduces by 2 steps on 2 consecutive rir = 0 sets", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 0, weightLb: 135 }),
      makeSet({ id: "s2", setIndex: 1, rir: 0, weightLb: 135 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.action).toBe("reduce");
    expect(rec.nextWeightLb).toBe(125); // 135 - 5*2
    expect(rec.reasons[0]).toMatch(/consecutive/i);
  });

  it("weight never goes below 0", () => {
    const sets = [makeSet({ rir: 0, weightLb: 5 })];
    const rec = getNextSetRecommendation({
      goal: "general",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.nextWeightLb).toBeGreaterThanOrEqual(0);
  });
});

// ---------------------------------------------------------------------------
// Rest time by goal
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — rest seconds by goal", () => {
  it("returns longer rest for strength vs hypertrophy", () => {
    const sets = [makeSet({ rir: 2 })];
    const recStrength = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    const recHyper = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(recStrength.restSeconds).toBeGreaterThan(recHyper.restSeconds!);
  });
});

// ---------------------------------------------------------------------------
// Rep range is always the exercise default
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — rep range", () => {
  it("always returns the exercise defaultRepIntent as nextRepsRange", () => {
    const sets = [makeSet({ rir: 4, weightLb: 100 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.nextRepsRange).toEqual(SQUAT.defaultRepIntent);
  });
});

// ---------------------------------------------------------------------------
// Form score advisory
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — form advisory", () => {
  it("appends form advisory when score drops ≥15 points across last 2 sets", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 4, weightLb: 100, formScore: 80 }),
      makeSet({ id: "s2", setIndex: 1, rir: 4, weightLb: 100, formScore: 60 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.reasons.some((r) => /form/i.test(r))).toBe(true);
  });

  it("does NOT add form advisory when form drop is < 15 points", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 2, weightLb: 100, formScore: 80 }),
      makeSet({ id: "s2", setIndex: 1, rir: 2, weightLb: 100, formScore: 75 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    // Reasons should not contain a form advisory
    expect(rec.reasons.every((r) => !/technique|form/i.test(r))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// New fields: setsCompleted, setsRecommended, exerciseStatus, fatigueSignal
// ---------------------------------------------------------------------------

describe("getNextSetRecommendation — setsCompleted and setsRecommended", () => {
  it("setsCompleted = 0 when no sets logged", () => {
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.setsCompleted).toBe(0);
  });

  it("setsCompleted counts only working sets (not warmups)", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, setType: "warmup" }),
      makeSet({ id: "s2", setIndex: 1, setType: "working", rir: 3 }),
      makeSet({ id: "s3", setIndex: 2, setType: "working", rir: 2 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.setsCompleted).toBe(2);
  });

  it("setsRecommended = 3 for strength goal", () => {
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.setsRecommended).toBe(3);
  });

  it("setsRecommended = 4 for hypertrophy goal", () => {
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.setsRecommended).toBe(4);
  });

  it("setsRecommended = 2 for general goal", () => {
    const rec = getNextSetRecommendation({
      goal: "general",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.setsRecommended).toBe(2);
  });
});

describe("getNextSetRecommendation — fatigueSignal", () => {
  it("fatigueSignal = 'normal' when no working sets", () => {
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.fatigueSignal).toBe("normal");
  });

  it("fatigueSignal = 'high' when last working set RIR = 0", () => {
    const sets = [makeSet({ rir: 0, weightLb: 135 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.fatigueSignal).toBe("high");
  });

  it("fatigueSignal = 'high' when RIR drops ≥3 points between consecutive sets", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 5, weightLb: 135 }),
      makeSet({ id: "s2", setIndex: 1, rir: 2, weightLb: 135 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.fatigueSignal).toBe("high");
  });

  it("fatigueSignal = 'rising' when RIR is decreasing at same weight (not high)", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 4, weightLb: 135 }),
      makeSet({ id: "s2", setIndex: 1, rir: 3, weightLb: 135 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.fatigueSignal).toBe("rising");
  });

  it("fatigueSignal = 'normal' when RIR is steady", () => {
    const sets = [
      makeSet({ id: "s1", setIndex: 0, rir: 3, weightLb: 135 }),
      makeSet({ id: "s2", setIndex: 1, rir: 3, weightLb: 135 }),
    ];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.fatigueSignal).toBe("normal");
  });
});

describe("getNextSetRecommendation — exerciseStatus", () => {
  it("exerciseStatus = 'continue' before any working sets", () => {
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: [],
    });
    expect(rec.exerciseStatus).toBe("continue");
  });

  it("exerciseStatus = 'finish' when setsCompleted >= setsRecommended (strength at 3 sets)", () => {
    const sets = makeSets(3, { rir: 2 });
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.exerciseStatus).toBe("finish");
  });

  it("exerciseStatus = 'finish' for strength after 2 sets at RIR ≤ 2", () => {
    const sets = makeSets(2, { rir: 2 });
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.exerciseStatus).toBe("finish");
  });

  it("exerciseStatus = 'optional' for strength after 2 sets at RIR = 3", () => {
    const sets = makeSets(2, { rir: 3 });
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.exerciseStatus).toBe("optional");
  });

  it("exerciseStatus = 'continue' for hypertrophy after 2 sets", () => {
    const sets = makeSets(2, { rir: 2 });
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.exerciseStatus).toBe("continue");
  });

  it("exerciseStatus = 'finish' for general after 2 sets at RIR ≤ 3", () => {
    const sets = makeSets(2, { rir: 2 });
    const rec = getNextSetRecommendation({
      goal: "general",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.exerciseStatus).toBe("finish");
  });
});

describe("getNextSetRecommendation — statusMessage", () => {
  it("statusMessage is defined when exerciseStatus = 'finish'", () => {
    const sets = makeSets(3, { rir: 2 });
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.statusMessage).toBeDefined();
    expect(typeof rec.statusMessage).toBe("string");
  });

  it("statusMessage is undefined during normal in-progress sets", () => {
    const sets = [makeSet({ rir: 3, weightLb: 135 })];
    const rec = getNextSetRecommendation({
      goal: "hypertrophy",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.statusMessage).toBeUndefined();
  });

  it("statusMessage mentions strength goal when exerciseStatus = 'finish' for strength", () => {
    const sets = makeSets(3, { rir: 2 });
    const rec = getNextSetRecommendation({
      goal: "strength",
      exercise: SQUAT,
      equipment: null,
      recentSets: sets,
    });
    expect(rec.statusMessage).toMatch(/strength/i);
  });
});
