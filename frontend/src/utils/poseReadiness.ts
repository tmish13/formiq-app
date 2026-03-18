/**
 * poseReadiness.ts
 *
 * Pure functions for evaluating whether a camera frame shows a person
 * positioned well enough for squat form analysis.
 *
 * All functions are side-effect-free so they can be unit tested without
 * a browser or ML runtime.
 */

// MoveNet / BlazePose share the same 17-keypoint layout.
export const KP = {
  NOSE: 0,
  LEFT_EYE: 1,
  RIGHT_EYE: 2,
  LEFT_EAR: 3,
  RIGHT_EAR: 4,
  LEFT_SHOULDER: 5,
  RIGHT_SHOULDER: 6,
  LEFT_ELBOW: 7,
  RIGHT_ELBOW: 8,
  LEFT_WRIST: 9,
  RIGHT_WRIST: 10,
  LEFT_HIP: 11,
  RIGHT_HIP: 12,
  LEFT_KNEE: 13,
  RIGHT_KNEE: 14,
  LEFT_ANKLE: 15,
  RIGHT_ANKLE: 16,
} as const;

export interface Keypoint {
  /** 0–1 confidence score */
  score?: number;
  /** y position in pixels (top = 0) */
  y: number;
  /** x position in pixels (left = 0) */
  x: number;
}

/** Minimum per-keypoint confidence to count as "visible". */
export const VISIBILITY_THRESHOLD = 0.3;

/** Minimum fraction of frame height that the body must span (head → knee). */
export const MIN_VERTICAL_SPAN = 0.45;

/**
 * Returns true when a keypoint is confidently detected.
 */
export function isVisible(kp: Keypoint | undefined): boolean {
  return (kp?.score ?? 0) >= VISIBILITY_THRESHOLD;
}

/**
 * Core readiness check — pure function, zero side-effects.
 *
 * Readiness requires ALL of:
 *   • Head: nose OR at least one shoulder
 *   • Torso: at least one hip
 *   • Legs: at least one knee
 *   • Vertical span head→knee ≥ MIN_VERTICAL_SPAN of frame height
 *
 * This rejects:
 *   • Empty frame (no keypoints above threshold)
 *   • Face-only shot (no shoulder / hip / knee)
 *   • Upper-body-only (no knee)
 *   • Severely cropped body (vertical span too small)
 */
export function evaluateFramingReadiness(
  keypoints: Keypoint[],
  frameHeight: number,
): boolean {
  if (!keypoints || keypoints.length < 17 || frameHeight <= 0) return false;

  const kp = keypoints;

  // ── 1. Landmark presence checks ─────────────────────────────────────────
  const hasHead =
    isVisible(kp[KP.NOSE]) ||
    isVisible(kp[KP.LEFT_EYE]) ||
    isVisible(kp[KP.RIGHT_EYE]);

  const hasShoulder =
    isVisible(kp[KP.LEFT_SHOULDER]) || isVisible(kp[KP.RIGHT_SHOULDER]);

  const hasHip =
    isVisible(kp[KP.LEFT_HIP]) || isVisible(kp[KP.RIGHT_HIP]);

  const hasKnee =
    isVisible(kp[KP.LEFT_KNEE]) || isVisible(kp[KP.RIGHT_KNEE]);

  // Need head or shoulder (at least upper body anchor), plus hips and knees
  if (!(hasHead || hasShoulder) || !hasHip || !hasKnee) return false;

  // ── 2. Vertical span check ───────────────────────────────────────────────
  // Find the topmost visible anchor (head/shoulder)
  const topCandidates = [
    KP.NOSE, KP.LEFT_EYE, KP.RIGHT_EYE, KP.LEFT_SHOULDER, KP.RIGHT_SHOULDER,
  ].filter((i) => isVisible(kp[i])).map((i) => kp[i].y);

  // Find the bottommost visible leg landmark (prefer ankle, fall back to knee)
  const bottomCandidates = [
    KP.LEFT_ANKLE, KP.RIGHT_ANKLE, KP.LEFT_KNEE, KP.RIGHT_KNEE,
  ].filter((i) => isVisible(kp[i])).map((i) => kp[i].y);

  if (topCandidates.length === 0 || bottomCandidates.length === 0) return false;

  const topY = Math.min(...topCandidates);
  const bottomY = Math.max(...bottomCandidates);
  const verticalSpan = (bottomY - topY) / frameHeight;

  return verticalSpan >= MIN_VERTICAL_SPAN;
}
