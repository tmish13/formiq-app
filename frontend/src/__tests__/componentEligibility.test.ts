import { getCaptureQualitySummary, VISIBILITY_TRUSTED, VISIBILITY_PARTIAL } from '../utils/componentEligibility';

describe('getCaptureQualitySummary', () => {
  it('all components >= 0.7 → good, empty tip', () => {
    const result = getCaptureQualitySummary({
      trunk_control: 0.85,
      knee_stability: 0.90,
      hip_drive: 0.75,
      forward_lean: 0.72,
    });
    expect(result.level).toBe('good');
    expect(result.tip).toBe('');
  });

  it('one component at 0.55 (partial range 0.4–0.7) → partial, tip mentions re-record', () => {
    const result = getCaptureQualitySummary({
      trunk_control: 0.85,
      knee_stability: 0.55,
      hip_drive: 0.80,
      forward_lean: 0.78,
    });
    expect(result.level).toBe('partial');
    expect(result.tip).toContain('Re-record');
  });

  it('one component at 0.3 (< 0.4) → poor, tip mentions missing scores', () => {
    const result = getCaptureQualitySummary({
      trunk_control: 0.85,
      knee_stability: 0.3,
      hip_drive: 0.80,
      forward_lean: 0.78,
    });
    expect(result.level).toBe('poor');
    expect(result.tip).toContain('missing');
  });

  it('undefined input → good safe default', () => {
    const result = getCaptureQualitySummary(undefined);
    expect(result.level).toBe('good');
    expect(result.tip).toBe('');
  });

  it('all components exactly at 0.4 (boundary of partial) → partial', () => {
    // 0.4 is >= VISIBILITY_PARTIAL so NOT poor, but < VISIBILITY_TRUSTED so partial
    const result = getCaptureQualitySummary({
      trunk_control: VISIBILITY_PARTIAL,
      knee_stability: VISIBILITY_PARTIAL,
      hip_drive: VISIBILITY_PARTIAL,
      forward_lean: VISIBILITY_PARTIAL,
    });
    expect(result.level).toBe('partial');
  });
});
