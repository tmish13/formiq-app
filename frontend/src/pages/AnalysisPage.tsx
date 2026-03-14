import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  CheckCircle,
  AlertTriangle,
  Target,
  TrendingUp,
  RotateCcw,
  BookOpen,
  Sparkles,
  Brain,
  ArrowLeft,
  ArrowUp,
  LoaderIcon,
  Info,
  Camera,
  X,
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';
import AppLayout from '../components/layout/AppLayout';

// DATA FLOW NOTES:
// - Form score: backend via formCheckService.getMLAnalysis() → MLAnalysisResponse
// - Backend endpoints: GET /form-checks/{id}/ml-analysis, GET /form-checks/{id}
// - Component scores: mlAnalysis.named_scores (torso_stability, knee_symmetry, bottom_control, forward_lean)
// - Exercise type: formCheck.exercise_type || formCheck.classified_exercise_slug (squat enforced by backend)
// - Working weight: formCheck.weight_kg (nullable kg, captured at recording time on RecordPage)
// - Squat session log drawer: weight+sets → addSquatSession() (squatSessions.ts)
//   + addTrainingSession() (trainingStorage.ts) for RIR-based progression engine

// Import our backend services
import { formCheckService } from '../services/formCheckService';
import { FormCheck, MLAnalysisResponse } from '../types/formCheck';
import { getCaptureQualitySummary } from '../utils/componentEligibility';
import { logBetaEvent } from '../utils/logEvent';
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerFooter,
  DrawerClose,
} from '../components/ui/drawer';
import { addSquatSession, computeSessionFromAnalysis } from '../utils/squatSessions';
import { squatSessionService } from '../services/squatSessionService';
import { addTrainingSession } from '../utils/trainingStorage';
import { TrainingSession } from '../types/training';

interface AnalysisBreakdown {
  category: string;
  score: number;
  status: 'excellent' | 'good' | 'warning' | 'poor';
  feedback: string;
  icon: string;
  improvement: string;
  keyFrames?: number[];
}

interface AIRecommendation {
  icon: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  exercise: string;
  duration: string;
}

// ---------------------------------------------------------------------------
// Score-band helpers (thresholds MUST match backend compute_score_band: 90/75/60)
// ---------------------------------------------------------------------------

/** Compute score band client-side — must stay in sync with backend scoring.py. */
const getScoreBand = (
  score: number | null,
): 'excellent' | 'good' | 'needs_work' | 'poor' | null => {
  if (score == null) return null;
  if (score >= 90) return 'excellent';
  if (score >= 75) return 'good';
  if (score >= 60) return 'needs_work';
  return 'poor';
};

const getHeaderGradient = (band: ReturnType<typeof getScoreBand>) => {
  switch (band) {
    case 'excellent': return 'from-green-600 via-emerald-600 to-green-700';
    case 'good':      return 'from-blue-500 via-blue-600 to-indigo-600';
    case 'needs_work':return 'from-amber-500 via-orange-500 to-amber-600';
    case 'poor':      return 'from-amber-600 via-orange-600 to-amber-700';
    default:          return 'from-gray-600 via-gray-700 to-gray-800'; // uncertain / no score
  }
};

const getComponentBarColor = (score: number) => {
  if (score >= 80) return 'bg-green-500';
  if (score >= 60) return 'bg-yellow-500';
  return 'bg-red-500';
};

function getComponentChip(score: number | null | undefined) {
  if (score === null || score === undefined)
    return { label: 'No data',    className: 'bg-gray-100 text-gray-500' };
  if (score >= 80) return { label: 'Strong',      className: 'bg-green-100 text-green-700' };
  if (score >= 60) return { label: 'Solid',        className: 'bg-yellow-100 text-yellow-700' };
  if (score >= 40) return { label: 'Needs work',   className: 'bg-orange-100 text-orange-700' };
  return              { label: 'Limiting',      className: 'bg-red-100 text-red-700' };
}

// ---------------------------------------------------------------------------
// Feature-insight feedback copy — keyed by top-signal feature name
// ---------------------------------------------------------------------------

const FEATURE_INSIGHT_FEEDBACK: Record<string, string> = {
  bottom_trunk_wobble:
    'Trunk sways at the bottom — brace your core harder before descending and hold tension at depth.',
  trunk_forward_lean:
    'Excessive forward lean shifts load to the lower back. Think "chest up" and keep lats engaged.',
  knee_asymmetry_mean:
    'Knees track unevenly throughout the rep. Cue "spread the floor" to keep tracking over toes.',
  bottom_knee_asymmetry:
    'Knee alignment diverges at the bottom. Slow the descent and focus on symmetrical width.',
  trunk_angle_std:
    'Torso angle varies between reps. Establish a braced, consistent spine angle before every rep.',
  left_knee_angle_std:
    'Left knee angle varies. Focus on tracking your left knee consistently over your left foot.',
  right_knee_angle_std:
    'Right knee angle varies. Focus on tracking your right knee consistently over your right foot.',
  left_hip_angle_std:
    'Left hip drive is inconsistent. Drive through both heels equally on the ascent.',
  trunk_angle_bottom_std:
    'Trunk is unstable at the bottom position. Pause for 1 second at depth to build positional strength.',
  left_knee_angle_bottom_std:
    'Left knee shifts at the bottom. Maintain width and keep knees stacked over ankles.',
  right_knee_angle_bottom_std:
    'Right knee shifts at the bottom. Keep knees stacked over ankles throughout the descent.',
};

// ---------------------------------------------------------------------------
// Signal grouping — deduplicate raw feature_insights into named categories
// (PARTS 2 & 6: one bullet / tip card per group, ordered by z-score severity)
// ---------------------------------------------------------------------------

/** Maps raw feature names from top_signals → deduplicated group key. */
const GROUPED_SIGNAL_MAP: Record<string, string> = {
  left_knee_angle_bottom_std:  'knee_instability',
  right_knee_angle_bottom_std: 'knee_instability',
  left_knee_angle_std:         'knee_instability',
  right_knee_angle_std:        'knee_instability',
  knee_asymmetry_mean:         'knee_asymmetry',
  bottom_knee_asymmetry:       'knee_asymmetry',
  bottom_trunk_wobble:         'trunk_instability',
  trunk_angle_bottom_std:      'trunk_instability',
  trunk_angle_std:             'trunk_inconsistency',
  trunk_angle_descent_std:     'trunk_inconsistency',
  trunk_angle_ascent_std:      'trunk_inconsistency',
  trunk_forward_lean:          'forward_lean',
  left_hip_angle_std:          'hip_drive',
  left_hip_angle_descent_std:  'hip_drive',
  left_hip_angle_bottom_std:   'hip_drive',
  left_hip_angle_ascent_std:   'hip_drive',
};

const GROUPED_SIGNAL_LABELS: Record<string, string> = {
  knee_instability:    'Knee instability through the rep',
  knee_asymmetry:      'Knee tracking asymmetry',
  trunk_instability:   'Trunk instability at the bottom position',
  trunk_inconsistency: 'Inconsistent trunk angle between reps',
  forward_lean:        'Excessive forward lean',
  hip_drive:           'Inconsistent hip drive',
};

/** Deduplicate top_signals into one entry per group, preserving severity order. */
const groupInsights = (
  topSignals: Array<{ name: string; z: number; message_short?: string }>,
): Array<{ group: string; label: string; z: number }> => {
  const seen = new Set<string>();
  const result: Array<{ group: string; label: string; z: number }> = [];
  for (const signal of topSignals) {
    const group = GROUPED_SIGNAL_MAP[signal.name];
    if (group && !seen.has(group)) {
      seen.add(group);
      result.push({ group, label: GROUPED_SIGNAL_LABELS[group] ?? signal.message_short ?? group, z: signal.z });
    }
  }
  return result;
};

/** Maps named_score keys to human-readable limiter labels for summary copy. */
const LIMITER_LABELS: Record<string, string> = {
  torso_stability_score: 'trunk stability',
  knee_symmetry_score:   'knee tracking',
  bottom_control_score:  'bottom position control',
  forward_lean_score:    'forward lean',
};

const _NEXT_LEVEL_NAME: Record<string, string> = {
  Beginner: 'Developing',
  Developing: 'Solid',
  Solid: 'Advanced',
  Advanced: 'Elite',
};

/** Score thresholds for each tier (must stay in sync with backend _LEVELS in scoring.py). */
const _NEXT_LEVEL_SCORE: Record<string, number> = {
  Beginner:   60,
  Developing: 75,
  Solid:      85,
  Advanced:   92,
};

// ---------------------------------------------------------------------------
// Tip cards keyed by GROUP (not raw feature name) — one card per issue cluster
// ---------------------------------------------------------------------------

interface TipCard {
  icon: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  exercise: string;
  duration: string;
}

const MERGED_KNEE_TIP: TipCard = {
  icon: '🦵',
  title: 'Fix Knee Tracking',
  description: 'Your knees show both stability and symmetry issues through the rep. Cue "spread the floor" — drive knees out over toes — and slow the eccentric to reinforce alignment at every depth.',
  priority: 'high',
  exercise: 'Banded squats x10 (priority), Pause squats 3-sec hold at depth x6',
  duration: '3 sets each before work sets',
};
const KNEE_TITLES = new Set(['Fix Knee Stability', 'Fix Knee Symmetry']);

