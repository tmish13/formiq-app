/**
 * Pure unit tests for getExercisesForEquipmentType — no mocks needed.
 * Verifies that the catalog correctly filters exercises by equipment type.
 */
import { EXERCISES, getExercisesForEquipmentType } from "../catalog";

test('cable_stack: includes cable_curl, excludes barbell_back_squat', () => {
  const result = getExercisesForEquipmentType("cable_stack");
  const ids = result.map((e) => e.id);
  expect(ids).toContain("cable_curl");
  expect(ids).not.toContain("barbell_back_squat");
});

test('smith: includes smith_bench_press, excludes seated_cable_row', () => {
  const result = getExercisesForEquipmentType("smith");
  const ids = result.map((e) => e.id);
  expect(ids).toContain("smith_bench_press");
  expect(ids).not.toContain("seated_cable_row");
});

test('bodyweight: includes pull_up and chin_up, excludes hack_squat', () => {
  const result = getExercisesForEquipmentType("bodyweight");
  const ids = result.map((e) => e.id);
  expect(ids).toContain("pull_up");
  expect(ids).toContain("chin_up");
  expect(ids).not.toContain("hack_squat");
});

test('machine_plate_loaded: includes hack_squat, excludes barbell_back_squat', () => {
  const result = getExercisesForEquipmentType("machine_plate_loaded");
  const ids = result.map((e) => e.id);
  expect(ids).toContain("hack_squat");
  expect(ids).not.toContain("barbell_back_squat");
});

test('other: returns all exercises (63 total)', () => {
  const result = getExercisesForEquipmentType("other");
  expect(result).toHaveLength(EXERCISES.length);
  expect(result).toHaveLength(63);
});

describe('machine_selectorized (pin-loaded)', () => {
  it('includes all new pin-loaded exercises', () => {
    const results = getExercisesForEquipmentType("machine_selectorized");
    ["adductor_machine", "abductor_machine", "machine_curl",
     "machine_tricep_extension", "assisted_pull_up_dip"].forEach(id =>
      expect(results.some(e => e.id === id)).toBe(true)
    );
  });
  it('excludes barbell-only and cable-only exercises', () => {
    const results = getExercisesForEquipmentType("machine_selectorized");
    expect(results.some(e => e.id === "barbell_back_squat")).toBe(false);
    expect(results.some(e => e.id === "deadlift")).toBe(false);
    expect(results.some(e => e.id === "cable_curl")).toBe(false);
  });
});
