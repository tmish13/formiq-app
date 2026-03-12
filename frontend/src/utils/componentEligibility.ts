export const VISIBILITY_TRUSTED = 0.7;  // matches backend
export const VISIBILITY_PARTIAL = 0.4;  // matches backend

export type CaptureQualityLevel = 'good' | 'partial' | 'poor';

export interface CaptureQualitySummary {
  level: CaptureQualityLevel;
  tip: string;
}

/**
 * Derives overall capture quality from component_visibility dict.
 * 'good'    — all components >= 0.7: don't show any warning (no UI noise)
 * 'partial' — any component 0.4–0.7: show re-record tip
 * 'poor'    — any component < 0.4: score already null from backend; show missing data warning
 * Undefined/empty input → 'good' (safe default, no restriction)
 */
export function getCaptureQualitySummary(
  cv: Record<string, number> | null | undefined,
): CaptureQualitySummary {
  if (!cv || Object.keys(cv).length === 0) {
    return { level: 'good', tip: '' };
  }
  const values = Object.values(cv);
  if (values.some(v => v < VISIBILITY_PARTIAL)) {
    return {
      level: 'poor',
      tip: 'Ensure your full body is in frame and well-lit. Some component scores may be missing.',
    };
  }
  if (values.some(v => v < VISIBILITY_TRUSTED)) {
    return {
      level: 'partial',
      tip: 'Re-record with your full body clearly visible for the most accurate results.',
    };
  }
  return { level: 'good', tip: '' };
}
