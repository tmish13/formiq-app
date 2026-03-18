/**
 * Tests for the pure framing-readiness logic.
 * No browser APIs, no React, no TFJS — pure function calls only.
 */
import {
  evaluateFramingReadiness,
  isVisible,
  KP,
  VISIBILITY_THRESHOLD,
  MIN_VERTICAL_SPAN,
  Keypoint,
} from '../poseReadiness';

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Build a 17-element keypoint array with all landmarks invisible by default. */
function blankKeypoints(): Keypoint[] {
  return Array.from({ length: 17 }, () => ({ score: 0, y: 0, x: 0 }));
}

/** Produce a keypoint with a given score and y position. */
function kp(score: number, y: number): Keypoint {
  return { score, y, x: 0 };
}

/**
 * Build a realistic "full-body standing" pose within a 480px-tall frame.
 * Head ≈ y=48, hips ≈ y=288, knees ≈ y=360, ankles ≈ y=432.
 * Vertical span ≈ (432-48)/480 = 0.80 → well above MIN_VERTICAL_SPAN.
 */
function fullBodyKeypoints(): Keypoint[] {
  const pts = blankKeypoints();
  // Head
  pts[KP.NOSE] = kp(0.9, 48);
  pts[KP.LEFT_EYE] = kp(0.85, 42);
  pts[KP.RIGHT_EYE] = kp(0.85, 42);
  // Shoulders
  pts[KP.LEFT_SHOULDER] = kp(0.88, 120);
  pts[KP.RIGHT_SHOULDER] = kp(0.88, 120);
  // Hips
  pts[KP.LEFT_HIP] = kp(0.85, 288);
  pts[KP.RIGHT_HIP] = kp(0.85, 288);
  // Knees
  pts[KP.LEFT_KNEE] = kp(0.82, 360);
  pts[KP.RIGHT_KNEE] = kp(0.82, 360);
  // Ankles
  pts[KP.LEFT_ANKLE] = kp(0.78, 432);
  pts[KP.RIGHT_ANKLE] = kp(0.78, 432);
  return pts;
}

// ── isVisible ────────────────────────────────────────────────────────────────

describe('isVisible', () => {
  it('returns true when score >= threshold', () => {
    expect(isVisible(kp(VISIBILITY_THRESHOLD, 0))).toBe(true);
    expect(isVisible(kp(0.99, 0))).toBe(true);
  });

  it('returns false when score < threshold', () => {
    expect(isVisible(kp(VISIBILITY_THRESHOLD - 0.01, 0))).toBe(false);
    expect(isVisible(kp(0, 0))).toBe(false);
  });

  it('returns false for undefined keypoint', () => {
    expect(isVisible(undefined)).toBe(false);
  });

  it('returns false when score is undefined', () => {
    expect(isVisible({ y: 0, x: 0 })).toBe(false);
  });
});

// ── evaluateFramingReadiness — should return TRUE ────────────────────────────

describe('evaluateFramingReadiness — ready cases', () => {
  it('accepts a full-body pose in a 480px frame', () => {
    expect(evaluateFramingReadiness(fullBodyKeypoints(), 480)).toBe(true);
  });

  it('accepts a pose where only one shoulder is visible', () => {
    const pts = fullBodyKeypoints();
    pts[KP.RIGHT_SHOULDER] = kp(0, 0); // hide right shoulder
    expect(evaluateFramingReadiness(pts, 480)).toBe(true);
  });

  it('accepts a pose where only one knee/ankle is visible', () => {
    const pts = fullBodyKeypoints();
    pts[KP.RIGHT_KNEE] = kp(0, 0);
    pts[KP.RIGHT_ANKLE] = kp(0, 0);
    expect(evaluateFramingReadiness(pts, 480)).toBe(true);
  });

  it('accepts a pose with ankles visible but nose hidden', () => {
    const pts = fullBodyKeypoints();
    pts[KP.NOSE] = kp(0, 0);
    // Shoulders still present → hasShoulder = true
    expect(evaluateFramingReadiness(pts, 480)).toBe(true);
  });

  it('returns true exactly at MIN_VERTICAL_SPAN boundary', () => {
    const pts = fullBodyKeypoints();
    const frameH = 480;
    // Place head at 0, knees/ankles at MIN_VERTICAL_SPAN * frameH
    pts[KP.NOSE] = kp(0.9, 0);
    const bottomY = MIN_VERTICAL_SPAN * frameH;
    pts[KP.LEFT_KNEE] = kp(0.85, bottomY);
    pts[KP.RIGHT_KNEE] = kp(0, 0); // hidden
    pts[KP.LEFT_ANKLE] = kp(0, 0);
    pts[KP.RIGHT_ANKLE] = kp(0, 0);
    expect(evaluateFramingReadiness(pts, frameH)).toBe(true);
  });
});

