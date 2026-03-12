import { getClampedWorkingRepRange } from "../repClamp";

describe("getClampedWorkingRepRange — strength", () => {
  it("clamps to 5–8 when engine range extends below 5", () => {
    const result = getClampedWorkingRepRange({
      goal: "strength",
      engineRange: { min: 4, max: 8 },
    });
    expect(result).toMatchObject({ min: 5, max: 8, wasClamped: true });
  });

  it("clamps to 5–8 when engine range extends above 8", () => {
    const result = getClampedWorkingRepRange({
      goal: "strength",
      engineRange: { min: 5, max: 12 },
    });
    expect(result).toMatchObject({ min: 5, max: 8, wasClamped: true });
  });

  it("does NOT clamp when engine range is already within 5–8", () => {
    const result = getClampedWorkingRepRange({
      goal: "strength",
      engineRange: { min: 5, max: 7 },
    });
    expect(result.wasClamped).toBe(false);
    expect(result.min).toBe(5);
    expect(result.max).toBe(7);
  });

  it("includes coachLine when clamped", () => {
    const result = getClampedWorkingRepRange({
      goal: "strength",
      engineRange: { min: 4, max: 8 },
    });
    expect(result.coachLine).toMatch(/5.8 reps/i);
  });
});

describe("getClampedWorkingRepRange — general", () => {
  it("clamps general to 6–20 when engine range extends below 6", () => {
    const result = getClampedWorkingRepRange({
      goal: "general",
      engineRange: { min: 4, max: 8 },
    });
    expect(result).toMatchObject({ min: 6, max: 20, wasClamped: true });
  });

  it("does NOT clamp general when already within 6–20", () => {
    const result = getClampedWorkingRepRange({
      goal: "general",
      engineRange: { min: 8, max: 15 },
    });
    expect(result.wasClamped).toBe(false);
    expect(result.min).toBe(8);
    expect(result.max).toBe(15);
  });

  it("includes 6–20 coachLine when clamped", () => {
    const result = getClampedWorkingRepRange({
      goal: "general",
      engineRange: { min: 4, max: 8 },
    });
    expect(result.coachLine).toMatch(/6.20 reps/i);
  });
});

describe("getClampedWorkingRepRange — hypertrophy (clamp: 6–12)", () => {
  it("clamps to 6–12 when engine range extends below 6", () => {
    const result = getClampedWorkingRepRange({
      goal: "hypertrophy",
      engineRange: { min: 4, max: 8 },
    });
    expect(result).toMatchObject({ min: 6, max: 12, wasClamped: true });
  });

  it("clamps to 6–12 when engine range extends above 12", () => {
    const result = getClampedWorkingRepRange({
      goal: "hypertrophy",
      engineRange: { min: 8, max: 15 },
    });
    expect(result).toMatchObject({ min: 6, max: 12, wasClamped: true });
  });

  it("does NOT clamp when engine range is already within 6–12", () => {
    const result = getClampedWorkingRepRange({
      goal: "hypertrophy",
      engineRange: { min: 7, max: 12 },
    });
    expect(result.wasClamped).toBe(false);
    expect(result.min).toBe(7);
    expect(result.max).toBe(12);
  });

  it("does NOT clamp {6,12} (exactly at boundary)", () => {
    const result = getClampedWorkingRepRange({
      goal: "hypertrophy",
      engineRange: { min: 6, max: 12 },
    });
    expect(result.wasClamped).toBe(false);
  });

  it("includes 6–12 coachLine when clamped", () => {
    const result = getClampedWorkingRepRange({
      goal: "hypertrophy",
      engineRange: { min: 4, max: 8 },
    });
    expect(result.coachLine).toMatch(/6.12 reps/i);
  });
});

describe("getClampedWorkingRepRange — fallback", () => {
  it("uses fallback when no engineRange supplied (within hypertrophy 6–12)", () => {
    const result = getClampedWorkingRepRange({
      goal: "hypertrophy",
      fallback: { min: 6, max: 12 },
    });
    expect(result.min).toBe(6);
    expect(result.max).toBe(12);
    expect(result.wasClamped).toBe(false);
  });

  it("default {6,12} not clamped for hypertrophy (exactly at boundary)", () => {
    const result = getClampedWorkingRepRange({ goal: "hypertrophy" });
    expect(result.min).toBe(6);
    expect(result.max).toBe(12);
    expect(result.wasClamped).toBe(false);
  });

  it("default {6,12} not clamped for general (within 6–20)", () => {
    const result = getClampedWorkingRepRange({ goal: "general" });
    expect(result.min).toBe(6);
    expect(result.max).toBe(12);
    expect(result.wasClamped).toBe(false);
  });
});
