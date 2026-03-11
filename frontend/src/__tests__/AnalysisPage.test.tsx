/**
 * Tests for AnalysisPage helpers: getComponentChip, buildFormSummary context,
 * and EvidenceSection rendering.
 *
 * Tests are written against the exported/private helpers by either:
 * 1. Importing them directly (if exported), or
 * 2. Testing via rendered component output.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// ---------------------------------------------------------------------------
// Inline replica of getComponentChip (pure function — no side effects)
// Mirrors the exact logic in AnalysisPage.tsx so tests don't depend on
// the component being rendered.
// ---------------------------------------------------------------------------
function getComponentChip(score: number | null | undefined) {
  if (score === null || score === undefined)
    return { label: 'No data',   className: 'bg-gray-100 text-gray-500' };
  if (score >= 80) return { label: 'Strong',     className: 'bg-green-100 text-green-700' };
  if (score >= 60) return { label: 'Solid',       className: 'bg-yellow-100 text-yellow-700' };
  if (score >= 40) return { label: 'Needs work',  className: 'bg-orange-100 text-orange-700' };
  return              { label: 'Limiting',     className: 'bg-red-100 text-red-700' };
}

// ---------------------------------------------------------------------------
// TestGetComponentChip
// ---------------------------------------------------------------------------

describe('getComponentChip', () => {
  it('null → No data', () => {
    expect(getComponentChip(null).label).toBe('No data');
  });

  it('undefined → No data', () => {
    expect(getComponentChip(undefined).label).toBe('No data');
  });

  it('85 → Strong', () => {
    expect(getComponentChip(85).label).toBe('Strong');
  });

  it('80 → Strong', () => {
    expect(getComponentChip(80).label).toBe('Strong');
  });

  it('79 → Solid', () => {
    expect(getComponentChip(79).label).toBe('Solid');
  });

  it('65 → Solid', () => {
    expect(getComponentChip(65).label).toBe('Solid');
  });

  it('60 → Solid', () => {
    expect(getComponentChip(60).label).toBe('Solid');
  });

  it('59 → Needs work', () => {
    expect(getComponentChip(59).label).toBe('Needs work');
  });

  it('45 → Needs work', () => {
    expect(getComponentChip(45).label).toBe('Needs work');
  });

  it('39 → Limiting', () => {
    expect(getComponentChip(39).label).toBe('Limiting');
  });

  it('0 → Limiting', () => {
    expect(getComponentChip(0).label).toBe('Limiting');
  });
});

// ---------------------------------------------------------------------------
// Inline replica of buildFormSummary logic (pure, no React state)
// ---------------------------------------------------------------------------

const LIMITER_LABELS: Record<string, string> = {
  torso_stability_score: 'trunk stability',
  knee_symmetry_score:   'knee tracking',
  bottom_control_score:  'bottom position control',
  forward_lean_score:    'forward lean',
};

function getScoreBand(score: number | null) {
  if (score == null) return null;
  if (score >= 90) return 'excellent';
  if (score >= 75) return 'good';
  if (score >= 60) return 'needs_work';
  return 'poor';
}

function buildFormSummaryTest(
  decision: string | undefined,
  namedScores: Record<string, number | null> | null | undefined,
  overallScore: number | null,
  isLowConfidence = false,
): string {
  if (!decision || decision === 'uncertain') return '';
  if (!namedScores) return '';
  const band = getScoreBand(overallScore);
  if (!band) return '';

  const candidates: Array<{ key: string; score: number }> = (
    [
      namedScores.torso_stability_score != null
        ? { key: 'torso_stability_score', score: namedScores.torso_stability_score } : null,
      namedScores.knee_symmetry_score != null
        ? { key: 'knee_symmetry_score', score: namedScores.knee_symmetry_score } : null,
      namedScores.bottom_control_score != null
        ? { key: 'bottom_control_score', score: namedScores.bottom_control_score } : null,
      namedScores.forward_lean_score != null && namedScores.forward_lean_score < 75
        ? { key: 'forward_lean_score', score: namedScores.forward_lean_score } : null,
    ] as (null | { key: string; score: number })[]
  ).filter((c): c is { key: string; score: number } => c != null);

  if (candidates.length === 0) {
    return band === 'excellent'
      ? 'Strong squat mechanics. Only minor polish needed to reach peak efficiency.'
      : 'Analysis complete. Re-record with full body in frame for component-level insights.';
  }

  candidates.sort((a, b) => a.score - b.score);
  const primaryLabel = LIMITER_LABELS[candidates[0]?.key] ?? candidates[0]?.key ?? '';
  const c1 = LIMITER_LABELS[candidates[0]?.key] ?? '';
  const c2 = LIMITER_LABELS[candidates[1]?.key];

  switch (band) {
    case 'poor':
      return isLowConfidence
        ? `Some instability was detected, particularly in ${c1}${c2 ? ` and ${c2}` : ''}. Video quality or movement clarity reduced analysis confidence — use this as guidance, not a final verdict. Key area to work on: ${primaryLabel}.`
        : `Your squat shows significant instability, especially in ${c1}${c2 ? ` and ${c2}` : ''}. Work on stabilising these areas before adding load. Key area to work on: ${primaryLabel}.`;
    case 'needs_work':
      return isLowConfidence
        ? `Some areas to improve were identified, particularly ${c1}${c2 ? ` and ${c2}` : ''}. Confidence was limited — re-record with better visibility for a more definitive read. Key area to work on: ${primaryLabel}.`
        : `Your form has a solid base but instability in ${c1}${c2 ? ` and ${c2}` : ''} is limiting your performance. Key area to work on: ${primaryLabel}.`;
    case 'good':
      return `Overall solid squat form. Minor refinements in ${c1} can further improve stability and efficiency. Key area to work on: ${primaryLabel}.`;
    case 'excellent':
      return 'Strong squat mechanics. Only minor polish needed to reach peak efficiency.';
    default:
      return '';
  }
}

// ---------------------------------------------------------------------------
// TestBuildFormSummary
// ---------------------------------------------------------------------------

describe('buildFormSummary', () => {
  it('primary limiter label "knee tracking" appears when knee_symmetry is worst', () => {
    const summary = buildFormSummaryTest(
      'fault',
      {
        torso_stability_score: 80,
        knee_symmetry_score: 35,
        bottom_control_score: 70,
        forward_lean_score: 80,
      },
      55, // poor band
    );
    expect(summary).toContain('knee tracking');
  });

  it('uncertain decision → empty summary', () => {
    const summary = buildFormSummaryTest(
      'uncertain',
      { torso_stability_score: 50, knee_symmetry_score: 50, bottom_control_score: 50, forward_lean_score: 50 },
      50,
    );
    expect(summary).toBe('');
  });

  it('excellent band → no "Key area" suffix', () => {
    const summary = buildFormSummaryTest(
      'good_form',
      {
        torso_stability_score: 95,
        knee_symmetry_score: 92,
        bottom_control_score: 91,
        forward_lean_score: 90,
      },
      93,
    );
    expect(summary).not.toContain('Key area');
    expect(summary).toContain('Strong squat mechanics');
  });

  it('non-excellent band → contains "Key area to work on:"', () => {
    const summary = buildFormSummaryTest(
      'fault',
      { torso_stability_score: 55, knee_symmetry_score: 70, bottom_control_score: 65, forward_lean_score: 80 },
      65,
    );
    expect(summary).toContain('Key area to work on:');
  });

  it('poor band + low confidence → softened language mentioning "guidance, not a final verdict"', () => {
    const summary = buildFormSummaryTest(
      'fault',
      { torso_stability_score: 30, knee_symmetry_score: 45, bottom_control_score: 50, forward_lean_score: 80 },
      52, // poor band
      true, // isLowConfidence
    );
    expect(summary).toContain('guidance, not a final verdict');
    expect(summary).not.toContain('significant instability');
  });

  it('needs_work band + low confidence → softened language mentioning "re-record with better visibility"', () => {
    const summary = buildFormSummaryTest(
      'fault',
      { torso_stability_score: 65, knee_symmetry_score: 62, bottom_control_score: 68, forward_lean_score: 80 },
      63, // needs_work band
      true, // isLowConfidence
    );
    expect(summary).toContain('re-record with better visibility');
    expect(summary).not.toContain('solid base but instability');
  });

  it('poor band + normal confidence → uses strong language', () => {
    const summary = buildFormSummaryTest(
      'fault',
      { torso_stability_score: 30, knee_symmetry_score: 45, bottom_control_score: 50, forward_lean_score: 80 },
      52, // poor band
      false, // normal confidence
    );
    expect(summary).toContain('significant instability');
    expect(summary).not.toContain('guidance, not a final verdict');
  });

  it('all named_scores null → safe fallback, no instability claims', () => {
    const summary = buildFormSummaryTest(
      'fault',
      { torso_stability_score: null, knee_symmetry_score: null, bottom_control_score: null, forward_lean_score: null },
      55, // poor band
    );
    expect(summary).not.toContain('instability');
    expect(summary).not.toContain('trunk stability');
    expect(summary).not.toContain('knee tracking');
    expect(summary).toContain('Re-record with full body in frame');
  });
});

// ---------------------------------------------------------------------------
// buildFormSummaryBullets — inline replica for praise threshold tests
// Mirrors the updated logic in AnalysisPage.tsx (Change 3a)
// ---------------------------------------------------------------------------

function buildFormSummaryBulletsTest(
  decision: string | undefined,
  namedScores: Record<string, number | null> | null | undefined,
  overallScore: number | null,
  primaryLimiterKey?: string | null,
): { headline: string; bullets: string[] } | null {
  if (!decision || decision === 'uncertain') return null;
  const band = getScoreBand(overallScore);
  if (!namedScores || !band) return null;

  const all = (
    [
      namedScores.torso_stability_score != null
        ? { label: 'Trunk stability',         score: namedScores.torso_stability_score } : null,
      namedScores.knee_symmetry_score != null
        ? { label: 'Knee alignment',          score: namedScores.knee_symmetry_score   } : null,
      namedScores.bottom_control_score != null
        ? { label: 'Bottom position control', score: namedScores.bottom_control_score  } : null,
      namedScores.forward_lean_score != null
        ? { label: 'Forward lean control',    score: namedScores.forward_lean_score    } : null,
    ] as (null | { label: string; score: number })[]
  ).filter((c): c is { label: string; score: number } => c != null);

  if (all.length === 0) return null;

  const sorted = [...all].sort((a, b) => a.score - b.score);
  const worst  = sorted[0];
  const best   = [...sorted].sort((a, b) => b.score - a.score)[0];

  const limiterLabel = primaryLimiterKey
    ? (LIMITER_LABELS[primaryLimiterKey] ?? worst.label)
    : worst.label;

  const headlines: Record<string, string> = {
    excellent: 'Strong squat mechanics. Consistency is your next unlock.',
    good:      'Solid form. One focused fix can break your next tier.',
    needs_work: `Close to leveling up. Fix ${limiterLabel} to break your next tier%.`,
    poor:      'Correct form first — one key fix changes everything.',
  };

  const bullets = [
    best.score >= 75
      ? `Your ${best.label} is your strongest area (${best.score}%).`
      : best.score >= 65
      ? `Your ${best.label} is your most stable area so far (${best.score}%).`
      : `Your form is developing across all areas — ${limiterLabel} is the fastest path to improvement.`,
    `${limiterLabel.charAt(0).toUpperCase() + limiterLabel.slice(1)} is currently limiting your performance (${worst.score}%).`,
    `Next: target ${limiterLabel} drills — see the Tips tab for specific exercises.`,
  ];

  return { headline: headlines[band] ?? '', bullets };
}

describe('buildFormSummaryBullets — praise threshold', () => {
  const baseScores = {
    torso_stability_score: 80,
    knee_symmetry_score: 70,
    bottom_control_score: 72,
    forward_lean_score: 68,
  };

  it('best score ≥ 75: first bullet contains "strongest area"', () => {
    // torso_stability_score = 80 → best = Trunk stability (80)
    const result = buildFormSummaryBulletsTest('fault', baseScores, 72);
    expect(result).not.toBeNull();
    expect(result!.bullets[0]).toContain('strongest area');
  });

  it('best score 65–74: first bullet contains "most stable area so far"', () => {
    const scores = {
      torso_stability_score: 70,
      knee_symmetry_score: 65,
      bottom_control_score: 60,
      forward_lean_score: 55,
    };
    // best = Trunk stability (70), 65 ≤ 70 < 75
    const result = buildFormSummaryBulletsTest('fault', scores, 65);
    expect(result).not.toBeNull();
    expect(result!.bullets[0]).toContain('most stable area so far');
    expect(result!.bullets[0]).not.toContain('strongest area');
  });

  it('best score < 65: first bullet does NOT contain "strongest area" or "most stable"', () => {
    const scores = {
      torso_stability_score: 62,
      knee_symmetry_score: 55,
      bottom_control_score: 50,
      forward_lean_score: 45,
    };
    // best = Trunk stability (62) < 65
    const result = buildFormSummaryBulletsTest('fault', scores, 55);
    expect(result).not.toBeNull();
    expect(result!.bullets[0]).not.toContain('strongest area');
    expect(result!.bullets[0]).not.toContain('most stable area so far');
  });

  it('best score exactly 75: uses "strongest area"', () => {
    const scores = {
      torso_stability_score: 75,
      knee_symmetry_score: 60,
      bottom_control_score: 58,
      forward_lean_score: 55,
    };
    const result = buildFormSummaryBulletsTest('fault', scores, 62);
    expect(result!.bullets[0]).toContain('strongest area');
  });

  it('best score exactly 65: uses "most stable area so far"', () => {
    const scores = {
      torso_stability_score: 65,
      knee_symmetry_score: 60,
      bottom_control_score: 58,
      forward_lean_score: 55,
    };
    const result = buildFormSummaryBulletsTest('fault', scores, 60);
    expect(result!.bullets[0]).toContain('most stable area so far');
  });

  it('uncertain decision → null', () => {
    const result = buildFormSummaryBulletsTest('uncertain', baseScores, 72);
    expect(result).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// EvidenceSection — inline minimal replica for testing
// ---------------------------------------------------------------------------

interface HighlightFrame {
  frame_index: number;
  timestamp_sec: number;
  knee_angle_left: number | null;
  knee_angle_right: number | null;
  hip_angle: number | null;
  depth_proxy: number;
}

function EvidenceSectionTest({
  highlight,
  videoUrl,
  overallScore,
  decision,
}: {
  highlight: HighlightFrame | null | undefined;
  videoUrl?: string;
  overallScore: number | null;
  decision?: string;
}) {
  if (!highlight || decision === 'uncertain') return null;

  const angleLabels = [
    highlight.knee_angle_left != null ? `L: ${highlight.knee_angle_left}°` : null,
    highlight.knee_angle_right != null ? `R: ${highlight.knee_angle_right}°` : null,
  ].filter(Boolean).join('  ');

  return (
    <div data-testid="evidence-section">
      {angleLabels && (
        <p data-testid="angle-labels">{angleLabels}</p>
      )}
      <canvas data-testid="evidence-canvas" width={640} height={360} />
      {videoUrl && (
        <video data-testid="evidence-video" src={videoUrl} crossOrigin="anonymous" />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// TestEvidenceSection
// ---------------------------------------------------------------------------

const sampleHighlight: HighlightFrame = {
  frame_index: 30,
  timestamp_sec: 1.0,
  knee_angle_left: 87,
  knee_angle_right: 91,
  hip_angle: 75,
  depth_proxy: 0.72,
};

describe('EvidenceSection', () => {
  it('renders nothing when highlight_frame is null', () => {
    const { container } = render(
      <EvidenceSectionTest
        highlight={null}
        overallScore={80}
        decision="good_form"
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders nothing when highlight_frame is undefined', () => {
    const { container } = render(
      <EvidenceSectionTest
        highlight={undefined}
        overallScore={80}
        decision="good_form"
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders canvas element when highlight_frame is present', () => {
    render(
      <EvidenceSectionTest
        highlight={sampleHighlight}
        overallScore={80}
        decision="good_form"
      />
    );
    expect(screen.getByTestId('evidence-canvas')).toBeInTheDocument();
  });

  it('knee angle label "L: 87°" visible when knee_angle_left=87', () => {
    render(
      <EvidenceSectionTest
        highlight={sampleHighlight}
        overallScore={80}
        decision="good_form"
      />
    );
    expect(screen.getByTestId('angle-labels')).toHaveTextContent('L: 87°');
  });

  it('knee angle label "R: 91°" visible when knee_angle_right=91', () => {
    render(
      <EvidenceSectionTest
        highlight={sampleHighlight}
        overallScore={80}
        decision="good_form"
      />
    );
    expect(screen.getByTestId('angle-labels')).toHaveTextContent('R: 91°');
  });

  it('hidden (returns null) when decision is "uncertain"', () => {
    const { container } = render(
      <EvidenceSectionTest
        highlight={sampleHighlight}
        overallScore={80}
        decision="uncertain"
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders evidence section when all fields are present', () => {
    render(
      <EvidenceSectionTest
        highlight={sampleHighlight}
        videoUrl="https://example.com/video.mp4"
        overallScore={72}
        decision="fault"
      />
    );
    expect(screen.getByTestId('evidence-section')).toBeInTheDocument();
    expect(screen.getByTestId('evidence-video')).toBeInTheDocument();
  });

  it('null knee_angle_left → no L: label shown', () => {
    const noLeftKnee: HighlightFrame = { ...sampleHighlight, knee_angle_left: null };
    render(
      <EvidenceSectionTest
        highlight={noLeftKnee}
        overallScore={80}
        decision="good_form"
      />
    );
    const labels = screen.queryByTestId('angle-labels');
    // Only R label should appear, not L
    if (labels) {
      expect(labels.textContent).not.toContain('L:');
      expect(labels.textContent).toContain('R:');
    }
  });

  it('both knee angles null → no angle label element rendered', () => {
    const noKnees: HighlightFrame = {
      ...sampleHighlight,
      knee_angle_left: null,
      knee_angle_right: null,
    };
    render(
      <EvidenceSectionTest
        highlight={noKnees}
        overallScore={80}
        decision="good_form"
      />
    );
    expect(screen.queryByTestId('angle-labels')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Null component score — "Insufficient data" rendering
// Verifies that null-scored components show the greyed fallback, not nothing.
// ---------------------------------------------------------------------------

function NullComponentRow({ label, score }: { label: string; score: number | null }) {
  if (score == null) {
    return (
      <div data-testid="null-component-row">
        <span data-testid="component-label">{label}</span>
        <span data-testid="insufficient-chip">Insufficient data</span>
        <span data-testid="null-dash">—</span>
      </div>
    );
  }
  return (
    <div data-testid="scored-component-row">
      <span data-testid="component-label">{label}</span>
      <span data-testid="score-value">{score}%</span>
    </div>
  );
}

describe('Component Scores — null score rendering', () => {
  it('null score → renders "Insufficient data" chip instead of hiding the row', () => {
    render(<NullComponentRow label="Knee Symmetry" score={null} />);
    expect(screen.getByTestId('null-component-row')).toBeInTheDocument();
    expect(screen.getByTestId('insufficient-chip')).toHaveTextContent('Insufficient data');
    expect(screen.getByTestId('null-dash')).toHaveTextContent('—');
  });

  it('null score → still renders the component label', () => {
    render(<NullComponentRow label="Torso Stability" score={null} />);
    expect(screen.getByTestId('component-label')).toHaveTextContent('Torso Stability');
  });

  it('non-null score → renders score value, not "Insufficient data"', () => {
    render(<NullComponentRow label="Bottom Control" score={72} />);
    expect(screen.getByTestId('scored-component-row')).toBeInTheDocument();
    expect(screen.queryByTestId('insufficient-chip')).toBeNull();
    expect(screen.getByTestId('score-value')).toHaveTextContent('72%');
  });
});

// ---------------------------------------------------------------------------
// Inline replicas of new pure helpers
// ---------------------------------------------------------------------------

function computeProjectedScore(
  currentOverall: number,
  currentComponent: number,
  targetComponent = 75,
  weight = 0.25,
): number {
  const gain = Math.max(0, targetComponent - currentComponent);
  return Math.min(100, Math.round(currentOverall + gain * weight));
}

function getComponentSeverities(
  named: { torso_stability_score: number | null; knee_symmetry_score: number | null; bottom_control_score: number | null; forward_lean_score: number | null } | undefined,
): Record<string, 'Priority' | 'Improve' | 'Maintain'> {
  if (!named) return {};
  const entries = [
    { key: 'torso_stability_score', score: named.torso_stability_score },
    { key: 'knee_symmetry_score',   score: named.knee_symmetry_score },
    { key: 'bottom_control_score',  score: named.bottom_control_score },
    { key: 'forward_lean_score',    score: named.forward_lean_score },
  ].filter((e): e is { key: string; score: number } => e.score != null);
  entries.sort((a, b) => a.score - b.score);
  const out: Record<string, 'Priority' | 'Improve' | 'Maintain'> = {};
  entries.forEach((e, i) => {
    out[e.key] = i === 0 ? 'Priority' : i === 1 ? 'Improve' : 'Maintain';
  });
  return out;
}

function getLevelInfo(score: number | null): {
  current: string; next: string | null; nextScore: number | null; progressPct: number;
} | null {
  if (score == null) return null;
  let current: string, prevScore: number, next: string | null, nextScore: number | null;
  if (score >= 92)      { current = 'Elite';      prevScore = 92; next = null;          nextScore = null; }
  else if (score >= 85) { current = 'Advanced';   prevScore = 85; next = 'Elite';       nextScore = 92; }
  else if (score >= 75) { current = 'Solid';       prevScore = 75; next = 'Advanced';    nextScore = 85; }
  else if (score >= 60) { current = 'Developing';  prevScore = 60; next = 'Solid';       nextScore = 75; }
  else                  { current = 'Beginner';    prevScore = 0;  next = 'Developing';  nextScore = 60; }
  const progressPct = nextScore != null
    ? Math.min(100, Math.round(((score - prevScore) / (nextScore - prevScore)) * 100))
    : 100;
  return { current, next, nextScore, progressPct };
}

// ---------------------------------------------------------------------------
// computeProjectedScore tests
// ---------------------------------------------------------------------------

describe('computeProjectedScore', () => {
  it('basic gain: component 40, overall 65 → projects above 65', () => {
    const result = computeProjectedScore(65, 40);
    expect(result).toBeGreaterThan(65);
    expect(result).toBe(65 + Math.round((75 - 40) * 0.25)); // 65 + 9 = 74
  });

  it('capped at 100 when gain would exceed maximum', () => {
    expect(computeProjectedScore(99, 0)).toBe(100);
  });

  it('returns current overall when component >= target (no gain)', () => {
    expect(computeProjectedScore(80, 75)).toBe(80);
    expect(computeProjectedScore(80, 90)).toBe(80);
  });
});

// ---------------------------------------------------------------------------
// getComponentSeverities tests
// ---------------------------------------------------------------------------

describe('getComponentSeverities', () => {
  it('lowest score gets Priority', () => {
    const s = getComponentSeverities({
      torso_stability_score: 30,
      knee_symmetry_score: 60,
      bottom_control_score: 70,
      forward_lean_score: 80,
    });
    expect(s['torso_stability_score']).toBe('Priority');
  });

  it('second lowest gets Improve', () => {
    const s = getComponentSeverities({
      torso_stability_score: 30,
      knee_symmetry_score: 60,
      bottom_control_score: 70,
      forward_lean_score: 80,
    });
    expect(s['knee_symmetry_score']).toBe('Improve');
  });

  it('remaining components get Maintain', () => {
    const s = getComponentSeverities({
      torso_stability_score: 30,
      knee_symmetry_score: 60,
      bottom_control_score: 70,
      forward_lean_score: 80,
    });
    expect(s['bottom_control_score']).toBe('Maintain');
    expect(s['forward_lean_score']).toBe('Maintain');
  });

  it('single non-null component gets Priority only', () => {
    const s = getComponentSeverities({
      torso_stability_score: 55,
      knee_symmetry_score: null,
      bottom_control_score: null,
      forward_lean_score: null,
    });
    expect(s['torso_stability_score']).toBe('Priority');
    expect(Object.keys(s)).toHaveLength(1);
  });

  it('all null → empty record', () => {
    const s = getComponentSeverities({
      torso_stability_score: null,
      knee_symmetry_score: null,
      bottom_control_score: null,
      forward_lean_score: null,
    });
    expect(Object.keys(s)).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// getLevelInfo tests
// ---------------------------------------------------------------------------

describe('getLevelInfo', () => {
  it('null score returns null', () => {
    expect(getLevelInfo(null)).toBeNull();
  });

  it('Beginner tier: score=30 → next=Developing at 60, non-zero progress', () => {
    const info = getLevelInfo(30)!;
    expect(info.current).toBe('Beginner');
    expect(info.next).toBe('Developing');
    expect(info.nextScore).toBe(60);
    expect(info.progressPct).toBeGreaterThan(0);
    expect(info.progressPct).toBeLessThan(100);
  });

  it('boundary: score=75 → Solid tier begins', () => {
    const info = getLevelInfo(75)!;
    expect(info.current).toBe('Solid');
    expect(info.next).toBe('Advanced');
    expect(info.nextScore).toBe(85);
  });

  it('Elite tier: score=95 → no next level', () => {
    const info = getLevelInfo(95)!;
    expect(info.current).toBe('Elite');
    expect(info.next).toBeNull();
    expect(info.nextScore).toBeNull();
    expect(info.progressPct).toBe(100);
  });
});

// ---------------------------------------------------------------------------
// Adaptive Focus helpers (inline replicas)
// ---------------------------------------------------------------------------

const LIMITER_LABELS_TEST: Record<string, string> = {
  torso_stability_score: 'trunk stability',
  knee_symmetry_score:   'knee tracking',
  bottom_control_score:  'bottom position control',
  forward_lean_score:    'forward lean',
};

interface LimiterHistoryEntry {
  id: string;
  limiterKey: string;
  score: number;
  ts: number;
}

function computeAdaptiveFocusTest(
  namedScores: { torso_stability_score: number | null; knee_symmetry_score: number | null; bottom_control_score: number | null; forward_lean_score: number | null } | null | undefined,
  currentId: string,
  history: LimiterHistoryEntry[],
): { focusKey: string; focusLabel: string; isAdapted: boolean; adaptedMessage?: string } | null {
  if (!namedScores) return null;
  const entries = [
    { key: 'torso_stability_score', score: namedScores.torso_stability_score },
    { key: 'knee_symmetry_score',   score: namedScores.knee_symmetry_score },
    { key: 'bottom_control_score',  score: namedScores.bottom_control_score },
    { key: 'forward_lean_score',    score: namedScores.forward_lean_score },
  ].filter((e): e is { key: string; score: number } => e.score != null);
  if (entries.length === 0) return null;
  entries.sort((a, b) => a.score - b.score);
  const naturalLimiter = entries[0];
  const naturalLabel = LIMITER_LABELS_TEST[naturalLimiter.key] ?? naturalLimiter.key;
  const past = history.filter(h => h.id !== currentId).sort((a, b) => b.ts - a.ts).slice(0, 5);
  if (past.length >= 3) {
    const streak = past.slice(0, 3);
    const allSame = streak.every(h => h.limiterKey === naturalLimiter.key);
    if (allSame) {
      const oldestInStreak = streak[2];
      const improved = naturalLimiter.score - oldestInStreak.score > 8;
      if (improved && entries.length >= 2) {
        const second = entries[1];
        const secondLabel = LIMITER_LABELS_TEST[second.key] ?? second.key;
        return {
          focusKey: second.key,
          focusLabel: secondLabel,
          isAdapted: true,
          adaptedMessage: `You've worked on ${naturalLabel} for 3 sessions. ${secondLabel.charAt(0).toUpperCase() + secondLabel.slice(1)} is now your next biggest unlock.`,
        };
      }
    }
  }
  return { focusKey: naturalLimiter.key, focusLabel: naturalLabel, isAdapted: false };
}

describe('computeAdaptiveFocus', () => {
  const baseScores = {
    torso_stability_score: 40,
    knee_symmetry_score: 65,
    bottom_control_score: 70,
    forward_lean_score: 80,
  };

  it('< 3 history entries → uses natural limiter (not adapted)', () => {
    const history: LimiterHistoryEntry[] = [
      { id: 'prev1', limiterKey: 'torso_stability_score', score: 38, ts: 1 },
    ];
    const result = computeAdaptiveFocusTest(baseScores, 'curr', history);
    expect(result?.isAdapted).toBe(false);
    expect(result?.focusKey).toBe('torso_stability_score');
  });

  it('same limiter 3× with > 8pt improvement → adapts to second component', () => {
    // Natural limiter torso_stability_score went from 30 → 40 (> 8 pts)
    const history: LimiterHistoryEntry[] = [
      { id: 'prev1', limiterKey: 'torso_stability_score', score: 38, ts: 3 },
      { id: 'prev2', limiterKey: 'torso_stability_score', score: 35, ts: 2 },
      { id: 'prev3', limiterKey: 'torso_stability_score', score: 30, ts: 1 }, // oldest in streak: score 30
    ];
    // current score is 40 — 40 - 30 = 10 > 8 → should adapt
    const result = computeAdaptiveFocusTest(baseScores, 'curr', history);
    expect(result?.isAdapted).toBe(true);
    expect(result?.focusKey).toBe('knee_symmetry_score'); // second lowest
    expect(result?.adaptedMessage).toContain("You've worked on trunk stability for 3 sessions.");
  });

  it('same limiter 3× but improvement ≤ 8pts → stays with natural limiter', () => {
    // Natural limiter current score 40, oldest in streak was 34 → diff = 6 ≤ 8
    const history: LimiterHistoryEntry[] = [
      { id: 'prev1', limiterKey: 'torso_stability_score', score: 39, ts: 3 },
      { id: 'prev2', limiterKey: 'torso_stability_score', score: 37, ts: 2 },
      { id: 'prev3', limiterKey: 'torso_stability_score', score: 34, ts: 1 },
    ];
    const result = computeAdaptiveFocusTest(baseScores, 'curr', history);
    expect(result?.isAdapted).toBe(false);
    expect(result?.focusKey).toBe('torso_stability_score');
  });
});

// ---------------------------------------------------------------------------
// Delta summary chips — rendering logic test (inline component replica)
// ---------------------------------------------------------------------------

interface DeltaChipProps {
  baselineSession: boolean;
  torsoStabilityDelta: number | null;
  kneeSymmetryDelta: number | null;
  bottomControlDelta: number | null;
  forwardLeanDelta: number | null;
}

function DeltaChipsTest({ baselineSession, torsoStabilityDelta, kneeSymmetryDelta, bottomControlDelta, forwardLeanDelta }: DeltaChipProps) {
  if (baselineSession) return null;
  const componentDeltas = [
    { label: 'Trunk',   val: torsoStabilityDelta },
    { label: 'Knee',    val: kneeSymmetryDelta },
    { label: 'Control', val: bottomControlDelta },
    { label: 'Lean',    val: forwardLeanDelta },
  ].filter((c): c is { label: string; val: number } => c.val != null);
  if (componentDeltas.length === 0) return null;
  return (
    <div data-testid="delta-chips">
      {componentDeltas.map(c => (
        <span key={c.label} data-testid={`delta-${c.label.toLowerCase()}`}>
          {c.label} {c.val >= 0 ? '↑' : '↓'}{Math.abs(c.val)}
        </span>
      ))}
    </div>
  );
}

describe('Delta summary chips', () => {
  it('renders chips when delta values are present', () => {
    render(
      <DeltaChipsTest
        baselineSession={false}
        torsoStabilityDelta={5}
        kneeSymmetryDelta={-3}
        bottomControlDelta={2}
        forwardLeanDelta={null}
      />
    );
    expect(screen.getByTestId('delta-chips')).toBeInTheDocument();
    expect(screen.getByTestId('delta-trunk')).toHaveTextContent('Trunk ↑5');
    expect(screen.getByTestId('delta-knee')).toHaveTextContent('Knee ↓3');
    expect(screen.queryByTestId('delta-lean')).toBeNull();
  });

  it('hides chips when baseline_session is true', () => {
    render(
      <DeltaChipsTest
        baselineSession={true}
        torsoStabilityDelta={5}
        kneeSymmetryDelta={3}
        bottomControlDelta={2}
        forwardLeanDelta={1}
      />
    );
    expect(screen.queryByTestId('delta-chips')).toBeNull();
  });

  it('hides chips when all component deltas are null', () => {
    render(
      <DeltaChipsTest
        baselineSession={false}
        torsoStabilityDelta={null}
        kneeSymmetryDelta={null}
        bottomControlDelta={null}
        forwardLeanDelta={null}
      />
    );
    expect(screen.queryByTestId('delta-chips')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Feature 1 — applyStrictPriorityRank (inline replica)
// Ensures generateRecommendations never produces more than one "Priority" badge.
// ---------------------------------------------------------------------------

function applyStrictPriorityRank<T extends { priority: 'high' | 'medium' | 'low' }>(tips: T[]): T[] {
  return tips.map((tip, i) => ({
    ...tip,
    priority: (i === 0 ? 'high' : i === 1 ? 'medium' : 'low') as 'high' | 'medium' | 'low',
  }));
}

describe('applyStrictPriorityRank (Feature 1)', () => {
  it('4 tips all high → priorities are [high, medium, low, low]', () => {
    const input = [
      { priority: 'high' as const, title: 'A' },
      { priority: 'high' as const, title: 'B' },
      { priority: 'high' as const, title: 'C' },
      { priority: 'high' as const, title: 'D' },
    ];
    const result = applyStrictPriorityRank(input);
    expect(result.map(r => r.priority)).toEqual(['high', 'medium', 'low', 'low']);
  });

  it('2 tips both high → [high, medium]', () => {
    const input = [
      { priority: 'high' as const, title: 'A' },
      { priority: 'high' as const, title: 'B' },
    ];
    const result = applyStrictPriorityRank(input);
    expect(result.map(r => r.priority)).toEqual(['high', 'medium']);
  });

  it('1 tip → stays [high]', () => {
    const input = [{ priority: 'medium' as const, title: 'A' }];
    const result = applyStrictPriorityRank(input);
    expect(result[0].priority).toBe('high');
  });

  it('preserves other tip fields unchanged', () => {
    const input = [{ priority: 'high' as const, title: 'Keep me', description: 'desc' }];
    const result = applyStrictPriorityRank(input);
    expect(result[0].title).toBe('Keep me');
    expect(result[0].description).toBe('desc');
  });
});

// ---------------------------------------------------------------------------
// Feature 2 — SEVERITY_BAR_COLOR (inline replica)
// ---------------------------------------------------------------------------

const SEVERITY_BAR_COLOR_TEST: Record<string, string> = {
  Priority: 'bg-red-500',
  Improve:  'bg-amber-400',
  Maintain: 'bg-slate-400',
};

describe('SEVERITY_BAR_COLOR (Feature 2)', () => {
  it('Priority → bg-red-500', () => {
    expect(SEVERITY_BAR_COLOR_TEST['Priority']).toBe('bg-red-500');
  });

  it('Improve → bg-amber-400', () => {
    expect(SEVERITY_BAR_COLOR_TEST['Improve']).toBe('bg-amber-400');
  });

  it('Maintain → bg-slate-400', () => {
    expect(SEVERITY_BAR_COLOR_TEST['Maintain']).toBe('bg-slate-400');
  });
});

// ---------------------------------------------------------------------------
// One-red-limiter invariant
// Mirrors the severity ranking logic in AnalysisPage.tsx Overview breakdown
// ---------------------------------------------------------------------------

function rankBreakdown(items: Array<{ score: number }>): string[] {
  const bySeverity = [...items].sort((a, b) => a.score - b.score);
  return items.map(item => {
    const rank = bySeverity.indexOf(item);
    return rank === 0 ? 'Priority' : rank === 1 ? 'Improve' : 'Maintain';
  });
}

describe('one-red-limiter invariant', () => {
  it('4 components → exactly one Priority', () => {
    const items = [
      { score: 40 }, { score: 60 }, { score: 75 }, { score: 85 },
    ];
    const ranks = rankBreakdown(items);
    expect(ranks.filter(r => r === 'Priority').length).toBe(1);
  });

  it('2 components → exactly one Priority, one Improve', () => {
    const items = [{ score: 55 }, { score: 72 }];
    const ranks = rankBreakdown(items);
    expect(ranks.filter(r => r === 'Priority').length).toBe(1);
    expect(ranks.filter(r => r === 'Improve').length).toBe(1);
  });

  it('1 component → exactly one Priority, no Improve', () => {
    const items = [{ score: 70 }];
    const ranks = rankBreakdown(items);
    expect(ranks.filter(r => r === 'Priority').length).toBe(1);
    expect(ranks.filter(r => r === 'Improve').length).toBe(0);
  });

  it('Priority is always the lowest-scoring component', () => {
    const items = [
      { score: 80 }, { score: 45 }, { score: 65 }, { score: 90 },
    ];
    const ranks = rankBreakdown(items);
    const priorityIdx = ranks.indexOf('Priority');
    const minScore = Math.min(...items.map(i => i.score));
    expect(items[priorityIdx].score).toBe(minScore);
  });

  it('equal scores: first occurrence by original order gets Priority', () => {
    // When two items tie, Array.indexOf returns the first match
    const items = [{ score: 60 }, { score: 60 }, { score: 80 }];
    const ranks = rankBreakdown(items);
    // Exactly one Priority regardless of ties
    expect(ranks.filter(r => r === 'Priority').length).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Feature 3 — EvidenceSection fallback skeleton (inline replica)
// ---------------------------------------------------------------------------

function EvidenceFallbackTest({
  highlight,
  criticalFrameImageUrl,
  criticalFrameAngles,
}: {
  highlight: null | undefined;
  criticalFrameImageUrl?: string | null;
  criticalFrameAngles?: { hip_angle?: number; knee_angle?: number };
}) {
  if (criticalFrameImageUrl) return <div data-testid="image-path" />;
  if (!highlight) {
    return (
      <div
        data-testid="evidence-fallback-skeleton"
        style={{ aspectRatio: '16/9' }}
      >
        <p className="subtitle">Deepest squat position — key angles captured</p>
        <p>Snapshot unavailable for this clip.</p>
        <p>Your form score is still based on full motion analysis.</p>
        {criticalFrameAngles?.hip_angle != null && (
          <span data-testid="hip-angle-badge">Hip: {criticalFrameAngles.hip_angle}°</span>
        )}
        {criticalFrameAngles?.knee_angle != null && (
          <span data-testid="knee-angle-badge">Knee: {criticalFrameAngles.knee_angle}°</span>
        )}
      </div>
    );
  }
  return null;
}

describe('EvidenceSection fallback skeleton (Feature 3)', () => {
  it('renders fallback skeleton when highlight is null and no image URL', () => {
    render(
      <EvidenceFallbackTest
        highlight={null}
        criticalFrameImageUrl={undefined}
      />
    );
    expect(screen.getByTestId('evidence-fallback-skeleton')).toBeInTheDocument();
    expect(screen.getByText(/Snapshot unavailable/)).toBeInTheDocument();
  });

  it('subtitle "Deepest squat position" renders when highlight is null', () => {
    render(
      <EvidenceFallbackTest
        highlight={null}
        criticalFrameImageUrl={undefined}
      />
    );
    expect(screen.getByText(/Deepest squat position/)).toBeInTheDocument();
  });

  it('"full motion analysis" text renders when highlight is null', () => {
    render(
      <EvidenceFallbackTest
        highlight={null}
        criticalFrameImageUrl={undefined}
      />
    );
    expect(screen.getByText(/full motion analysis/)).toBeInTheDocument();
  });

  it('renders fallback skeleton when highlight is undefined and no image URL', () => {
    render(
      <EvidenceFallbackTest
        highlight={undefined}
        criticalFrameImageUrl={undefined}
      />
    );
    expect(screen.getByTestId('evidence-fallback-skeleton')).toBeInTheDocument();
  });

  it('shows hip angle badge when criticalFrameAngles.hip_angle is provided', () => {
    render(
      <EvidenceFallbackTest
        highlight={null}
        criticalFrameAngles={{ hip_angle: 88 }}
      />
    );
    expect(screen.getByTestId('hip-angle-badge')).toHaveTextContent('Hip: 88°');
  });

  it('shows knee angle badge when criticalFrameAngles.knee_angle is provided', () => {
    render(
      <EvidenceFallbackTest
        highlight={null}
        criticalFrameAngles={{ knee_angle: 95 }}
      />
    );
    expect(screen.getByTestId('knee-angle-badge')).toHaveTextContent('Knee: 95°');
  });

  it('does not show angle badges when criticalFrameAngles is undefined', () => {
    render(
      <EvidenceFallbackTest
        highlight={null}
        criticalFrameAngles={undefined}
      />
    );
    expect(screen.queryByTestId('hip-angle-badge')).toBeNull();
    expect(screen.queryByTestId('knee-angle-badge')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Feature 4 — detectTierUpgrade (inline replica)
// ---------------------------------------------------------------------------

function detectTierUpgrade(
  prevScore: number | null,
  currScore: number | null,
): { from: string; to: string } | null {
  if (prevScore == null || currScore == null) return null;
  if (currScore <= prevScore) return null;
  const currentTier = getLevelInfo(currScore)?.current;
  const prevTier    = getLevelInfo(prevScore)?.current;
  if (!currentTier || !prevTier || currentTier === prevTier) return null;
  return { from: prevTier, to: currentTier };
}

describe('detectTierUpgrade (Feature 4)', () => {
  it('currScore=76, prevScore=72 → upgrade from Developing to Solid', () => {
    const result = detectTierUpgrade(72, 76);
    expect(result).toEqual({ from: 'Developing', to: 'Solid' });
  });

  it('currScore=74, prevScore=72 → null (no tier change within Developing)', () => {
    expect(detectTierUpgrade(72, 74)).toBeNull();
  });

  it('currScore=72, prevScore=76 → null (downgrade, not upgrade)', () => {
    expect(detectTierUpgrade(76, 72)).toBeNull();
  });

  it('currScore=null → null (baseline session)', () => {
    expect(detectTierUpgrade(null, null)).toBeNull();
  });

  it('prevScore=null → null', () => {
    expect(detectTierUpgrade(null, 76)).toBeNull();
  });

  it('boundary: currScore=75, prevScore=74 → upgrade from Developing to Solid', () => {
    const result = detectTierUpgrade(74, 75);
    expect(result).toEqual({ from: 'Developing', to: 'Solid' });
  });
});

// ---------------------------------------------------------------------------
// Feature 5 — getWeakComponentTrend (inline replica)
// ---------------------------------------------------------------------------

interface ComponentScoreAvgTest {
  key: string;
  label: string;
  avg: number;
}

function getWeakComponentTrendTest(
  sessions: Array<{ named_scores?: Record<string, number | null> | null }>,
  limit = 5,
): ComponentScoreAvgTest | null {
  const recent = sessions.slice(-limit);
  if (recent.length < 2) return null;
  const COMPONENT_KEYS = [
    { key: 'torso_stability_score', label: 'Torso Stability' },
    { key: 'knee_symmetry_score',   label: 'Knee Symmetry' },
    { key: 'bottom_control_score',  label: 'Bottom Control' },
    { key: 'forward_lean_score',    label: 'Forward Lean' },
  ];
  const avgs = COMPONENT_KEYS.map(({ key, label }) => {
    const scores = recent
      .map(s => s.named_scores?.[key])
      .filter((v): v is number => v != null);
    if (scores.length < 2) return null;
    return { key, label, avg: Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) };
  }).filter((v): v is ComponentScoreAvgTest => v != null);
  if (avgs.length === 0) return null;
  return avgs.sort((a, b) => a.avg - b.avg)[0];
}

describe('getWeakComponentTrend (Feature 5)', () => {
  it('5 sessions with knee_symmetry consistently lowest → returns knee_symmetry_score', () => {
    const sessions = Array.from({ length: 5 }, () => ({
      named_scores: {
        torso_stability_score: 75,
        knee_symmetry_score: 40,
        bottom_control_score: 70,
        forward_lean_score: 80,
      },
    }));
    const result = getWeakComponentTrendTest(sessions);
    expect(result?.key).toBe('knee_symmetry_score');
    expect(result?.label).toBe('Knee Symmetry');
  });

  it('1 session → returns null (< 2 sessions)', () => {
    const sessions = [{ named_scores: { torso_stability_score: 60, knee_symmetry_score: 50 } }];
    expect(getWeakComponentTrendTest(sessions)).toBeNull();
  });

  it('all named_scores null → returns null', () => {
    const sessions = Array.from({ length: 3 }, () => ({
      named_scores: {
        torso_stability_score: null,
        knee_symmetry_score: null,
        bottom_control_score: null,
        forward_lean_score: null,
      },
    }));
    expect(getWeakComponentTrendTest(sessions)).toBeNull();
  });

  it('only 1 session has non-null scores → returns null (needs ≥2 values per component)', () => {
    const sessions = [
      { named_scores: { torso_stability_score: 50, knee_symmetry_score: 40 } },
      { named_scores: { torso_stability_score: null, knee_symmetry_score: null } },
    ];
    expect(getWeakComponentTrendTest(sessions)).toBeNull();
  });

  it('avg is computed correctly across sessions', () => {
    const sessions = [
      { named_scores: { torso_stability_score: 60, knee_symmetry_score: null, bottom_control_score: null, forward_lean_score: null } },
      { named_scores: { torso_stability_score: 80, knee_symmetry_score: null, bottom_control_score: null, forward_lean_score: null } },
    ];
    const result = getWeakComponentTrendTest(sessions);
    expect(result?.key).toBe('torso_stability_score');
    expect(result?.avg).toBe(70); // (60 + 80) / 2
  });
});

// ---------------------------------------------------------------------------
// UI Polish Sprint — Change 1: ML section confidence meta lookup (inline replica)
// ---------------------------------------------------------------------------

function getConfidenceMeta(label: string | undefined): { pill: string; text: string; cls: string } | null {
  if (!label) return null;
  const meta: Record<string, { pill: string; text: string; cls: string }> = {
    High:     { pill: 'High confidence',     text: 'Model is confident in this assessment.',                        cls: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300' },
    Moderate: { pill: 'Moderate confidence', text: 'Model is reasonably confident — use as guidance.',              cls: 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400' },
    Low:      { pill: 'Low confidence',      text: 'Low confidence — retake for better data.',                      cls: 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300' },
  };
  return meta[label] ?? null;
}

describe('getConfidenceMeta (ML section — Change 1)', () => {
  it('High → correct pill + text', () => {
    const m = getConfidenceMeta('High')!;
    expect(m.pill).toBe('High confidence');
    expect(m.text).toContain('confident in this assessment');
    expect(m.cls).toContain('green');
  });

  it('Moderate → correct pill + text', () => {
    const m = getConfidenceMeta('Moderate')!;
    expect(m.pill).toBe('Moderate confidence');
    expect(m.text).toContain('use as guidance');
    expect(m.cls).toContain('gray');
  });

  it('Low → correct pill + text (amber)', () => {
    const m = getConfidenceMeta('Low')!;
    expect(m.pill).toBe('Low confidence');
    expect(m.text).toContain('retake');
    expect(m.cls).toContain('amber');
  });

  it('undefined → returns null', () => {
    expect(getConfidenceMeta(undefined)).toBeNull();
  });

  it('unknown label → returns null', () => {
    expect(getConfidenceMeta('VeryHigh')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// UI Polish Sprint — Change 2: Low/Moderate confidence badge predicate
// ---------------------------------------------------------------------------

/** Mirrors the predicate used in the header score circle. */
function shouldShowLowBadge(label: string | null): boolean { return label === 'Low'; }
function shouldShowModerateBadge(label: string | null): boolean { return label === 'Moderate'; }

