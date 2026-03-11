/**
 * Technique skill level computation — pure, deterministic, zero side effects.
 *
 * Maps backend component score keys (named_scores from AnalyticsSession)
 * to a displayable technique skill profile.
 */

export interface TechniqueLevels {
  stability: number | null;   // from torsoStability
  kneeControl: number | null; // from kneeSymmetry
  depth: number | null;       // from bottomControl
  posture: number | null;     // from forwardLean
  overall: number | null;
  level: "Beginner" | "Developing" | "Intermediate" | "Advanced" | "Elite" | null;
}

const LEVELS: { min: number; label: NonNullable<TechniqueLevels["level"]> }[] = [
  { min: 92, label: "Elite" },
  { min: 85, label: "Advanced" },
  { min: 75, label: "Intermediate" },
  { min: 60, label: "Developing" },
  { min: 0,  label: "Beginner" },
];

/**
 * Maps a named_scores object from AnalyticsSession to technique levels.
 * Returns null fields when data is unavailable.
 */
export function calculateTechniqueLevels(
  namedScores: Record<string, number | null> | null | undefined,
): TechniqueLevels {
  if (!namedScores) {
    return {
      stability: null,
      kneeControl: null,
      depth: null,
      posture: null,
      overall: null,
      level: null,
    };
  }

  const stability  = namedScores["torsoStability"] ?? null;
  const kneeControl = namedScores["kneeSymmetry"]  ?? null;
  const depth      = namedScores["bottomControl"]  ?? null;
  const posture    = namedScores["forwardLean"]    ?? null;

  const values = [stability, kneeControl, depth, posture].filter(
    (v): v is number => v !== null,
  );
  const overall = values.length
    ? Math.round(values.reduce((a, b) => a + b, 0) / values.length)
    : null;

  const level =
    overall !== null
      ? LEVELS.find((l) => overall >= l.min)?.label ?? "Beginner"
      : null;

  return { stability, kneeControl, depth, posture, overall, level };
}

/**
 * Averages named_scores across up to 3 recent sessions with data.
 * Returns a merged named_scores object suitable for calculateTechniqueLevels().
 */
export function averageNamedScores(
  sessions: Array<{ named_scores: Record<string, number | null> | null }>,
): Record<string, number | null> | null {
  const withScores = sessions.filter((s) => s.named_scores != null);
  if (!withScores.length) return null;

  const recent = withScores.slice(0, 3);
  const allKeys = Array.from(
    new Set(recent.flatMap((s) => Object.keys(s.named_scores!))),
  );

  const avg: Record<string, number | null> = {};
  for (const key of allKeys) {
    const vals = recent
      .map((s) => s.named_scores?.[key])
      .filter((v): v is number => typeof v === "number");
    avg[key] = vals.length
      ? Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)
      : null;
  }
  return avg;
}