const GROUP_TIP_MAP: Record<string, TipCard> = {
  knee_instability: {
    icon: '🦵',
    title: 'Fix Knee Stability',
    description:
      'Your knees shift during the descent. Slow the eccentric and focus on keeping knees stacked over ankles throughout the full range.',
    priority: 'high',
    exercise: 'Pause squats (3-second hold at depth), Banded squats to reinforce alignment',
    duration: '3 sets of 6 reps',
  },
  knee_asymmetry: {
    icon: '🦵',
    title: 'Fix Knee Symmetry',
    description:
      'Knees track unevenly through the rep. Cue "spread the floor" — imagine ripping the floor apart with your feet to drive knees over toes.',
    priority: 'high',
    exercise: 'Banded squats (mini-band above knees), Bodyweight box squats facing mirror',
    duration: '3 sets of 10 reps',
  },
  trunk_instability: {
    icon: '🎯',
    title: 'Trunk Stability at Bottom',
    description:
      'Trunk sways at the bottom position. Brace your core before descending and maintain that tension — do not relax at depth.',
    priority: 'high',
    exercise: 'Pause squats (3-second hold at depth), Dead bugs 3×10',
    duration: '3 sets of 5 paused reps',
  },
  trunk_inconsistency: {
    icon: '🏋️',
    title: 'Consistent Torso Angle',
    description:
      'Torso angle varies between reps. Establish a braced position before every rep — breathe at the top, brace, then descend with the same spine angle.',
    priority: 'medium',
    exercise: 'Breathing squats with deliberate reset, Pause squats at parallel',
    duration: '3 sets of 5 reps',
  },
  forward_lean: {
    icon: '⬆️',
    title: 'Reduce Forward Lean',
    description:
      'Excessive forward lean shifts load to the lower back. Think "chest up" and keep lats engaged. Often caused by ankle mobility restrictions.',
    priority: 'high',
    exercise: 'Goblet squats, Ankle mobility stretches (3 min/day), High-bar back squats',
    duration: '3 sets of 8 reps',
  },
  hip_drive: {
    icon: '💪',
    title: 'Consistent Hip Drive',
    description:
      'Hip drive is irregular across reps. Drive evenly through both heels on the ascent — avoid favouring one side.',
    priority: 'medium',
    exercise: 'Hip thrusts (bilateral then unilateral), Romanian deadlifts',
    duration: '3 sets of 10 reps',
  },
};

// ---------------------------------------------------------------------------
// computeProjectedScore — projected overall if primary limiter reaches target
// Uses the same canonical weighted average as the backend.
// ---------------------------------------------------------------------------

const COMPONENT_WEIGHTS_FE: Record<string, number> = {
  torso_stability_score: 0.30,
  knee_symmetry_score:   0.25,
  bottom_control_score:  0.25,
  forward_lean_score:    0.20,
};

// Maps a short limiter key (from primary_limiter.key) to the named_scores key.
const LIMITER_SCORE_KEY: Record<string, string> = {
  torso_stability_score: 'torso_stability_score',
  knee_symmetry_score:   'knee_symmetry_score',
  bottom_control_score:  'bottom_control_score',
  forward_lean_score:    'forward_lean_score',
  // short-form aliases
  torso_stability: 'torso_stability_score',
  knee_symmetry:   'knee_symmetry_score',
  bottom_control:  'bottom_control_score',
  forward_lean:    'forward_lean_score',
};

function computeProjectedScore(
  namedScores: Record<string, number | null>,
  limiterKey: string,
  targetValue = 75,
): number | null {
  const scoreKey = LIMITER_SCORE_KEY[limiterKey] ?? limiterKey;
  if (namedScores[scoreKey] == null) return null;
  const improved: Record<string, number | null> = {
    ...namedScores,
    [scoreKey]: Math.max(namedScores[scoreKey] as number, targetValue),
  };
  const valid = Object.entries(improved).filter(
    ([k, v]) => v != null && COMPONENT_WEIGHTS_FE[k] != null,
  );
  if (valid.length === 0) return null;
  const totalW = valid.reduce((s, [k]) => s + COMPONENT_WEIGHTS_FE[k], 0);
  const avg = valid.reduce(
    (s, [k, v]) => s + (v as number) * COMPONENT_WEIGHTS_FE[k] / totalW,
    0,
  );
  return Math.round(avg);
}

// ---------------------------------------------------------------------------
// getComponentSeverities — rank-based Priority/Improve/Maintain per component
// ---------------------------------------------------------------------------

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