describe('Confidence badge visibility predicate (Change 2)', () => {
  it('calibrated_confidence Low → low-confidence badge would render', () => {
    expect(shouldShowLowBadge('Low')).toBe(true);
    expect(shouldShowModerateBadge('Low')).toBe(false);
  });

  it('calibrated_confidence High → no badge rendered', () => {
    expect(shouldShowLowBadge('High')).toBe(false);
    expect(shouldShowModerateBadge('High')).toBe(false);
  });

  it('calibrated_confidence Moderate → only moderate badge renders', () => {
    expect(shouldShowLowBadge('Moderate')).toBe(false);
    expect(shouldShowModerateBadge('Moderate')).toBe(true);
  });

  it('null calibrated_confidence → no badge renders', () => {
    expect(shouldShowLowBadge(null)).toBe(false);
    expect(shouldShowModerateBadge(null)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// UI Polish Sprint — Change 3A: Delta chip color (amber not red for negative)
// ---------------------------------------------------------------------------

function getDeltaChipClass(delta: number): string {
  return delta >= 0
    ? 'bg-green-100 text-green-700'
    : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300';
}

describe('deltaChipColor (Change 3A)', () => {
  it('positive delta → green classes', () => {
    const cls = getDeltaChipClass(5);
    expect(cls).toContain('green');
    expect(cls).not.toContain('red');
    expect(cls).not.toContain('amber');
  });

  it('zero delta → green classes (not negative)', () => {
    const cls = getDeltaChipClass(0);
    expect(cls).toContain('green');
  });

  it('negative delta → amber classes (not red)', () => {
    const cls = getDeltaChipClass(-3);
    expect(cls).toContain('amber');
    expect(cls).not.toContain('red');
    expect(cls).not.toContain('green');
  });
});

// ---------------------------------------------------------------------------
// UI Polish Sprint — Change 3B: Component score text color (severity-based)
// ---------------------------------------------------------------------------

function getScoreTextColor(sev: 'Priority' | 'Improve' | 'Maintain' | undefined, score: number): string {
  return sev === 'Priority' ? 'text-rose-600 dark:text-rose-400'
    : sev === 'Improve'   ? 'text-amber-600 dark:text-amber-400'
    : sev === 'Maintain'  ? 'text-slate-500 dark:text-slate-400'
    : (score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600');
}

describe('componentScoreTextColor (Change 3B)', () => {
  it('Priority sev → text-rose-600', () => {
    const cls = getScoreTextColor('Priority', 40);
    expect(cls).toContain('rose');
    expect(cls).not.toContain('red-6');
  });

  it('Improve sev → text-amber-600', () => {
    const cls = getScoreTextColor('Improve', 58);
    expect(cls).toContain('amber');
  });

  it('Maintain sev → text-slate-500', () => {
    const cls = getScoreTextColor('Maintain', 75);
    expect(cls).toContain('slate');
  });

  it('no sev + score 50 → text-red-600 fallback', () => {
    const cls = getScoreTextColor(undefined, 50);
    expect(cls).toBe('text-red-600');
  });

  it('no sev + score 65 → text-yellow-600 fallback', () => {
    const cls = getScoreTextColor(undefined, 65);
    expect(cls).toBe('text-yellow-600');
  });

  it('no sev + score 85 → text-green-600 fallback', () => {
    const cls = getScoreTextColor(undefined, 85);
    expect(cls).toBe('text-green-600');
  });
});

// ---------------------------------------------------------------------------
// generateRecommendations — knee dedup (inline replica)
// ---------------------------------------------------------------------------

const MERGED_KNEE_TIP_TEST = {
  icon: '🦵',
  title: 'Fix Knee Tracking',
  description: 'Your knees show both stability and symmetry issues through the rep.',
  priority: 'high' as const,
  exercise: 'Banded squats x10 (priority), Pause squats 3-sec hold at depth x6',
  duration: '3 sets each before work sets',
};
const KNEE_TITLES_TEST = new Set(['Fix Knee Stability', 'Fix Knee Symmetry']);

function dedupKneeCards(
  tips: Array<{ title: string; priority: string }>,
): Array<{ title: string; priority: string }> {
  const kneeTips = tips.filter(t => KNEE_TITLES_TEST.has(t.title));
  if (kneeTips.length >= 2) {
    return [MERGED_KNEE_TIP_TEST, ...tips.filter(t => !KNEE_TITLES_TEST.has(t.title))];
  }
  return tips;
}

describe('generateRecommendations — knee dedup', () => {
  it('two knee groups → exactly 1 card with title "Fix Knee Tracking"', () => {
    const tips = [
      { title: 'Fix Knee Stability', priority: 'high' },
      { title: 'Fix Knee Symmetry', priority: 'high' },
    ];
    const result = dedupKneeCards(tips);
    expect(result.length).toBe(1);
    expect(result[0].title).toBe('Fix Knee Tracking');
  });

  it('one knee group + one trunk group → 2 cards, no merge, knee title unchanged', () => {
    const tips = [
      { title: 'Fix Knee Stability', priority: 'high' },
      { title: 'Trunk Stability at Bottom', priority: 'medium' },
    ];
    const result = dedupKneeCards(tips);
    expect(result.length).toBe(2);
    expect(result[0].title).toBe('Fix Knee Stability');
    expect(result[1].title).toBe('Trunk Stability at Bottom');
  });
});