// ── evaluateFramingReadiness — should return FALSE ───────────────────────────

describe('evaluateFramingReadiness — not-ready cases', () => {
  it('rejects an empty frame (all scores 0)', () => {
    expect(evaluateFramingReadiness(blankKeypoints(), 480)).toBe(false);
  });

  it('rejects face-only framing (no shoulders, hips, or knees)', () => {
    const pts = blankKeypoints();
    pts[KP.NOSE] = kp(0.95, 48);
    pts[KP.LEFT_EYE] = kp(0.9, 42);
    pts[KP.RIGHT_EYE] = kp(0.9, 42);
    expect(evaluateFramingReadiness(pts, 480)).toBe(false);
  });

  it('rejects upper-body-only (head + shoulders + hips, but no knees)', () => {
    const pts = blankKeypoints();
    pts[KP.NOSE] = kp(0.9, 48);
    pts[KP.LEFT_SHOULDER] = kp(0.88, 120);
    pts[KP.RIGHT_SHOULDER] = kp(0.88, 120);
    pts[KP.LEFT_HIP] = kp(0.85, 288);
    pts[KP.RIGHT_HIP] = kp(0.85, 288);
    // No knee/ankle landmarks
    expect(evaluateFramingReadiness(pts, 480)).toBe(false);
  });

  it('rejects a pose missing hips (legs but no hips)', () => {
    const pts = fullBodyKeypoints();
    pts[KP.LEFT_HIP] = kp(0, 0);
    pts[KP.RIGHT_HIP] = kp(0, 0);
    expect(evaluateFramingReadiness(pts, 480)).toBe(false);
  });

  it('rejects a pose where vertical span is below MIN_VERTICAL_SPAN', () => {
    const pts = blankKeypoints();
    const frameH = 480;
    // Head and knee both crammed into the top 30% of the frame
    pts[KP.NOSE] = kp(0.9, 50);
    pts[KP.LEFT_SHOULDER] = kp(0.9, 80);
    pts[KP.LEFT_HIP] = kp(0.85, 100);
    pts[KP.LEFT_KNEE] = kp(0.85, 120); // span = (120-50)/480 ≈ 0.15 < MIN_VERTICAL_SPAN
    expect(evaluateFramingReadiness(pts, frameH)).toBe(false);
  });

  it('rejects empty keypoints array', () => {
    expect(evaluateFramingReadiness([], 480)).toBe(false);
  });

  it('rejects keypoints array shorter than 17', () => {
    expect(evaluateFramingReadiness(blankKeypoints().slice(0, 10), 480)).toBe(false);
  });

  it('rejects zero frameHeight to avoid division errors', () => {
    expect(evaluateFramingReadiness(fullBodyKeypoints(), 0)).toBe(false);
  });

  it('rejects a frame where knees are visible but vertical span is insufficient', () => {
    const pts = blankKeypoints();
    const frameH = 480;
    // All landmarks clustered in the center — tight vertical span
    pts[KP.NOSE] = kp(0.9, 200);
    pts[KP.LEFT_SHOULDER] = kp(0.9, 220);
    pts[KP.LEFT_HIP] = kp(0.85, 240);
    pts[KP.LEFT_KNEE] = kp(0.85, 260); // span = 60/480 = 0.125 < 0.45
    expect(evaluateFramingReadiness(pts, frameH)).toBe(false);
  });
});