const SEVERITY_CHIP: Record<string, { label: string; className: string }> = {
  Priority: { label: 'Priority', className: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300' },
  Improve:  { label: 'Improve',  className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300' },
  Maintain: { label: 'Maintain', className: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400' },
};

const SEVERITY_BAR_COLOR: Record<string, string> = {
  Priority: 'bg-red-500',
  Improve:  'bg-amber-400',
  Maintain: 'bg-slate-400',
};

// ---------------------------------------------------------------------------
// getLevelInfo — score-to-level progress metadata
// ---------------------------------------------------------------------------

function getLevelInfo(score: number | null): {
  current: string;
  next: string | null;
  nextScore: number | null;
  progressPct: number;
} | null {
  if (score == null) return null;
  let current: string;
  let prevScore: number;
  let next: string | null;
  let nextScore: number | null;

  if (score >= 92) {
    current = 'Elite'; prevScore = 92; next = null; nextScore = null;
  } else if (score >= 85) {
    current = 'Advanced'; prevScore = 85; next = 'Elite'; nextScore = 92;
  } else if (score >= 75) {
    current = 'Solid'; prevScore = 75; next = 'Advanced'; nextScore = 85;
  } else if (score >= 60) {
    current = 'Developing'; prevScore = 60; next = 'Solid'; nextScore = 75;
  } else {
    current = 'Beginner'; prevScore = 0; next = 'Developing'; nextScore = 60;
  }

  const progressPct =
    nextScore != null
      ? Math.min(100, Math.round(((score - prevScore) / (nextScore - prevScore)) * 100))
      : 100;

  return { current, next, nextScore, progressPct };
}

// ---------------------------------------------------------------------------
// Adaptive focus — localStorage: formiq-limiter-history (max 10, rolling)
// ---------------------------------------------------------------------------

interface LimiterHistoryEntry {
  id: string;
  limiterKey: string;
  score: number;
  ts: number;
}

interface AdaptiveFocusResult {
  focusKey: string;
  focusLabel: string;
  isAdapted: boolean;
  adaptedMessage?: string;
}

function loadLimiterHistory(): LimiterHistoryEntry[] {
  try {
    const raw = localStorage.getItem('formiq-limiter-history');
    if (!raw) return [];
    return JSON.parse(raw) as LimiterHistoryEntry[];
  } catch {
    return [];
  }
}

function saveLimiterHistory(entry: LimiterHistoryEntry): void {
  try {
    const history = loadLimiterHistory();
    const filtered = history.filter(h => h.id !== entry.id);
    filtered.push(entry);
    const trimmed = filtered.sort((a, b) => b.ts - a.ts).slice(0, 10);
    localStorage.setItem('formiq-limiter-history', JSON.stringify(trimmed));
  } catch {
    // localStorage may be unavailable — silently ignore
  }
}

function computeAdaptiveFocus(
  namedScores: { torso_stability_score: number | null; knee_symmetry_score: number | null; bottom_control_score: number | null; forward_lean_score: number | null } | null | undefined,
  currentId: string,
  history: LimiterHistoryEntry[],
): AdaptiveFocusResult | null {
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
  const naturalLabel = LIMITER_LABELS[naturalLimiter.key] ?? naturalLimiter.key;

  // Check last 5 past sessions (excluding current), newest first
  const past = history
    .filter(h => h.id !== currentId)
    .sort((a, b) => b.ts - a.ts)
    .slice(0, 5);

  if (past.length >= 3) {
    const streak = past.slice(0, 3);
    const allSameLimiter = streak.every(h => h.limiterKey === naturalLimiter.key);
    if (allSameLimiter) {
      const oldestInStreak = streak[2];
      const improved = naturalLimiter.score - oldestInStreak.score > 8;
      if (improved && entries.length >= 2) {
        const secondLimiter = entries[1];
        const secondLabel = LIMITER_LABELS[secondLimiter.key] ?? secondLimiter.key;
        return {
          focusKey: secondLimiter.key,
          focusLabel: secondLabel,
          isAdapted: true,
          adaptedMessage: `You've worked on ${naturalLabel} for 3 sessions. ${secondLabel.charAt(0).toUpperCase() + secondLabel.slice(1)} is now your next biggest unlock.`,
        };
      }
    }
  }

  return { focusKey: naturalLimiter.key, focusLabel: naturalLabel, isAdapted: false };
}


export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [formCheck, setFormCheck] = useState<FormCheck | null>(null);
  const [mlAnalysis, setMlAnalysis] = useState<MLAnalysisResponse | null>(null);
  const [, setLoading] = useState(false);
  const [showDetails, setShowDetails] = useState<number | null>(null);
  const [breakdown, setBreakdown] = useState<AnalysisBreakdown[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [, setModelVersion] = useState<string | null>(null);
  const [pollingTimedOut, setPollingTimedOut] = useState(false);
  const [breakdownUnavailable, setBreakdownUnavailable] = useState(false);
  const [showFirstAnalysisBanner, setShowFirstAnalysisBanner] = useState(false);
  const [adaptiveFocus, setAdaptiveFocus] = useState<AdaptiveFocusResult | null>(null);
  const [showLevelUpBanner, setShowLevelUpBanner] = useState<{ from: string; to: string } | null>(null);
  const [scorePulse, setScorePulse] = useState(false);
  const [showSquatLogDrawer, setShowSquatLogDrawer] = useState(false);
  const [logWeightLb, setLogWeightLb] = useState<number>(0);
  const [logSets, setLogSets] = useState<Array<{ reps: number }>>([
    { reps: 5 }, { reps: 5 }, { reps: 5 },
  ]);
  const [logAvgRir, setLogAvgRir] = useState<number>(2);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef<boolean>(true);
  const pollCountRef = useRef<number>(0);
  const pollDelayRef = useRef<number>(1000); // starts at 1 s, doubles each attempt
  const MAX_POLL_ATTEMPTS = 20; // max ~3 min total (1+2+4+8+15×16 s)

  useEffect(() => {
    if (id) {
      loadAnalysisData(id);
    } else {
      // No ID in URL — send user to the history list
      navigate('/analysis');
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Fire beta event when ML analysis lands with an uncertain decision
  useEffect(() => {
    if (mlAnalysis?.posture_v1?.decision === 'uncertain') {
      logBetaEvent('invalid_clip_detected', { formCheckId: id });
    }
  }, [mlAnalysis?.posture_v1?.decision, id]);

  // Set up mount tracking and clean up polling timeout when component unmounts
  useEffect(() => {
    isMountedRef.current = true;
    pollCountRef.current = 0;
    pollDelayRef.current = 1000;
    return () => {
      isMountedRef.current = false;
      if (pollingRef.current) clearTimeout(pollingRef.current);
    };
  }, []);

  const loadAnalysisData = async (formCheckId: string) => {
    // Stop any existing polling before starting fresh
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }

    try {
      setLoading(true);

      const formCheckData = await formCheckService.getFormCheck(formCheckId);
      setFormCheck(formCheckData);

      // Fetch model info (non-critical — ignore errors)
      formCheckService.getMLModelInfo()
        .then(info => setModelVersion(info.version))
        .catch(() => {
          toast({
            title: 'Model info is temporarily unavailable.',
            duration: 2000,
          });
        });

      const exerciseSlug = formCheckData.exercise_type || formCheckData.classified_exercise_slug || 'exercise';

      if (formCheckData.status === 'completed') {
        // Load ML analysis now that processing is done
        try {
          const mlData = await formCheckService.getMLAnalysis(formCheckId);
          setMlAnalysis(mlData);
          if (formCheckData.weight_kg) {
            setLogWeightLb(Math.round(formCheckData.weight_kg * 2.20462));
          }
          const fcScore = formCheckData.posture_score ?? formCheckData.score ?? null;
          // Level-up detection — fires once per formCheckId, only on score improvement crossing a tier
          if (mlData.delta && !mlData.delta.baseline_session && mlData.delta.overall_score_delta != null
              && mlData.delta.overall_score_delta > 0 && fcScore != null) {
            const prevScore = fcScore - mlData.delta.overall_score_delta;
            const currentTier = getLevelInfo(fcScore)?.current;
            const prevTier    = getLevelInfo(prevScore)?.current;
            if (currentTier && prevTier && currentTier !== prevTier) {
              const seenKey = `formiq-seen-levelup-${formCheckId}`;
              if (!localStorage.getItem(seenKey)) {
                if (isMountedRef.current) {
                  setShowLevelUpBanner({ from: prevTier, to: currentTier });
                  setScorePulse(true);
                  setTimeout(() => { if (isMountedRef.current) setScorePulse(false); }, 2000);
                }
                localStorage.setItem(seenKey, '1');
              }
            }
          }
          const generatedBreakdown = generateBreakdownFromML(mlData);
          setBreakdown(generatedBreakdown);
          const grouped = groupInsights(mlData.top_signals || []);
          setRecommendations(generateRecommendations(grouped, fcScore, exerciseSlug));
          logBetaEvent('analysis_success', { formCheckId, exercise: exerciseSlug, score: fcScore });
          if (!localStorage.getItem('formiq_first_analysis_shown')) {
            localStorage.setItem('formiq_first_analysis_shown', '1');
            setShowFirstAnalysisBanner(true);
          }
          // Adaptive focus — compute + persist natural limiter to history
          if (mlData.named_scores) {
            const historyEntries = loadLimiterHistory();
            const af = computeAdaptiveFocus(mlData.named_scores, formCheckId, historyEntries);
            setAdaptiveFocus(af);
            // Save natural limiter (lowest named_score) for streak tracking
            const naturalEntries = [
              { key: 'torso_stability_score', score: mlData.named_scores.torso_stability_score },
              { key: 'knee_symmetry_score',   score: mlData.named_scores.knee_symmetry_score },
              { key: 'bottom_control_score',  score: mlData.named_scores.bottom_control_score },
              { key: 'forward_lean_score',    score: mlData.named_scores.forward_lean_score },
            ].filter((e): e is { key: string; score: number } => e.score != null)
             .sort((a, b) => a.score - b.score);
            if (naturalEntries.length > 0) {
              saveLimiterHistory({ id: formCheckId, limiterKey: naturalEntries[0].key, score: naturalEntries[0].score, ts: Date.now() });
            }
          }
        } catch (mlError) {
          console.warn('ML analysis not available, using fallback data');
          setBreakdown(getFallbackBreakdown(formCheckData));
          setRecommendations(getFallbackRecommendations(exerciseSlug));
          logBetaEvent('analysis_failed', { formCheckId, exercise: exerciseSlug, reason: 'ml_fetch_error' });
        }
      } else if (formCheckData.status === 'pending' || formCheckData.status === 'analyzing' || formCheckData.status === 'processing') {
        // Show fallback breakdown while waiting, then poll for completion
        setBreakdown(getFallbackBreakdown(formCheckData));
        setRecommendations(getFallbackRecommendations(exerciseSlug));

        // Exponential backoff: 1 s → 2 → 4 → 8 → cap at 15 s.
        // Much lighter than fixed 3 s interval — Celery typically takes 5–30 s.
        pollDelayRef.current = 1000;

        const schedulePoll = () => {
          pollingRef.current = setTimeout(async () => {
            pollCountRef.current += 1;

            if (pollCountRef.current >= MAX_POLL_ATTEMPTS) {
              pollingRef.current = null;
              if (isMountedRef.current) setPollingTimedOut(true);
              return;
            }

            try {
              const updated = await formCheckService.getFormCheck(formCheckId);
              if (isMountedRef.current) setFormCheck(updated);

              if (updated.status === 'completed' || updated.status === 'failed') {
                pollingRef.current = null;

                if (updated.status === 'completed') {
                  const updatedSlug = updated.exercise_type || updated.classified_exercise_slug || 'exercise';
                  try {
                    const mlData = await formCheckService.getMLAnalysis(formCheckId);
                    if (isMountedRef.current) {
                      setMlAnalysis(mlData);
                      if (updated.weight_kg) {
                        setLogWeightLb(Math.round(updated.weight_kg * 2.20462));
                      }
                      const updatedScore = updated.posture_score ?? updated.score ?? null;
                      // Level-up detection — polling completion path
                      if (mlData.delta && !mlData.delta.baseline_session && mlData.delta.overall_score_delta != null
                          && mlData.delta.overall_score_delta > 0 && updatedScore != null) {
                        const prevScore = updatedScore - mlData.delta.overall_score_delta;
                        const currentTier = getLevelInfo(updatedScore)?.current;
                        const prevTier    = getLevelInfo(prevScore)?.current;
                        if (currentTier && prevTier && currentTier !== prevTier) {
                          const seenKey = `formiq-seen-levelup-${formCheckId}`;
                          if (!localStorage.getItem(seenKey)) {
                            if (isMountedRef.current) {
                              setShowLevelUpBanner({ from: prevTier, to: currentTier });
                              setScorePulse(true);
                              setTimeout(() => { if (isMountedRef.current) setScorePulse(false); }, 2000);
                            }
                            localStorage.setItem(seenKey, '1');
                          }
                        }
                      }
                      const bd = generateBreakdownFromML(mlData);
                      setBreakdown(bd);
                      const grouped = groupInsights(mlData.top_signals || []);
                      setRecommendations(generateRecommendations(grouped, updatedScore, updatedSlug));
                      logBetaEvent('analysis_success', { formCheckId, exercise: updatedSlug, score: updatedScore });
                      if (!localStorage.getItem('formiq_first_analysis_shown')) {
                        localStorage.setItem('formiq_first_analysis_shown', '1');
                        setShowFirstAnalysisBanner(true);
                      }
                      // Adaptive focus — compute + persist for polling-completion path
                      if (mlData.named_scores) {
                        const historyEntries = loadLimiterHistory();
                        const af = computeAdaptiveFocus(mlData.named_scores, formCheckId, historyEntries);
                        setAdaptiveFocus(af);
                        const naturalEntries = [
                          { key: 'torso_stability_score', score: mlData.named_scores.torso_stability_score },
                          { key: 'knee_symmetry_score',   score: mlData.named_scores.knee_symmetry_score },
                          { key: 'bottom_control_score',  score: mlData.named_scores.bottom_control_score },
                          { key: 'forward_lean_score',    score: mlData.named_scores.forward_lean_score },
                        ].filter((e): e is { key: string; score: number } => e.score != null)
                         .sort((a, b) => a.score - b.score);
                        if (naturalEntries.length > 0) {
                          saveLimiterHistory({ id: formCheckId, limiterKey: naturalEntries[0].key, score: naturalEntries[0].score, ts: Date.now() });
                        }
                      }
                    }
                  } catch {
                    if (isMountedRef.current) {
                      setBreakdown([]);
                      setRecommendations(getFallbackRecommendations(updatedSlug));
                      setBreakdownUnavailable(true);
                      logBetaEvent('analysis_failed', { formCheckId, exercise: updatedSlug, reason: 'ml_poll_error' });
                    }
                  }
                }
              } else {
                // Still processing — schedule next poll with doubled delay (cap 15 s)
                pollDelayRef.current = Math.min(pollDelayRef.current * 2, 15000);
                if (isMountedRef.current) schedulePoll();
              }
            } catch (e) {
              console.warn('Polling error:', e);
              // On network error, keep backing off and retry
              pollDelayRef.current = Math.min(pollDelayRef.current * 2, 15000);
              if (isMountedRef.current) schedulePoll();
            }
          }, pollDelayRef.current);
        };

        schedulePoll();
      } else {
        // failed or unknown status — show fallback
        setBreakdown(getFallbackBreakdown(formCheckData));
        setRecommendations(getFallbackRecommendations(exerciseSlug));
      }
    } catch (error) {
      console.error('Failed to load analysis:', error);
      toast({
        title: 'Analysis Error',
        description: 'Failed to load analysis data.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Build the form breakdown from PostureV1 named_scores + top_signals context.
   * Uses component scores (torso_stability, knee_symmetry, etc.) not legacy
   * posture_score/stability_score/depth_score fields.
   */
  const generateBreakdownFromML = (mlData: any): AnalysisBreakdown[] => {
    const named = mlData?.named_scores;
    if (!named) return [];

    const topSignalNames: string[] = (mlData?.top_signals ?? []).map((s: any) => s.name as string);

    const COMPONENT_DEFS: Array<{
      key: string;
      label: string;
      icon: string;
      feedbackKey: string;
      genericGood: string;
    }> = [
      {
        key: 'torso_stability_score',
        label: 'Torso Stability',
        icon: '🏋️',
        feedbackKey: 'trunk_forward_lean',
        genericGood: 'Torso stays upright and stable throughout the movement.',
      },
      {
        key: 'knee_symmetry_score',
        label: 'Knee Symmetry',
        icon: '🦵',
        feedbackKey: 'knee_asymmetry_mean',
        genericGood: 'Knees track symmetrically over toes — solid alignment.',
      },
      {
        key: 'bottom_control_score',
        label: 'Bottom Control',
        icon: '📐',
        feedbackKey: 'bottom_trunk_wobble',
        genericGood: 'Good control and stability at the bottom of the movement.',
      },
      {
        key: 'forward_lean_score',
        label: 'Forward Lean',
        icon: '⬆️',
        feedbackKey: 'trunk_forward_lean',
        genericGood: 'Forward lean is within an acceptable range.',
      },
    ];

    return COMPONENT_DEFS.flatMap(({ key, label, icon, feedbackKey, genericGood }) => {
      const score = named[key];
      if (score == null) return [];
      const s = Math.round(score);
      // Use specific insight copy when this feature appears in top_signals
      const hasFault = topSignalNames.includes(feedbackKey) ||
        (topSignalNames.includes('bottom_trunk_wobble') && key === 'bottom_control_score');
      const feedback = hasFault
        ? (FEATURE_INSIGHT_FEEDBACK[feedbackKey] ?? genericGood)
        : (s < 60 ? (FEATURE_INSIGHT_FEEDBACK[feedbackKey] ?? genericGood) : genericGood);
      return [{
        category: label,
        score: s,
        status: getScoreStatus(s),
        feedback,
        icon,
        improvement: '',
      }];
    });
  };

  // Returns empty array — breakdown is only shown when real ML data is available.
  const getFallbackBreakdown = (_fc: FormCheck): AnalysisBreakdown[] => [];

  /**
   * Generate tip cards from GROUPED insights (one card per issue cluster).
   * - Only shows top 2 group-deduplicated issues.
   * - Never shows strength/progressive overload when score < 85.
   * - If no groups map to tips, falls back to neutral defaults.
   */
  const generateRecommendations = (
    grouped: Array<{ group: string; label: string; z: number }>,
    score: number | null,
    exerciseType: string,
  ): AIRecommendation[] => {
    let tips: AIRecommendation[] = [];

    // Top 2 grouped issues (already severity-ordered from groupInsights)
    for (const insight of grouped.slice(0, 2)) {
      const tip = GROUP_TIP_MAP[insight.group];
      if (tip) {
        tips.push({
          icon: tip.icon,
          title: tip.title,
          description: tip.description,
          priority: tip.priority,
          exercise: tip.exercise,
          duration: tip.duration,
        });
      }
    }

    if (tips.length === 0) {
      return getFallbackRecommendations(exerciseType);
    }

    // Merge duplicate knee cards into one combined card
    const kneeTips = tips.filter(t => KNEE_TITLES.has(t.title));
    if (kneeTips.length >= 2) {
      tips = [MERGED_KNEE_TIP, ...tips.filter(t => !KNEE_TITLES.has(t.title))];
    }

    // Strength Development card — only when form is genuinely solid (score >= 85)
    // NEVER shown when score < 60 (posture_score < 60 means "poor" band)
    if (score !== null && score >= 85) {
      tips.push({
        icon: '💪',
        title: 'Strength Development',
        description: 'Your mechanics are solid — consider adding progressive overload for continued strength gains.',
        priority: 'low',
        exercise: `Weighted ${exerciseType}s or single-leg variations`,
        duration: '3 sets of 5-8 reps',
      });
    }

    // Enforce strict priority hierarchy: first tip → Priority, second → Improve, rest → Maintain.
    // This prevents multiple "Priority" badges when GROUP_TIP_MAP has multiple 'high' entries.
    return tips.map((tip, i) => ({
      ...tip,
      priority: (i === 0 ? 'high' : i === 1 ? 'medium' : 'low') as 'high' | 'medium' | 'low',
    }));
  };

  const getFallbackRecommendations = (_exerciseType: string): AIRecommendation[] => [
    {
      icon: '🦵',
      title: 'Knee Tracking',
      description: 'Focus on keeping knees tracking over toes. Try the "spread the floor" cue during descent.',
      priority: 'high',
      exercise: 'Bodyweight squats with deliberate knee focus',
      duration: '2-3 sets of 10 reps',
    },
    {
      icon: '📏',
      title: 'Depth Work',
      description: 'Work on achieving consistent parallel depth while maintaining an upright torso.',
      priority: 'medium',
      exercise: 'Goblet squats, heel elevation if needed',
      duration: '3 sets of 8 reps',
    },
  ];

  const getScoreStatus = (score: number): 'excellent' | 'good' | 'warning' | 'poor' => {
    if (score >= 90) return 'excellent';
    if (score >= 80) return 'good';
    if (score >= 60) return 'warning';
    return 'poor';
  };


  /**
   * Deterministic summary driven by score_band + worst component scores.
   * Never concatenates all four components — picks worst 2 (or 1 for excellent).
   * Only mentions forward_lean when its score < 75.
   * Appends "Key area to work on: {label}." for non-excellent bands.
   */
  const buildFormSummary = (): string => {
    const decision = mlAnalysis?.posture_v1?.decision;
    if (!decision || decision === 'uncertain') return '';

    const named = mlAnalysis?.named_scores;
    const band  = getScoreBand(overallScore);
    if (!named || !band) return '';

    const isLowConfidence =
      mlAnalysis?.calibrated_confidence?.label === 'Low' ||
      (mlAnalysis?.calibrated_confidence == null &&
        (mlAnalysis?.posture_v1?.confidence ?? 1) < 0.4);

    // Collect scored components using _score-suffixed keys for LIMITER_LABELS lookup.
    // Forward lean only included when notable. Null scores are excluded (no data).
    const candidates: Array<{ key: string; score: number }> = (
      [
        named.torso_stability_score != null
          ? { key: 'torso_stability_score', score: named.torso_stability_score } : null,
        named.knee_symmetry_score != null
          ? { key: 'knee_symmetry_score', score: named.knee_symmetry_score } : null,
        named.bottom_control_score != null
          ? { key: 'bottom_control_score', score: named.bottom_control_score } : null,
        named.forward_lean_score != null && named.forward_lean_score < 75
          ? { key: 'forward_lean_score', score: named.forward_lean_score } : null,
      ] as (null | { key: string; score: number })[]
    ).filter((c): c is { key: string; score: number } => c != null);

    // If all components missing (visibility-gated), return safe fallback
    if (candidates.length === 0) {
      return band === 'excellent'
        ? 'Strong squat mechanics. Only minor polish needed to reach peak efficiency.'
        : 'Analysis complete. Re-record with full body in frame for component-level insights.';
    }

    // Sort worst-first, take top 2
    candidates.sort((a, b) => a.score - b.score);
    const c1 = LIMITER_LABELS[candidates[0]?.key] ?? '';
    const c2 = LIMITER_LABELS[candidates[1]?.key];
    const primaryLabel = LIMITER_LABELS[candidates[0]?.key] ?? candidates[0]?.key ?? '';

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
  };

  /**
   * Scannable summary for the Overview tab — headline + 3 action-oriented bullets.
   * Driven by posture_score band, worst/best component scores, and primary_limiter.
   */
  const buildFormSummaryBullets = (): { headline: string; bullets: string[] } | null => {
    const decision = mlAnalysis?.posture_v1?.decision;
    if (!decision || decision === 'uncertain') return null;

    const named = mlAnalysis?.named_scores;
    const band  = getScoreBand(overallScore);
    if (!named || !band) return null;

    const all = (
      [
        named.torso_stability_score != null
          ? { label: 'Trunk stability',         score: named.torso_stability_score } : null,
        named.knee_symmetry_score != null
          ? { label: 'Knee alignment',          score: named.knee_symmetry_score   } : null,
        named.bottom_control_score != null
          ? { label: 'Bottom position control', score: named.bottom_control_score  } : null,
        named.forward_lean_score != null
          ? { label: 'Forward lean control',    score: named.forward_lean_score    } : null,
      ] as (null | { label: string; score: number })[]
    ).filter((c): c is { label: string; score: number } => c != null);

    if (all.length === 0) return null;

    const sorted = [...all].sort((a, b) => a.score - b.score);
    const worst  = sorted[0];
    const best   = [...sorted].sort((a, b) => b.score - a.score)[0];

    // Prefer backend primary_limiter label if available
    const limiterLabel =
      mlAnalysis?.primary_limiter?.key
        ? (LIMITER_LABELS[mlAnalysis.primary_limiter.key] ?? worst.label)
        : worst.label;

    const nextTierScore = getLevelInfo(overallScore)?.nextScore;
    const headlines: Record<string, string> = {
      excellent: 'Strong squat mechanics. Consistency is your next unlock.',
      good:      'Solid form. One focused fix can break your next tier.',
      needs_work: `Close to leveling up. Fix ${limiterLabel} to break ${nextTierScore ?? 'your next tier'}%.`,
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
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent':
        return 'text-green-600';
      case 'good':
        return 'text-blue-600';
      case 'warning':
        return 'text-yellow-600';
      case 'poor':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-l-red-500 bg-red-50 dark:bg-red-900/20';
      case 'medium':
        return 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'low':
        return 'border-l-green-500 bg-green-50 dark:bg-green-900/20';
      default:
        return 'border-l-gray-500 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  if (!formCheck) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 dark:text-gray-400 mb-4">Analysis not found</p>
          <Button onClick={() => navigate('/record')}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Record New Video
          </Button>
        </div>
      </div>
    );
  }

  // Show a terminal "failed" screen with a supportive message + "Record again" CTA
  if (formCheck.status === 'failed') {
    return (
      <AppLayout>
        <div className="pb-24" style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 24px)' }}>
          <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-4">
            <div className="flex items-center justify-between">
              <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Analysis</h1>
              <div className="w-16" />
            </div>
          </div>
          <div className="px-4 py-12 flex flex-col items-center text-center space-y-6 max-w-sm mx-auto">
            <div className="w-16 h-16 bg-amber-100 dark:bg-amber-900/20 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Analysis couldn't be completed
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
                This sometimes happens with very short clips, poor lighting, or if your full body wasn't visible. Try recording again with your complete range of motion in frame.
              </p>
            </div>
            <Button
              className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white"
              onClick={() => navigate('/record')}
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Record Again
            </Button>
            <Button variant="ghost" size="sm" onClick={() => navigate('/analysis')}>
              View History
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  // Show a live "processing" screen while Celery is still running
  if (formCheck.status === 'pending' || formCheck.status === 'analyzing' || formCheck.status === 'processing') {
    return (
      <AppLayout>
        <div className="pb-24" style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 24px)' }}>
          <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-4">
            <div className="flex items-center justify-between">
              <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Analyzing…</h1>
              <div className="w-16" />
            </div>
          </div>
          <div className="px-4 py-12 flex flex-col items-center text-center space-y-6">
            {pollingTimedOut && (
              <div className="w-full max-w-xs rounded-lg border border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-700 p-4 text-sm text-yellow-800 dark:text-yellow-200 space-y-3">
                <p>This analysis is taking longer than expected. The job may still be running in the background.</p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 border-yellow-400 text-yellow-800 dark:text-yellow-200 bg-transparent hover:bg-yellow-100 dark:hover:bg-yellow-900/30"
                    onClick={() => window.location.reload()}
                  >
                    Refresh
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 border-yellow-400 text-yellow-800 dark:text-yellow-200 bg-transparent hover:bg-yellow-100 dark:hover:bg-yellow-900/30"
                    onClick={() => navigate('/record')}
                  >
                    Record Again
                  </Button>
                </div>
              </div>
            )}
            <LoaderIcon className="w-12 h-12 animate-spin text-blue-600" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Analyzing your rep
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                This usually takes 30–60 seconds.
              </p>
            </div>
            <div className="space-y-2 text-sm text-gray-500 dark:text-gray-400 text-left w-full max-w-xs">
              {[
                'Reading your movement',
                'Identifying your mechanics',
                'Scoring your form',
                'Building your feedback',
              ].map((step, i) => (
                <div key={i} className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse flex-shrink-0" />
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  const exerciseSlug = formCheck.exercise_type || formCheck.classified_exercise_slug || 'exercise';
  // Use posture_score (PostureV1) as primary, fall back to generic score; never hardcode
  const overallScore = formCheck.posture_score ?? formCheck.score ?? null;
  const exerciseDisplayName =
    formCheck.exercise_name ||
    (exerciseSlug.charAt(0).toUpperCase() + exerciseSlug.slice(1).replace(/_/g, ' '));

  // Squat session log predicates — guard CTA + Drawer
  const isSquatAnalysis = exerciseSlug.toLowerCase().includes('squat');
  const hasComponentScores = !!(
    mlAnalysis?.named_scores &&
    mlAnalysis.posture_v1?.decision !== 'uncertain'
  );

  return (
    <AppLayout>
      <div className="pb-24" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 24px)" }}>
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-4">
        <div className="flex items-center justify-between">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Analysis Results</h1>
          <div className="w-16" />
        </div>
      </div>

      <div className="px-4 py-4 space-y-4 max-w-lg mx-auto">
        {/* Analysis Header — always visible above tabs */}
        <Card className={`bg-gradient-to-r ${getHeaderGradient(getScoreBand(overallScore))} text-white border-0`}>
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h1 className="text-xl font-bold mb-0.5">
                  {mlAnalysis?.posture_v1?.decision === 'uncertain' ? 'Analysis Unavailable' : 'Analysis Complete'}
                </h1>
                <p className="text-blue-100 text-sm">
                  {exerciseDisplayName}
                  {formCheck.created_at && (
                    <> · {new Date(formCheck.created_at).toLocaleDateString('en-US', {
                      month: 'short', day: 'numeric',
                    })}</>
                  )}
                </p>
              </div>
              <div className="text-center">
                <div className={`w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mb-1 transition-all duration-300 ${scorePulse ? 'ring-4 ring-white/40 scale-105' : ''}`}>
                  <span className="text-3xl font-bold">{overallScore !== null ? overallScore : '—'}</span>
                </div>
                <p className="text-xs text-blue-100">Form Score</p>
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.calibrated_confidence?.label === 'Low' && (
                  <div className="mt-1 bg-white/20 rounded-full px-2 py-0.5 text-center" data-testid="low-confidence-badge">
                    <p className="text-[10px] text-white font-medium leading-tight">Low confidence</p>
                    <p className="text-[9px] text-white/70 leading-tight">Retake for better accuracy</p>
                  </div>
                )}
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.calibrated_confidence?.label === 'Moderate' && (
                  <span className="mt-1 text-[9px] text-white/60 block text-center" data-testid="moderate-confidence-badge">
                    Moderate confidence
                  </span>
                )}
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && (mlAnalysis?.score_exclusions?.length ?? 0) >= 2 && (
                  <span
                    className="mt-1 inline-block text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full"
                    data-testid="low-visibility-badge"
                  >
                    Low visibility — score may be less precise
                  </span>
                )}
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && (
                  <p className="text-xs text-blue-100/70 mt-0.5">
                    {formCheck.reps != null
                      ? `${formCheck.reps} rep${formCheck.reps > 1 ? 's' : ''} analyzed`
                      : 'Single rep analysis'}
                  </p>
                )}
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.level?.current_level && (() => {
                  const currentLevel = mlAnalysis.level!.current_level!;
                  const nextLevel  = _NEXT_LEVEL_NAME[currentLevel];
                  const nextScore  = _NEXT_LEVEL_SCORE[currentLevel];
                  return nextScore != null ? (
                    <p className="text-xs text-blue-100 mt-1">
                      Next: <span className="font-semibold">{nextLevel}</span> at {nextScore}
                    </p>
                  ) : (
                    <p className="text-xs text-yellow-200 mt-1 font-semibold">Top tier reached</p>
                  );
                })()}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <p className="text-sm text-blue-100">
                {mlAnalysis?.posture_v1?.decision === 'uncertain'
                  ? 'Video could not be scored — see tips below'
                  : 'Instant AI feedback on your rep'}
              </p>
              <div className="flex items-center space-x-2 flex-wrap gap-1">
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && (
                  <Badge className="bg-green-500/20 text-green-100 border-green-400">
                    <TrendingUp className="w-3 h-3 mr-1" />
                    AI Analyzed
                  </Badge>
                )}
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.delta && !mlAnalysis.delta.baseline_session && mlAnalysis.delta.overall_score_delta != null && (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    mlAnalysis.delta.overall_score_delta >= 0
                      ? 'bg-green-100 text-green-700'
                      : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
                  }`}>
                    {mlAnalysis.delta.overall_score_delta >= 0 ? '+' : ''}
                    {mlAnalysis.delta.overall_score_delta} vs last
                  </span>
                )}
                {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.delta?.personal_best && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700">
                    Personal Best 🏆
                  </span>
                )}
              </div>
            </div>
            {/* Component-level delta chips — shown when we have a previous session to compare */}
            {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.delta && !mlAnalysis.delta.baseline_session && (() => {
              const d = mlAnalysis.delta;
              const componentDeltas = [
                { label: 'Trunk',   val: d.torso_stability_delta },
                { label: 'Knee',    val: d.knee_symmetry_delta },
                { label: 'Control', val: d.bottom_control_delta },
                { label: 'Lean',    val: d.forward_lean_delta },
              ].filter(c => c.val != null) as Array<{ label: string; val: number }>;
              if (componentDeltas.length === 0) return null;
              return (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {componentDeltas.map(c => (
                    <span key={c.label} className="text-xs px-2 py-0.5 rounded-full bg-white/20 text-white font-medium">
                      {c.label} {c.val >= 0 ? '↑' : '↓'}{Math.abs(c.val)}
                    </span>
                  ))}
                </div>
              );
            })()}
          </CardContent>
        </Card>

        {/* Capture Quality — shown when visibility is partial or poor */}
        {(() => {
          const cv = mlAnalysis?.posture_v1?.component_visibility;
          const quality = getCaptureQualitySummary(cv);
          if (quality.level === 'good') return null;
          return (
            <div className="flex items-center gap-2 px-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                quality.level === 'poor'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                  : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
              }`}>
                {quality.level === 'poor' ? 'Poor visibility' : 'Partial visibility'}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">{quality.tip}</span>
            </div>
          );
        })()}

        {/* First-analysis banner — shown once, dismissed locally */}
        {showFirstAnalysisBanner && (
          <div className="flex items-center gap-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl px-3 py-2.5">
            <Sparkles className="w-4 h-4 text-blue-500 dark:text-blue-400 flex-shrink-0" />
            <p className="text-xs text-blue-700 dark:text-blue-300 leading-snug flex-1">
              You're helping improve FormIQ. Your recordings make the model smarter.
            </p>
            <button
              onClick={() => setShowFirstAnalysisBanner(false)}
              className="p-1 text-blue-400 hover:text-blue-600 dark:hover:text-blue-200 flex-shrink-0"
              aria-label="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Level-up banner — shown once per formCheckId when score crosses a tier boundary */}
        <AnimatePresence>
          {showLevelUpBanner && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
              className="flex items-center gap-3 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-xl px-4 py-3 text-white shadow-sm"
            >
              <span className="text-xl flex-shrink-0">🔓</span>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm">Leveled up to {showLevelUpBanner.to} form!</p>
                <p className="text-xs text-white/70">New milestone unlocked</p>
              </div>
              <button
                onClick={() => setShowLevelUpBanner(null)}
                className="text-white/60 hover:text-white p-1 flex-shrink-0"
                aria-label="Dismiss"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Uncertain — compact reason card + "Record again" CTA */}
        {mlAnalysis?.posture_v1?.decision === 'uncertain' && (
          <Card className="border-0 shadow-sm border-l-4 border-l-amber-400 bg-amber-50 dark:bg-amber-900/10">
            <CardContent className="p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-amber-900 dark:text-amber-200 mb-1">Why is analysis unavailable?</p>
                  <p className="text-xs text-amber-800 dark:text-amber-300">
                    {(() => {
                      const flags = mlAnalysis?.posture_v1?.quality?.quality_flags ?? [];
                      if (flags.some((f: string) => f.includes('duration')))
                        return 'The video is too long for single-rep analysis. Record one clean squat rep — ideally 3–6 seconds.';
                      if (flags.some((f: string) => f.includes('visibility') || f.includes('body')))
                        return 'Your full body wasn\'t clearly visible during the rep. Film from a side or back angle with your full body in frame.';
                      if (flags.some((f: string) => f.includes('frame') || f.includes('motion')))
                        return 'Not enough clear movement was detected. Keep the camera steady and complete the full rep from start to finish.';
                      return 'We couldn\'t read enough pose data to score this clip. Try again: one squat rep, 3–6 seconds, side or back angle, full body visible.';
                    })()}
                  </p>
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-3 border-amber-300 dark:border-amber-600 text-amber-800 dark:text-amber-200 bg-transparent hover:bg-amber-100 dark:hover:bg-amber-900/30"
                    onClick={() => navigate('/record')}
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                    Record New Clip
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Context banners — always visible */}
        {mlAnalysis?.posture_v1?.status === 'not_supported' && (
          <Card className="border-blue-200 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-700">
            <CardContent className="p-4">
              <div className="flex items-start space-x-3">
                <Info className="w-5 h-5 text-blue-600 mt-0.5" />
                <div>
                  <p className="font-medium text-blue-800 dark:text-blue-200">AI Scoring Coming Soon</p>
                  <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
                    AI-powered form analysis for {mlAnalysis.posture_v1.exercise_type || 'this exercise'} is not yet available.
                    Currently supported: Squat.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {mlAnalysis?.posture_v1?.decision === 'uncertain' && (
          <Card className="border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 dark:border-yellow-700">
            <CardContent className="p-5">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 mb-4">
                <div className="flex items-center space-x-2 mb-3">
                  <Camera className="w-4 h-4 text-blue-600" />
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Tips for a readable clip</p>
                </div>
                <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
                  <li className="flex items-start gap-2"><span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />One squat rep — not a multi-rep set</li>
                  <li className="flex items-start gap-2"><span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />3–6 seconds from start to finish</li>
                  <li className="flex items-start gap-2"><span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />Side or back angle (not front-facing)</li>
                  <li className="flex items-start gap-2"><span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />Full body in frame, good even lighting</li>
                  <li className="flex items-start gap-2"><span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />Camera steady — use a tripod or lean it against something</li>
                </ul>
              </div>
              <p className="text-xs text-yellow-700 dark:text-yellow-400 mb-4">
                A low confidence score doesn't mean bad form — it means the video didn't give us enough to work with.
              </p>
              <Button onClick={() => navigate('/record')} className="w-full">
                <RotateCcw className="w-4 h-4 mr-2" />
                Record or Upload a New Clip
              </Button>
            </CardContent>
          </Card>
        )}

        {mlAnalysis?.posture_v1?.decision !== 'uncertain' && (() => {
          const confLabel = mlAnalysis?.calibrated_confidence?.label;
          if (confLabel === 'High') {
            // High confidence — no banner needed; score speaks for itself.
            return null;
          }
          if (confLabel === 'Low') {
            return (
              <Card className="border-amber-200 bg-amber-50 dark:bg-amber-900/10 dark:border-amber-800">
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <Info className="w-5 h-5 text-amber-600 mt-0.5" />
                    <p className="text-sm text-amber-800 dark:text-amber-200">
                      Low confidence. Camera angle or visibility may have affected accuracy. Re-record for a cleaner assessment.
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          }
          if (confLabel === 'Moderate') {
            return (
              <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
                Moderate confidence. Score reflects available pose data.
              </p>
            );
          }
          // Fallback to legacy raw confidence when calibrated_confidence not yet available
          if (confLabel == null && mlAnalysis?.posture_v1?.confidence != null) {
            if (mlAnalysis.posture_v1.confidence < 0.4) {
              return (
                <Card className="border-amber-200 bg-amber-50 dark:bg-amber-900/10 dark:border-amber-800">
                  <CardContent className="p-4">
                    <div className="flex items-start space-x-3">
                      <Info className="w-5 h-5 text-amber-600 mt-0.5" />
                      <p className="text-sm text-amber-800 dark:text-amber-200">
                        Low confidence. Camera angle or visibility may have affected accuracy. Re-record for a cleaner assessment.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              );
            }
            if (mlAnalysis.posture_v1.confidence < 0.7) {
              return (
                <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
                  Moderate confidence. Score reflects available pose data.
                </p>
              );
            }
          }
          return null;
        })()}

        {/* Three-tab results layout */}
        <Tabs
          defaultValue="overview"
          onValueChange={(value) => {
            if (value === 'tips') logBetaEvent('tips_tab_opened', { formCheckId: id });
            if (value === 'detailed') logBetaEvent('detailed_tab_opened', { formCheckId: id });
          }}
        >
          <TabsList className="w-full grid grid-cols-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="detailed">Detailed</TabsTrigger>
            <TabsTrigger value="tips">Tips</TabsTrigger>
          </TabsList>

          {/* ── OVERVIEW TAB ── */}
          <TabsContent value="overview" className="space-y-4 mt-4">
            {/* Scannable summary: headline + 3 action bullets */}
            {(() => {
              const summary = buildFormSummaryBullets();
              if (!summary) return null;
              const isLowConf =
                mlAnalysis?.calibrated_confidence?.label === 'Low' ||
                (mlAnalysis?.calibrated_confidence == null &&
                  (mlAnalysis?.posture_v1?.confidence ?? 1) < 0.4);
              return (
                <div className="space-y-2">
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg px-4 py-4 space-y-2">
                    <p className="text-sm font-semibold text-blue-900 dark:text-blue-100">
                      {summary.headline}
                    </p>
                    <ul className="space-y-1">
                      {summary.bullets.map((b, i) => (
                        <li key={i} className="text-sm text-blue-800 dark:text-blue-200 leading-relaxed">
                          {b}
                        </li>
                      ))}
                    </ul>
                  </div>
                  {/* Low-confidence disclaimer — softens strong claims when data quality was poor */}
                  {isLowConf && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 leading-relaxed px-1">
                      Some parts of this clip were hard to see clearly — treat this as guidance rather than a final verdict. Consider re-recording from the recommended angle.
                    </p>
                  )}
                </div>
              );
            })()}

            {/* Focus This Session card */}
            {mlAnalysis?.named_scores && mlAnalysis?.posture_v1?.decision !== 'uncertain' && (() => {
              const focusResult = adaptiveFocus ?? computeAdaptiveFocus(mlAnalysis.named_scores, id ?? '', loadLimiterHistory());
              if (!focusResult) return null;
              const levelInfo = getLevelInfo(overallScore);
              const nextLevelScore = mlAnalysis?.level?.percent_to_next_level != null
                ? null  // backend percent supplied — use nextScore from levelInfo
                : levelInfo?.nextScore;
              const displayNextScore = levelInfo?.nextScore ?? nextLevelScore;
              return (
                <Card className="border border-indigo-200 bg-indigo-50 dark:bg-indigo-900/20 shadow-sm">
                  <CardContent className="p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500 mb-1">
                      Focus This Session
                    </p>
                    {focusResult.isAdapted && focusResult.adaptedMessage && (
                      <p className="text-xs text-indigo-600 dark:text-indigo-400 mb-1 leading-snug">
                        {focusResult.adaptedMessage}
                      </p>
                    )}
                    <p className="font-semibold text-gray-900 dark:text-white">
                      {(LIMITER_LABELS[focusResult.focusKey] ?? focusResult.focusLabel).charAt(0).toUpperCase() +
                       (LIMITER_LABELS[focusResult.focusKey] ?? focusResult.focusLabel).slice(1)} is limiting your performance.
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-0.5">
                      Fix this to unlock {displayNextScore != null ? `${displayNextScore}%` : 'your next level'}.
                    </p>
                  </CardContent>
                </Card>
              );
            })()}

            {/* Form Breakdown */}
            <div className="space-y-3">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">Form Breakdown</h2>
              {breakdown.length === 0 ? (
                <p className="py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                  {breakdownUnavailable
                    ? 'No detailed breakdown is available yet for this analysis.'
                    : 'Breakdown will appear once analysis is complete.'}
                </p>
              ) : (() => {
                const _bySeverity = [...breakdown].sort((a, b) => a.score - b.score);
                return breakdown.map((item, index) => {
                  const rank = _bySeverity.indexOf(item);
                  const sev = rank === 0 ? 'Priority' : rank === 1 ? 'Improve' : 'Maintain';
                  return (
                    <Card key={index} className="border-0 shadow-sm">
                      <CardContent className="p-4">
                        <div
                          className="flex items-center justify-between cursor-pointer"
                          onClick={() => setShowDetails(showDetails === index ? null : index)}
                        >
                          <div className="flex items-center space-x-3">
                            {sev === 'Priority'
                              ? <AlertTriangle className="w-4 h-4 text-rose-500 flex-shrink-0" />
                              : sev === 'Improve'
                              ? <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                              : <CheckCircle className="w-4 h-4 text-slate-400 flex-shrink-0" />}
                            <div>
                              <h4 className="font-medium text-gray-900 dark:text-white">{item.category}</h4>
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {item.feedback.length > 40 && showDetails !== index
                                  ? item.feedback.substring(0, 40) + '...'
                                  : item.feedback}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className={`text-lg font-bold ${getStatusColor(item.status)}`}>{item.score}%</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-3">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${
                              sev === 'Priority' ? 'bg-red-500' :
                              sev === 'Improve'  ? 'bg-amber-400' : 'bg-slate-400'
                            }`}
                            style={{ width: `${item.score}%` }}
                          />
                        </div>
                        {showDetails === index && (
                          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                            <p className="text-sm text-gray-600 dark:text-gray-400">{item.feedback}</p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                });
              })()
              }
            </div>

            {/* Key Findings — deduplicated by group (PART 2) */}
            {mlAnalysis?.top_signals?.length > 0 && mlAnalysis.posture_v1?.decision !== 'uncertain' && (() => {
              const grouped = groupInsights(mlAnalysis.top_signals || []);
              if (grouped.length === 0) return null;
              return (
                <div className="space-y-2">
                  <h2 className="text-base font-semibold text-gray-900 dark:text-white">Key Findings</h2>
                  {grouped.map((item, i) => (
                    <div key={i} className="flex items-center space-x-3 py-1">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        i === 0 ? 'bg-rose-400' : i === 1 ? 'bg-amber-400' : 'bg-slate-300'
                      }`} />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{item.label}</span>
                    </div>
                  ))}
                </div>
              );
            })()}

            {/* Save as squat session — only for completed squat analyses with component scores */}
            {isSquatAnalysis && hasComponentScores && formCheck.status === 'completed' && (
              <Button
                variant="outline"
                className="w-full h-11 border-indigo-200 text-indigo-700 dark:border-indigo-700 dark:text-indigo-300 bg-transparent"
                onClick={() => setShowSquatLogDrawer(true)}
              >
                <BookOpen className="w-4 h-4 mr-2" />
                Save as squat session
              </Button>
            )}

            {/* Primary action buttons */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <Button
                className="h-12 bg-blue-600 hover:bg-blue-700"
                onClick={() => navigate('/record')}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                New Recording
              </Button>
              <Button
                variant="outline"
                className="h-12 bg-transparent"
                onClick={() => navigate('/progress')}
              >
                <Target className="w-4 h-4 mr-2" />
                View Progress
              </Button>
            </div>
          </TabsContent>

          {/* ── DETAILED TAB ── */}
          <TabsContent value="detailed" className="space-y-4 mt-4">
            {/* Persistent limiter warning */}
            {mlAnalysis?.primary_limiter?.persistent_limiter && (
              <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg p-3">
                Recurring issue detected: <span className="font-semibold">
                  {LIMITER_LABELS[mlAnalysis.primary_limiter.key] ?? mlAnalysis.primary_limiter.key}
                </span> has been your primary limiter for 3+ sessions. Focus here first.
              </div>
            )}
            {/* Named Scores */}
            {mlAnalysis?.named_scores && mlAnalysis.posture_v1?.decision !== 'uncertain' && mlAnalysis.posture_v1?.status !== 'not_supported' && (
              <Card className="border-0 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-base">
                    <Sparkles className="w-5 h-5 text-purple-600" />
                    <span>Component Scores</span>
                  </CardTitle>
                  <CardDescription>Higher percentages indicate better form quality in each area.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {(() => {
                    const severities = getComponentSeverities(mlAnalysis.named_scores);
                    return [
                      { key: 'torso_stability_score', label: 'Torso Stability' },
                      { key: 'knee_symmetry_score', label: 'Knee Symmetry' },
                      { key: 'bottom_control_score', label: 'Bottom Control' },
                      { key: 'forward_lean_score', label: 'Forward Lean' },
                    ].map(({ key, label }) => {
                      const score = mlAnalysis.named_scores[key];
                      const detail = mlAnalysis?.component_details?.[key];
                      const isInsufficient = detail?.status === 'insufficient_data' || score == null;
                      if (isInsufficient) {
                        return (
                          <div key={key}>
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-400 dark:text-gray-500">{label}</span>
                                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500">
                                  Insufficient data
                                </span>
                              </div>
                              <span className="text-sm text-gray-400 dark:text-gray-500">—</span>
                            </div>
                            {detail?.reason && (
                              <p className="text-[10px] text-gray-400 dark:text-gray-500 mb-1">Re-record recommended</p>
                            )}
                            <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-2" />
                          </div>
                        );
                      }
                      const sev = severities[key];
                      const barColor = sev ? (SEVERITY_BAR_COLOR[sev] ?? getComponentBarColor(score)) : getComponentBarColor(score);
                      const chip = sev ? SEVERITY_CHIP[sev] : getComponentChip(score);
                      const scoreTextColor = sev === 'Priority' ? 'text-rose-600 dark:text-rose-400'
                        : sev === 'Improve'   ? 'text-amber-600 dark:text-amber-400'
                        : sev === 'Maintain'  ? 'text-slate-500 dark:text-slate-400'
                        : (score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600');
                      return (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center space-x-2">
                              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${chip.className}`}>
                                {chip.label}
                              </span>
                            </div>
                            <span className={`text-sm font-bold ${scoreTextColor}`}>
                              {score}%
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                            <div className={`${barColor} h-2 rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
                          </div>
                        </div>
                      );
                    });
                  })()}
                </CardContent>
              </Card>
            )}

            {/* ML Confidence */}
            {mlAnalysis && mlAnalysis.posture_v1?.decision !== 'uncertain' && (mlAnalysis.calibrated_confidence || (mlAnalysis.ml_scores && Object.values(mlAnalysis.ml_scores).some(v => v != null))) && (
              <Card className="border-0 shadow-sm">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-base">
                    <Target className="w-5 h-5 text-blue-600" />
                    <span>ML Analysis Scores</span>
                  </CardTitle>
                  <CardDescription>Detailed machine learning assessment</CardDescription>
                </CardHeader>
                <CardContent>
                  {mlAnalysis.calibrated_confidence ? (() => {
                    const label = mlAnalysis.calibrated_confidence!.label;
                    const meta = {
                      High:     { text: 'Model is confident in this assessment.', cls: 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300', pill: 'High confidence' },
                      Moderate: { text: 'Model is reasonably confident — use as guidance.', cls: 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400', pill: 'Moderate confidence' },
                      Low:      { text: 'Low confidence — retake for better data.', cls: 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300', pill: 'Low confidence' },
                    }[label];
                    if (!meta) return null;
                    return (
                      <div className={`rounded-lg px-4 py-3 ${meta.cls}`}>
                        <p className="text-xs font-semibold mb-0.5">{meta.pill}</p>
                        <p className="text-xs leading-relaxed">{meta.text}</p>
                      </div>
                    );
                  })() : (
                    <p className="text-xs text-muted-foreground">Confidence data unavailable for this session.</p>
                  )}
                </CardContent>
              </Card>
            )}

            <Button
              variant="outline"
              className="w-full h-10 bg-transparent text-sm"
              onClick={() => navigate('/analysis')}
            >
              <BookOpen className="w-4 h-4 mr-2" />
              All Analyses
            </Button>
          </TabsContent>

          {/* ── TIPS TAB ── */}
          <TabsContent value="tips" className="space-y-4 mt-4">

            {/* Deterministic form summary (PART 1) */}
            {buildFormSummary() && (
              <Card className="border-0 bg-blue-50 dark:bg-blue-900/20 shadow-sm">
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <Brain className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                    <p className="text-sm text-blue-800 dark:text-blue-200 leading-relaxed">
                      {buildFormSummary()}
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Key Insights — deduplicated by group (PART 2) */}
            {mlAnalysis?.top_signals?.length > 0 && mlAnalysis?.posture_v1?.decision !== 'uncertain' && (() => {
              const grouped = groupInsights(mlAnalysis.top_signals || []);
              if (grouped.length === 0) return null;
              return (
                <div className="space-y-2">
                  <h2 className="text-base font-semibold text-gray-900 dark:text-white">Key Insights</h2>
                  {grouped.map((item, i) => (
                    <div key={i} className="flex items-start space-x-3 py-1">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 mt-1.5 ${
                        i === 0 ? 'bg-rose-400' : i === 1 ? 'bg-amber-400' : 'bg-slate-300'
                      }`} />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{item.label}</span>
                    </div>
                  ))}
                </div>
              );
            })()}

            {/* Primary Limiter — single worst component (PART 3) */}
            {mlAnalysis?.posture_v1?.decision !== 'uncertain' && mlAnalysis?.named_scores && (() => {
              const named = mlAnalysis.named_scores;
              const candidates = [
                { key: 'torso_stability', score: named.torso_stability_score, label: 'Trunk Stability',       explanation: 'Excessive sway at the bottom reduces power transfer and control.' },
                { key: 'knee_symmetry',   score: named.knee_symmetry_score,   label: 'Knee Symmetry',         explanation: 'Uneven knee tracking increases joint stress and reduces force output.' },
                { key: 'bottom_control',  score: named.bottom_control_score,  label: 'Bottom Control',        explanation: 'Instability at the bottom position limits depth and limits power development.' },
                { key: 'forward_lean',    score: named.forward_lean_score,    label: 'Forward Lean Control',  explanation: 'Excessive forward lean shifts load to the lower back, reducing efficiency.' },
              ].filter((c): c is typeof c & { score: number } => c.score != null);

              if (candidates.length === 0) return null;
              candidates.sort((a, b) => a.score - b.score);
              const limiter = candidates[0];

              const isLowConf =
                mlAnalysis?.calibrated_confidence?.label === 'Low' ||
                (mlAnalysis?.calibrated_confidence == null &&
                  (mlAnalysis?.posture_v1?.confidence ?? 1) < 0.4);
              return (
                <Card className="border border-orange-300 dark:border-orange-700 bg-orange-50 dark:bg-orange-900/20 shadow-sm">
                  <CardContent className="p-4">
                    <div className="flex items-start space-x-3">
                      <Target className="w-5 h-5 text-orange-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-orange-500 dark:text-orange-400 mb-1">
                          Primary Limiter — Biggest impact fix
                        </p>
                        <p className="font-semibold text-gray-900 dark:text-white">
                          {limiter.label} <span className="text-orange-600">({limiter.score}%)</span>
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                          {isLowConf
                            ? `${limiter.explanation} This is the most likely area to improve — though lower confidence means re-recording may refine this assessment.`
                            : `${limiter.explanation} Fixing this will have the greatest effect on your overall score.`}
                        </p>
                        {(() => {
                          if (overallScore == null || limiter.score >= 75) return null;
                          const projected = computeProjectedScore(named as Record<string, number | null>, limiter.key);
                          if (projected == null || projected <= overallScore) return null;
                          return (
                            <div className="mt-3 flex items-center gap-2 text-purple-700 dark:text-purple-300 text-sm">
                              <ArrowUp className="w-3.5 h-3.5 flex-shrink-0" />
                              <span>Fixing {limiter.label.toLowerCase()} could raise your score to ~{projected}%.</span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">Fastest path to next level.</span>
                            </div>
                          );
                        })()}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })()}

            {/* Coach Feedback — AI-generated paragraph (populated when RAG is enabled) */}
            {mlAnalysis?.feedback_text && mlAnalysis.posture_v1?.decision !== 'uncertain' && (
              <Card className="border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-950/20 shadow-sm">
                <CardContent className="p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-indigo-600 dark:text-indigo-400 flex-shrink-0" />
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
                      Coach Feedback
                    </p>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                    {mlAnalysis.feedback_text}
                  </p>
                </CardContent>
              </Card>
            )}

            {/* AI Recommendations */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Brain className="w-5 h-5 text-purple-600" />
                <h2 className="text-base font-semibold text-gray-900 dark:text-white">Personalized Recommendations</h2>
              </div>
              {mlAnalysis?.posture_v1?.decision === 'uncertain' ? (
                <Card className="border border-dashed border-gray-300 dark:border-gray-600">
                  <CardContent className="p-5 text-center space-y-3">
                    <Camera className="w-6 h-6 text-gray-400 mx-auto" />
                    <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Recommendations need a scored clip</p>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      Record one squat rep from a side or back angle, 3–6 seconds, full body in frame.
                    </p>
                    <Button size="sm" variant="outline" onClick={() => navigate('/record')}>Record New Clip</Button>
                  </CardContent>
                </Card>
              ) : (
                recommendations.map((rec, index) => (
                  <Card key={index} className={`border-l-4 ${getPriorityColor(rec.priority)} border-0 shadow-sm`}>
                    <CardContent className="p-4">
                      <div className="flex items-start space-x-3">
                        <div className="text-2xl">{rec.icon}</div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <h4 className="font-semibold text-gray-900 dark:text-white">{rec.title}</h4>
                            <Badge
                              variant="outline"
                              className={`text-xs ${
                                rec.priority === 'high'
                                  ? 'border-rose-200 text-rose-700'
                                  : rec.priority === 'medium'
                                    ? 'border-amber-200 text-amber-700'
                                    : 'border-slate-200 text-slate-500'
                              }`}
                            >
                              {rec.priority === 'high' ? 'Priority' : rec.priority === 'medium' ? 'Improve' : 'Maintain'}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 leading-relaxed">{rec.description}</p>
                          <div className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1.5">
                              Practice drills
                            </p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">{rec.exercise}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">{rec.duration}</p>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>

            {/* Next Target card */}
            <Card className="border-0 bg-blue-50 dark:bg-blue-900/20 shadow-sm">
              <CardContent className="p-4">
                <h4 className="font-semibold text-gray-900 dark:text-white mb-1">Next Target</h4>
                {(() => {
                  if (overallScore === null) {
                    return (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        Complete a valid analysis to set your next target.
                      </p>
                    );
                  }
                  // Use backend percent_to_next_level if available, else compute locally
                  const levelInfo = getLevelInfo(overallScore);
                  const backendPct = mlAnalysis?.level?.percent_to_next_level;
                  const progressPct = backendPct != null ? Math.round(backendPct * 100) : levelInfo?.progressPct;
                  const nextLevel = levelInfo?.next;
                  const nextScore = levelInfo?.nextScore;
                  const ptsAway = nextScore != null ? nextScore - overallScore : null;

                  const copy = overallScore >= 92
                    ? 'Elite tier reached — maintain this consistency.'
                    : overallScore >= 70 && overallScore < 75
                    ? `${75 - overallScore} pts to reach Solid.`
                    : overallScore >= 70
                    ? `Aim for ${nextScore ?? ''}% to reach ${nextLevel ?? 'the next level'}.`
                    : 'Focus on the key findings above before adding more weight.';

                  return (
                    <>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{copy}</p>
                      {overallScore < 92 && nextScore != null && progressPct != null && (
                        <>
                          <Progress value={progressPct} className="h-1.5 mt-2" />
                          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                            {ptsAway != null ? `${ptsAway} pts away from ${nextLevel}` : `${progressPct}% to ${nextLevel}`}
                          </p>
                        </>
                      )}
                    </>
                  );
                })()}
              </CardContent>
            </Card>

            {/* Success Banner — only shown when score genuinely excellent (≥85) */}
            {overallScore !== null && overallScore >= 85 && (
              <Card className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800">
                <CardContent className="p-4">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                      <Sparkles className="w-5 h-5 text-green-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-green-900 dark:text-green-100">Strong Mechanics</h4>
                      <p className="text-sm text-green-700 dark:text-green-200">
                        Solid technique on your {exerciseDisplayName}. Keep this up.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Action buttons */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <Button
                className="h-12 bg-blue-600 hover:bg-blue-700"
                onClick={() => navigate('/record')}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                New Recording
              </Button>
              <Button
                variant="outline"
                className="h-12 bg-transparent"
                onClick={() => navigate('/progress')}
              >
                <Target className="w-4 h-4 mr-2" />
                View Progress
              </Button>
            </div>
          </TabsContent>
        </Tabs>
      </div>
      </div>

      {/* ── Squat Session Log Drawer ── */}
      <Drawer open={showSquatLogDrawer} onOpenChange={open => { setShowSquatLogDrawer(open); if (!open) setLogAvgRir(2); }}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Log squat session</DrawerTitle>
            <DrawerDescription>
              Record your working sets to build your training history.
            </DrawerDescription>
          </DrawerHeader>

          <div className="px-4 pb-2 space-y-4">
            {/* Coaching context — forward-looking, not score-first */}
            {(mlAnalysis?.level?.current_level || mlAnalysis?.primary_limiter?.key) && (
              <div className="rounded-lg bg-muted/40 px-3 py-2.5 space-y-1.5">
                {mlAnalysis?.level?.current_level && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Current level</span>
                    <span className="text-xs font-semibold">{mlAnalysis.level.current_level}</span>
                  </div>
                )}
                {mlAnalysis?.primary_limiter?.key && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Key focus area</span>
                    <span className="text-xs font-semibold capitalize">
                      {LIMITER_LABELS[mlAnalysis.primary_limiter.key] ?? mlAnalysis.primary_limiter.key.replace(/_/g, ' ')}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Working weight */}
            <div>
              <label className="text-sm font-medium text-foreground block mb-1.5">
                Working weight (lb)
              </label>
              <input
                type="number"
                min={0}
                step={5}
                value={logWeightLb}
                onChange={e => setLogWeightLb(Math.max(0, Number(e.target.value)))}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>

            {/* Sets & reps */}
            <div>
              <label className="text-sm font-medium text-foreground block mb-1.5">
                Sets &amp; reps
              </label>
              <div className="space-y-2">
                {logSets.map((set, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-10">Set {i + 1}</span>
                    <input
                      type="number"
                      min={1}
                      step={1}
                      value={set.reps}
                      onChange={e => {
                        const updated = [...logSets];
                        updated[i] = { reps: Math.max(1, Number(e.target.value)) };
                        setLogSets(updated);
                      }}
                      className="flex-1 rounded-lg border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                    <span className="text-xs text-muted-foreground">reps</span>
                    {logSets.length > 1 && (
                      <button
                        onClick={() => setLogSets(logSets.filter((_, idx) => idx !== i))}
                        className="text-muted-foreground hover:text-foreground text-xs px-1"
                        aria-label="Remove set"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {logSets.length < 6 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-2 h-8 text-xs text-indigo-600 dark:text-indigo-400"
                  onClick={() => setLogSets([...logSets, { reps: 5 }])}
                >
                  + Add set
                </Button>
              )}
            </div>

            {/* Average RIR */}
            <div>
              <label className="text-sm font-medium text-foreground block mb-1.5">
                Average RIR for working sets (0–5)
              </label>
              <input
                type="number" min={0} max={5} step={1}
                value={logAvgRir}
                onChange={e => setLogAvgRir(Math.min(5, Math.max(0, Number(e.target.value))))}
                className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <p className="text-xs text-muted-foreground mt-1">
                0 = all out, 3 = could do ~3 more reps, 5 = very easy.
              </p>
            </div>
          </div>

          <DrawerFooter>
            <Button
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
              onClick={() => {
                if (!mlAnalysis) return;
                const isValid =
                  logWeightLb >= 0 &&
                  logSets.length >= 1 &&
                  logSets.every(s => s.reps >= 1);
                if (!isValid) {
                  toast({ title: 'Please fill in weight and at least one set.', variant: 'destructive' });
                  return;
                }
                try {
                  const session = computeSessionFromAnalysis(
                    mlAnalysis,
                    logWeightLb,
                    logSets,
                  );
                  addSquatSession(session);
                  squatSessionService.create(session, id).catch(() => {
                    // localStorage already saved; backend failure is silent
                  });
                  const avgReps = Math.round(logSets.reduce((s, x) => s + x.reps, 0) / logSets.length);
                  const trainingSession: TrainingSession = {
                    id: (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
                      ? crypto.randomUUID() : Date.now().toString()),
                    exerciseId: 'squat',
                    date: new Date().toISOString(),
                    weightLb: logWeightLb,
                    sets: logSets.length,
                    reps: avgReps,
                    avgRir: logAvgRir,
                    formScore: overallScore ?? undefined,
                  };
                  addTrainingSession(trainingSession);
                  setShowSquatLogDrawer(false);
                  toast({
                    title: 'Squat session saved.',
                    description: 'View your coaching on the Progress page.',
                  });
                } catch {
                  toast({ title: 'Could not save session.', description: 'Storage may be unavailable.', variant: 'destructive' });
                }
              }}
            >
              Save session
            </Button>
            <DrawerClose asChild>
              <Button variant="outline" className="w-full bg-transparent">Cancel</Button>
            </DrawerClose>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </AppLayout>
  );
}