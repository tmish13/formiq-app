/**
 * Unit tests for storage.ts — focused on FIX 3–5 behaviors.
 * Uses a real jsdom localStorage (provided by Jest + jsdom environment).
 */

// makeId must be mocked before importing storage (storage uses require("./id") lazily)
jest.mock("../id", () => {
  let counter = 0;
  return { makeId: () => `mock-id-${++counter}` };
});

import {
  saveNextTarget,
  getNextTarget,
  findOrCreateGym,
  listGyms,
  getLastEquipmentForExercise,
  setLastEquipmentForExercise,
  keyPart,
  getRecentEquipmentProfileIds,
  pushRecentEquipmentProfileId,
} from "../storage";
import type { NextSessionTarget } from "../../../utils/nextSessionTargets";

const SAMPLE_TARGET: NextSessionTarget = {
  targetWeightLb: 140,
  targetRepsRange: { min: 5, max: 8 },
  targetRir: 2,
  rationale: "RIR ≥ 3 → increase load",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function clearStorage() {
  localStorage.clear();
}

// ---------------------------------------------------------------------------
// FIX 3 — next-target key collision
// ---------------------------------------------------------------------------

describe("saveNextTarget / getNextTarget — gym-aware keys (FIX 3)", () => {
  beforeEach(clearStorage);

  it("retrieves a target saved without equipment for the matching gym", () => {
    saveNextTarget("barbell_back_squat", undefined, "gymA", SAMPLE_TARGET);
    const result = getNextTarget("barbell_back_squat", undefined, "gymA");
    expect(result).toEqual(SAMPLE_TARGET);
  });

  it("two gyms with no equipment do NOT share targets", () => {
    const targetA: NextSessionTarget = { ...SAMPLE_TARGET, targetWeightLb: 135 };
    const targetB: NextSessionTarget = { ...SAMPLE_TARGET, targetWeightLb: 155 };
    saveNextTarget("barbell_back_squat", undefined, "gymA", targetA);
    saveNextTarget("barbell_back_squat", undefined, "gymB", targetB);

    expect(getNextTarget("barbell_back_squat", undefined, "gymA")!.targetWeightLb).toBe(135);
    expect(getNextTarget("barbell_back_squat", undefined, "gymB")!.targetWeightLb).toBe(155);
  });

  it("with equipment ID: key is scoped to equipmentProfileId (gym not in key)", () => {
    saveNextTarget("barbell_back_squat", "eq-1", "gymA", SAMPLE_TARGET);
    // Same equipmentProfileId, different gym — same key (gym is implicit via equipment)
    const result = getNextTarget("barbell_back_squat", "eq-1", "gymB");
    expect(result).toEqual(SAMPLE_TARGET);
  });

  it("returns null when no target saved for that gym+exercise", () => {
    saveNextTarget("barbell_back_squat", undefined, "gymA", SAMPLE_TARGET);
    const result = getNextTarget("barbell_back_squat", undefined, "gymB");
    expect(result).toBeNull();
  });

  it("undefined gymId falls back to 'default' bucket", () => {
    saveNextTarget("deadlift", undefined, undefined, SAMPLE_TARGET);
    expect(getNextTarget("deadlift", undefined, undefined)).toEqual(SAMPLE_TARGET);
    // 'default' string explicitly should match
    expect(getNextTarget("deadlift", undefined, "default")).toEqual(SAMPLE_TARGET);
  });

  it("upserts: saving again for same key overwrites", () => {
    saveNextTarget("deadlift", undefined, "gymA", SAMPLE_TARGET);
    const updated = { ...SAMPLE_TARGET, targetWeightLb: 999 };
    saveNextTarget("deadlift", undefined, "gymA", updated);
    expect(getNextTarget("deadlift", undefined, "gymA")!.targetWeightLb).toBe(999);
  });
});

// ---------------------------------------------------------------------------
// FIX 4 — gym findOrCreate (trim/dedupe)
// ---------------------------------------------------------------------------

describe("findOrCreateGym (FIX 4)", () => {
  beforeEach(clearStorage);

  it("creates a new gym and returns it", () => {
    const gym = findOrCreateGym("Planet Fitness");
    expect(gym.name).toBe("Planet Fitness");
    expect(listGyms().some((g) => g.name === "Planet Fitness")).toBe(true);
  });

  it("trims whitespace from gym name", () => {
    const gym = findOrCreateGym("  My Gym  ");
    expect(gym.name).toBe("My Gym");
  });

  it("deduplicates case-insensitively — returns existing instead of creating new", () => {
    const first = findOrCreateGym("24 Hour Fitness");
    const second = findOrCreateGym(" 24 hour fitness "); // different casing + whitespace
    expect(second.id).toBe(first.id);
    // Only one gym with that name
    const gyms = listGyms().filter(
      (g) => g.name.toLowerCase().includes("24 hour"),
    );
    expect(gyms).toHaveLength(1);
  });

  it("returns default gym when name is empty string", () => {
    const gym = findOrCreateGym("");
    expect(gym.id).toBe("default");
  });

  it("returns default gym when name is only whitespace", () => {
    const gym = findOrCreateGym("   ");
    expect(gym.id).toBe("default");
  });

  it("same name, different case — second call returns same id (no duplicate)", () => {
    findOrCreateGym("Gold's Gym");
    findOrCreateGym("GOLD'S GYM");
    const gyms = listGyms().filter((g) =>
      g.name.toLowerCase().includes("gold"),
    );
    expect(gyms).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// FIX 5 — last-used equipment per (gym, exercise)
// ---------------------------------------------------------------------------

describe("getLastEquipmentForExercise / setLastEquipmentForExercise (FIX 5)", () => {
  beforeEach(clearStorage);

  it("returns null when nothing has been saved", () => {
    const result = getLastEquipmentForExercise({
      gymId: "gymA",
      exerciseId: "barbell_back_squat",
    });
    expect(result).toBeNull();
  });

  it("saves and retrieves last-used equipment for a gym+exercise", () => {
    setLastEquipmentForExercise({
      gymId: "gymA",
      exerciseId: "barbell_back_squat",
      equipmentProfileId: "eq-panatta",
    });
    expect(
      getLastEquipmentForExercise({ gymId: "gymA", exerciseId: "barbell_back_squat" }),
    ).toBe("eq-panatta");
  });

  it("two different gyms have independent last-equip records", () => {
    setLastEquipmentForExercise({ gymId: "gymA", exerciseId: "leg_press", equipmentProfileId: "eq-a" });
    setLastEquipmentForExercise({ gymId: "gymB", exerciseId: "leg_press", equipmentProfileId: "eq-b" });

    expect(getLastEquipmentForExercise({ gymId: "gymA", exerciseId: "leg_press" })).toBe("eq-a");
    expect(getLastEquipmentForExercise({ gymId: "gymB", exerciseId: "leg_press" })).toBe("eq-b");
  });

  it("overwriting last-equip for same gym+exercise replaces it", () => {
    setLastEquipmentForExercise({ gymId: "gymA", exerciseId: "deadlift", equipmentProfileId: "eq-old" });
    setLastEquipmentForExercise({ gymId: "gymA", exerciseId: "deadlift", equipmentProfileId: "eq-new" });
    expect(getLastEquipmentForExercise({ gymId: "gymA", exerciseId: "deadlift" })).toBe("eq-new");
  });

  it("undefined gymId uses 'default' bucket", () => {
    setLastEquipmentForExercise({ gymId: undefined, exerciseId: "bench_press", equipmentProfileId: "eq-x" });
    expect(getLastEquipmentForExercise({ gymId: undefined, exerciseId: "bench_press" })).toBe("eq-x");
    // Explicit "default" should also match
    expect(getLastEquipmentForExercise({ gymId: "default", exerciseId: "bench_press" })).toBe("eq-x");
  });
});

// ---------------------------------------------------------------------------
// FIX 1 — keyPart helper
// ---------------------------------------------------------------------------

describe("keyPart", () => {
  it("returns the value for a normal string", () => {
    expect(keyPart("gymA")).toBe("gymA");
  });

  it("trims surrounding whitespace", () => {
    expect(keyPart("  trimmed  ")).toBe("trimmed");
  });

  it("returns 'none' for undefined", () => {
    expect(keyPart(undefined)).toBe("none");
  });

  it("returns 'none' for null", () => {
    expect(keyPart(null)).toBe("none");
  });

  it("returns 'none' for empty string", () => {
    expect(keyPart("")).toBe("none");
  });

  it("returns 'none' for whitespace-only string", () => {
    expect(keyPart("   ")).toBe("none");
  });
});

// ---------------------------------------------------------------------------
// Phase 2 — getRecentEquipmentProfileIds / pushRecentEquipmentProfileId
// ---------------------------------------------------------------------------

describe("getRecentEquipmentProfileIds / pushRecentEquipmentProfileId", () => {
  beforeEach(clearStorage);

  it("returns [] when nothing has been saved", () => {
    expect(getRecentEquipmentProfileIds()).toEqual([]);
  });

  it("pushes a single id and retrieves it", () => {
    pushRecentEquipmentProfileId("eq-1");
    expect(getRecentEquipmentProfileIds()).toEqual(["eq-1"]);
  });

  it("prepends on each push — most-recent-first", () => {
    pushRecentEquipmentProfileId("eq-1");
    pushRecentEquipmentProfileId("eq-2");
    expect(getRecentEquipmentProfileIds()).toEqual(["eq-2", "eq-1"]);
  });

  it("deduplicates: pushing an existing id moves it to the front", () => {
    pushRecentEquipmentProfileId("eq-1");
    pushRecentEquipmentProfileId("eq-2");
    pushRecentEquipmentProfileId("eq-1"); // re-push eq-1 → should be at front, no duplicate
    expect(getRecentEquipmentProfileIds()).toEqual(["eq-1", "eq-2"]);
  });

  it("caps list at default limit of 3", () => {
    pushRecentEquipmentProfileId("eq-1");
    pushRecentEquipmentProfileId("eq-2");
    pushRecentEquipmentProfileId("eq-3");
    pushRecentEquipmentProfileId("eq-4"); // evicts eq-1
    expect(getRecentEquipmentProfileIds()).toEqual(["eq-4", "eq-3", "eq-2"]);
  });

  it("respects a custom limit parameter on read", () => {
    pushRecentEquipmentProfileId("eq-1");
    pushRecentEquipmentProfileId("eq-2");
    pushRecentEquipmentProfileId("eq-3");
    expect(getRecentEquipmentProfileIds(2)).toEqual(["eq-3", "eq-2"]);
  });

  it("push with same id repeatedly is idempotent (stays at front, no length growth)", () => {
    pushRecentEquipmentProfileId("eq-x");
    pushRecentEquipmentProfileId("eq-x");
    pushRecentEquipmentProfileId("eq-x");
    expect(getRecentEquipmentProfileIds()).toEqual(["eq-x"]);
  });
});
