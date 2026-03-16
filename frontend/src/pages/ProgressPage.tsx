// DATA FLOW NOTES:
// - Score history: progressService.getAnalytics('squat') → AnalyticsResponse.sessions[] (backend)
// - Backend endpoints: GET /progress/analytics, GET /progress/stats (2 calls per mount)
// - Component scores per session: AnalyticsSession.named_scores (may be null for older records)
// - Local squat sessions: loadSquatSessions() from squatSessions.ts → localStorage 'formiq-squat-sessions-v1'
// Progress data sources:
// - Backend history: progressService.getAnalytics('squat') → AnalyticsResponse.sessions[] (score trend)
// - Local squat sessions: loadSquatSessions() → SquatTrainingSession[] (coaching + opportunity cards)
// - Training sessions: loadTrainingSessionsForExercise('squat') → TrainingSession[] (RIR-based progression)
// Component scores surfaced from: MLAnalysisResponse.named_scores (formCheckService → AnalysisPage)

import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, Target, Activity, Camera, Dumbbell, BarChart2, BookOpen, Info } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { useNavigate } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import {
  ComposedChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend
} from 'recharts';

import { progressService, AnalyticsResponse } from '../services/progressService';
import { logEvent } from '../utils/logEvent';
import { useAuth } from '../hooks/useAuth';
import { listSessions, listSetLogsForSession } from '../features/training/storage';
import type { Goal } from '../features/training/types';
import { EXERCISES } from '../features/training/catalog';
import { loadSquatSessions, saveSquatSessions, getBiggestOpportunityFromSessions } from '../utils/squatSessions';
import { squatSessionService } from '../services/squatSessionService';
import { trainingSessionService } from '../services/trainingSessionService';
import { SquatTrainingSession } from '../types/formCheck';
import { getUserPrefs } from '../utils/userPrefs';
import { calculateStrengthScore, patternWeight } from '../utils/strengthScore';
import type { StrengthScore } from '../utils/strengthScore';
import { averageNamedScores } from '../utils/formSkills';
import { generateStrengthTrend } from '../utils/progressStory';
import type { StrengthTrend, ExerciseTrend, TrendCategory } from '../utils/progressStory';
import { getRepresentativeSessionPerformance, classifySession } from '../utils/e1rm';
import type { SessionClassification } from '../utils/e1rm';
import { TechniqueSkillCard } from '../components/molecules/TechniqueSkillCard';

// TODO(OHP): when Overhead Press is supported, add 'ohp' here and expose the selector
// TODO(Row): when Barbell Row is supported, add 'barbell_row' here
type SupportedExercise = 'squat';

/** Coerce a backend-returned goal string into the Goal union; defaults to "general". */
const VALID_GOALS = new Set<Goal>(["strength", "hypertrophy", "general"]);
function toGoal(s: string): Goal {
  return VALID_GOALS.has(s as Goal) ? (s as Goal) : "general";
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  highlight?: boolean;
  /** Optional override for the value text color (Tailwind class string). */
  valueColor?: string;
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, highlight = false, valueColor }) => (
  <Card className={`border border-border ${highlight ? "bg-blue-50 dark:bg-blue-900/15" : "bg-card"}`}>
    <CardContent className="p-4 text-center">
      <div className="flex items-center justify-center mb-2">{icon}</div>
      <div className={`text-2xl font-bold ${valueColor ?? (highlight ? "text-blue-600 dark:text-blue-400" : "text-foreground")}`}>
        {value}
      </div>
      <div className="text-xs font-medium text-muted-foreground mt-0.5">{label}</div>
    </CardContent>
  </Card>
);

/** Consistent section label — matches the "Form Performance / Recent Performance / Weight Performance" headers. */
const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="text-xs uppercase tracking-wide font-medium text-slate-400 dark:text-slate-500 mb-2 px-0.5">
    {children}
  </div>
);

const COMP_LABELS: Record<string, string> = {
  torsoStability: 'Torso Stability',
  kneeSymmetry: 'Knee Symmetry',
  bottomControl: 'Bottom Control',
  forwardLean: 'Forward Lean',
};

const EXERCISE_PREVIEW_COUNT = 5;

/** Map a strength percentile to a labelled tier and Tailwind colour classes. */
function strengthTier(pct: number | null): { label: string; cls: string } | null {
  if (pct === null) return null;
  if (pct >= 90) return { label: 'Elite',      cls: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' };
  if (pct >= 75) return { label: 'Advanced',   cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' };
  if (pct >= 60) return { label: 'Solid',      cls: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' };
  if (pct >= 40) return { label: 'Developing', cls: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400' };
  return           { label: 'Beginner',   cls: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400' };
}

const TREND_LABELS: Record<TrendCategory, string> = {
  strong_progress:    "Strong Progress",
  improving:          "Improving",
  stable:             "Holding Steady",
  slight_decline:     "Slight Pullback",
  needs_attention:    "Watch Trend",
  insufficient_data:  "Not enough data",
};

const TREND_CHIP: Record<TrendCategory, string> = {
  strong_progress:   "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  improving:         "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  stable:            "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  slight_decline:    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  needs_attention:   "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  insufficient_data: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500",
};

const TREND_PCT_CLS: Record<TrendCategory, string> = {
  strong_progress:   "text-emerald-600 dark:text-emerald-400",
  improving:         "text-green-600 dark:text-green-400",
  stable:            "text-muted-foreground",
  slight_decline:    "text-amber-500 dark:text-amber-400",
  needs_attention:   "text-orange-600 dark:text-orange-400",
  insufficient_data: "text-muted-foreground",
};

interface WeightAwareTrend {
  label: string;
  cls: string;
}

export function computeWeightAwareTrendLabel(
  analyticsSessions: Array<{ posture_score: number | null }>,
  weightTrend: Array<{ weight_kg: number }> | undefined,
): WeightAwareTrend {
  const IMPROVING_CLS = 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300';
  const AMBER_CLS     = 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
  const GRAY_CLS      = 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400';

  let weightDelta: number | null = null;
  if (weightTrend && weightTrend.length >= 2) {
    const first = weightTrend[0].weight_kg;
    const last  = weightTrend[weightTrend.length - 1].weight_kg;
    if (first > 0) weightDelta = last / first;
  }
  const validScores = analyticsSessions.map(s => s.posture_score).filter((v): v is number => v != null);
  let scoreDelta: number | null = null;
  if (validScores.length >= 2) {
    scoreDelta = validScores[validScores.length - 1] - validScores[0];
  }

  // Case A: weight ↑≥10% + form ↓
  if (weightDelta != null && weightDelta >= 1.10 && scoreDelta != null && scoreDelta < 0)
    return { label: 'Form stressed under heavier load', cls: AMBER_CLS };
  // Case B: form dipped, no significant load increase
  if (scoreDelta != null && scoreDelta <= -5)
    return { label: 'Recent dip — refine technique', cls: AMBER_CLS };
  // Case C: form ↑ + load ↑≥5%
  if (scoreDelta != null && scoreDelta > 0 && weightDelta != null && weightDelta >= 1.05)
    return { label: 'Strong under increasing load', cls: IMPROVING_CLS };
  // Case D: stable
  return { label: 'Stable', cls: GRAY_CLS };
}

export function computeWeightLoadDelta(
  weightTrend: Array<{ weight_kg: number }> | undefined,
): { value: string; positive: boolean | null } | null {
  if (!weightTrend || weightTrend.length < 2) return null;
  const deltaKg = weightTrend[weightTrend.length - 1].weight_kg - weightTrend[0].weight_kg;
  const deltaLb = Math.round(deltaKg * 2.20462);
  if (Math.abs(deltaKg) <= 2) return { value: 'Stable', positive: null };
  return { value: deltaLb > 0 ? `+${deltaLb} lb` : `${deltaLb} lb`, positive: deltaLb > 0 };
}

export function buildOpportunityBody(
  weakLabel: string,
  sessionCount: number,
  avg: number,
  analyticsSessions: Array<{ posture_score: number | null }>,
  weightTrend: Array<{ weight_kg: number }> | undefined,
): { mainText: string; causalText: string | null } {
  const mainText = `${weakLabel} has been your weakest area over your last ${sessionCount} sessions (avg ${avg}%). Improving this moves your total score the fastest.`;

  const validScores = analyticsSessions.map(s => s.posture_score).filter((v): v is number => v != null);
  const scoreDelta = validScores.length >= 2 ? validScores[validScores.length - 1] - validScores[0] : null;
  const wt = weightTrend ?? [];
  const wtDelta = wt.length >= 2 && wt[0].weight_kg > 0 ? wt[wt.length - 1].weight_kg / wt[0].weight_kg : null;

  if (wtDelta != null && wtDelta >= 1.10 && scoreDelta != null && scoreDelta < 0 && avg < 70) {
    return { mainText, causalText: `Heavier load is exposing weaknesses in ${weakLabel.toLowerCase()}. Refine technique at this weight before pushing higher.` };
  }
  return { mainText, causalText: null };
}

/**
 * Maps sessions-in-14-days to a user-friendly frequency label.
 * Avoids negative words like "Inconsistent" in favour of directional wording.
 */
function frequencyLabel(sessions14d: number): string {
  if (sessions14d >= 7) return "High frequency";
  if (sessions14d >= 4) return "Consistent training";
  if (sessions14d >= 2) return "Building consistency";
  return "Very low frequency";
}

/**
 * Short coaching label for a recent workout card.
 * Based on avg RIR of the primary exercise and the e1RM delta.
 */
function getSessionInterpretation(
  avgRIR: number | null,
  deltaE1RM: number | null,
  hasPrior: boolean,
): string {
  if (!hasPrior) return "Baseline session";
  if (avgRIR === null) return "";
  if (deltaE1RM !== null && deltaE1RM > 0) {
    return avgRIR <= 2 ? "Good overload session" : "Strength up — more in the tank";
  }
  if (avgRIR < 1.5) return "Hard effort — hold before increasing";
  if (avgRIR >= 3)  return "Comfortable — ready to push more";
  if (deltaE1RM !== null && deltaE1RM < 0) return "Tough session — monitor trend";
  return "Solid session";
}

export default function ProgressPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();

  // selectedExercise is 'squat' for now; swap to state + selector when OHP/Row are ready
  const selectedExercise: SupportedExercise = 'squat';

  const [, setLoading] = useState(false);
  const [progressStats, setProgressStats] = useState<any>(null);
  const [currentStreak, setCurrentStreak] = useState(0);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [squatSessions, setSquatSessions] = useState<SquatTrainingSession[]>([]);
  const [progressTab, setProgressTab] = useState<"strength" | "form">("strength");
  const [showAllExercises, setShowAllExercises] = useState(false);
  const [showAllSessions, setShowAllSessions] = useState(false);

  // Scroll to top when switching tabs so the new content header is visible
  const handleTabChange = (t: "strength" | "form") => {
    setProgressTab(t);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  useEffect(() => {
    loadProgressData();
  }, []);

  const BACKFILL_KEY = 'formiq-squat-backfill-v1';

  useEffect(() => {
    squatSessionService.list()
      .then(backendSessions => {
        if (backendSessions.length === 0 && !localStorage.getItem(BACKFILL_KEY)) {
          const local = loadSquatSessions();
          if (local.length > 0) {
            localStorage.setItem(BACKFILL_KEY, 'done'); // set BEFORE posting (prevents double-run)
            Promise.allSettled(local.map(s => squatSessionService.create(s)))
              .then(() => squatSessionService.list())
              .then(refreshed => {
                setSquatSessions(refreshed);
                saveSquatSessions(refreshed);
              })
              .catch(() => {});
          }
        }
        // Show backend data if available, otherwise keep localStorage data visible
        if (backendSessions.length > 0) {
          setSquatSessions(backendSessions);
          saveSquatSessions(backendSessions);
        } else {
          setSquatSessions(loadSquatSessions());
        }
      })
      .catch(() => {
        setSquatSessions(loadSquatSessions()); // offline fallback
      });
  }, []);


  const loadProgressData = async () => {
    try {
      setLoading(true);
      const stats = await progressService.getProgressStats();
      setProgressStats(stats);
      setCurrentStreak(stats.currentStreak ?? 0);
    } catch (error) {
      console.warn('Failed to load progress stats:', error);
      logEvent('progress_load_failed', { error: String(error) });
      // Silent fallback — don't show a toast; the page still renders with local data
      setProgressStats({
        averageScore: 0,
        improvementRate: 0,
        totalAnalyses: 0,
        exerciseTypeBreakdown: {},
        recentTrend: 'stable',
        currentStreak: 0,
      });
    } finally {
      setLoading(false);
    }

    // Load analytics separately — non-blocking; always filter to selected exercise
    progressService.getAnalytics(selectedExercise).then(setAnalytics).catch(() => {});
  };

  const getBestScore = (): number => {
    if (formMetrics?.bestScore != null) return formMetrics.bestScore;
    if (analytics?.best_score_ever != null) return analytics.best_score_ever;
    return progressStats?.averageScore || 0;
  };

  const toLb = (kg: number | null | undefined): number | null =>
    kg == null ? null : Math.round(kg * 2.20462);

  /** Average weight (in lb) over last 5 sessions with weight data */
  const getAvgWeightLast5 = (): number | null => {
    if (!analytics?.weight_trend || analytics.weight_trend.length === 0) return null;
    const last5 = analytics.weight_trend.slice(-5);
    const sumKg = last5.reduce((acc, w) => acc + w.weight_kg, 0);
    return toLb(sumKg / last5.length);
  };

  /**
   * Human-readable coaching paragraph driven by analytics.
   * Avoids shame language; frames dips as refinement opportunities.
   */
  const getBaselineText = (): string | null => {
    const sessionCount = formMetrics?.sessionCount ?? analytics?.sessions.length ?? 0;
    if (sessionCount === 0) return null;
    if (sessionCount === 1) {
      return "Great start. Record a few more sessions to see how your form trends over time.";
    }

    const parts: string[] = [];

    // Prefer formMetrics changeVsBaseline (avg last 5 − avg first 3); fall back to API delta
    const change = formMetrics?.changeVsBaseline ?? analytics?.improvement_since_first;
    const latestLimiter = formMetrics?.latestLimiter;

    if (change != null) {
      if (change > 0) {
        parts.push(`Your squat form has improved ${change} pts vs your baseline — keep building on that momentum.`);
      } else if (change < 0) {
        const limiterMsg = latestLimiter
          ? ` Focus on your primary limiter: ${COMP_LABELS[latestLimiter] ?? latestLimiter}.`
          : ` Focus on refining technique — especially your primary limiter.`;
        parts.push(`Your recent sessions are trending below your baseline.${limiterMsg} Small improvements here translate into stronger lifts.`);
      } else {
        parts.push(`Your squat form score is holding steady vs your baseline.`);
      }
    }

    // Surface the primary limiter explicitly when form is steady or improving
    if (latestLimiter && (change == null || change >= 0)) {
      const limiterLabel = COMP_LABELS[latestLimiter] ?? latestLimiter;
      parts.push(`Primary limiter: ${limiterLabel}.`);
    }

    // Weight-load context from backend analytics
    const wt = analytics?.weight_trend ?? [];
    const scoreSessions = analytics?.sessions ?? [];
    const validScores = scoreSessions.map(s => s.posture_score).filter((v): v is number => v != null);
    const scoreDelta = validScores.length >= 2 ? validScores[validScores.length - 1] - validScores[0] : null;
    const wtDelta = wt.length >= 2 && wt[0].weight_kg > 0 ? wt[wt.length - 1].weight_kg / wt[0].weight_kg : null;
    if (wtDelta != null && wtDelta >= 1.10 && scoreDelta != null && scoreDelta < 0) {
      parts.push('Heavier load is likely exposing technique weaknesses. Refine form at this weight before pushing higher.');
    }

    // Personal best callout — show weight when available from local sessions
    const bestScore = formMetrics?.bestScore ?? analytics?.best_score_ever;
    const bestWeight = formMetrics?.prSession?.workingWeight;
    if (bestScore != null && bestWeight != null) {
      parts.push(`Personal best: ${bestScore}% at ${bestWeight} lb.`);
    } else if (bestScore != null && analytics?.best_weight != null) {
      parts.push(`Personal best: ${bestScore}% at ${toLb(analytics.best_weight)} lb.`);
    } else if (bestScore != null) {
      parts.push(`Best score: ${bestScore}%.`);
    }

    // Avg last 5
    const avgLast5 = formMetrics?.avgLast5 ?? analytics?.avg_last_5;
    if (avgLast5 != null) {
      parts.push(`Average over last 5 sessions: ${avgLast5}%.`);
    }

    return parts.length > 0 ? parts.join(' ') : null;
  };

  // Backend-aware session list with inline sets. Initialized from localStorage
  // synchronously (no blank flash); upgraded to backend data after fetch.
  const [loadedSessions, setLoadedSessions] = useState(() =>
    listSessions().map((s) => ({
      id: s.id,
      startedAt: s.startedAt,
      goal: s.goal,
      sets: listSetLogsForSession(s.id),
    }))
  );

  // Hydrate loadedSessions from backend.
  // Re-runs when isAuthenticated transitions to true (e.g. after logout → login).
  // Using [] alone caused the fetch to silently fail with no retry on re-login.
  useEffect(() => {
    if (!isAuthenticated) return;
    trainingSessionService.list().then((records) => {
      if (records.length > 0) {
        setLoadedSessions(
          records.map((r) => ({
            id: r.id,
            startedAt: r.started_at,
            goal: toGoal(r.goal),
            sets: r.sets_json,
          }))
        );
      }
      // else: backend empty — keep localStorage fallback already in state
    }).catch(() => {});
  }, [isAuthenticated]);

  useEffect(() => {
    const refresh = () => {
      setSquatSessions(loadSquatSessions());
      // Refresh backend training sessions
      trainingSessionService.list().then((records) => {
        if (records.length > 0) {
          setLoadedSessions(
            records.map((r) => ({
              id: r.id,
              startedAt: r.started_at,
              goal: toGoal(r.goal),
              sets: r.sets_json,
            }))
          );
        } else {
          setLoadedSessions(
            listSessions().map((s) => ({
              id: s.id,
              startedAt: s.startedAt,
              goal: s.goal,
              sets: listSetLogsForSession(s.id),
            }))
          );
        }
      }).catch(() => {});
      // Silently refresh backend analytics so backend stats don't stay stale
      progressService.getProgressStats()
        .then(stats => { setProgressStats(stats); setCurrentStreak(stats.currentStreak ?? 0); })
        .catch(() => {});
      progressService.getAnalytics(selectedExercise).then(setAnalytics).catch(() => {});
    };
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener('focus', refresh);
    return () => {
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener('focus', refresh);
    };
  }, []);

  const lastFourSessions = useMemo(() => squatSessions.slice(0, 4), [squatSessions]);
  const biggestOpportunity = useMemo(
    () => getBiggestOpportunityFromSessions(squatSessions),
    [squatSessions],
  );

  /**
   * Normalized form analysis sessions sorted chronologically (oldest first).
   * Single source of truth for all Form Analysis tab metrics.
   * Fields map directly to the spec: exerciseId, formScore, workingWeight, timestamp, limiter.
   */
  const formAnalysisSessions = useMemo(() =>
    [...squatSessions]
      .map(s => ({
        id: s.id,
        exerciseId: s.exercise as string,
        formScore: s.overallScore,
        workingWeight: s.workingWeight,
        timestamp: s.date,
        limiter: s.primaryLimiter as string | undefined,
      }))
      .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
    [squatSessions],
  );

  /**
   * Derived form metrics computed from formAnalysisSessions.
   * Updates automatically whenever squatSessions state changes.
   */
  const formMetrics = useMemo(() => {
    const sessions = formAnalysisSessions;
    if (!sessions.length) return null;

    // Best score + the session where it occurred (for "Form PR at X lb" display)
    const bestScore = Math.max(...sessions.map(s => s.formScore));
    const prSession = sessions.find(s => s.formScore === bestScore) ?? null;

    // Avg last 5 — sessions are already oldest-first; slice from end
    const last5 = sessions.slice(-5);
    const avgLast5 = Math.round(last5.reduce((a, s) => a + s.formScore, 0) / last5.length);

    // Baseline: average of the first 3 sessions
    const first3 = sessions.slice(0, 3);
    const baseline = Math.round(first3.reduce((a, s) => a + s.formScore, 0) / first3.length);

    // Change vs baseline (only meaningful once last5 and first3 are distinct windows)
    const changeVsBaseline = avgLast5 - baseline;

    // Most recent session's primary limiter for coaching copy
    const latestLimiter = sessions[sessions.length - 1]?.limiter ?? null;

    return { bestScore, prSession, avgLast5, baseline, changeVsBaseline, latestLimiter, sessionCount: sessions.length };
  }, [formAnalysisSessions]);
  const strengthScore = useMemo<StrengthScore>(
    () => {
      const prefs = getUserPrefs();
      // Prefer backend-sourced values from Redux user; fall back to local prefs
      const bwKg = user?.weight_kg ?? prefs.weightKg;
      const age = user?.age ?? prefs.age;
      // Pass backend-hydrated sessions so score survives logout/login
      return calculateStrengthScore(bwKg, age, loadedSessions);
    },
    [user, loadedSessions],
  );

  const strengthTrend = useMemo<StrengthTrend>(
    () => generateStrengthTrend(loadedSessions),
    [loadedSessions],
  );

  /** True when neither the backend user nor local prefs have body weight set. */
  const missingBodyweight = useMemo(() => {
    const prefs = getUserPrefs();
    return !user?.weight_kg && !prefs.weightKg;
  }, [user]);

  /** Total working sets ever logged — used in the Strength Score "Based on N sets" sub-label. */
  const totalWorkingSets = useMemo(() =>
    loadedSessions.reduce((total, sess) => {
      return total + sess.sets.filter(s => s.setType === "working" && s.weightLb > 0 && s.reps > 0).length;
    }, 0),
    [loadedSessions],
  );

  const latestNamedScores = useMemo(() => {
    if (!analytics?.sessions?.length) return null;
    return averageNamedScores(analytics.sessions);
  }, [analytics]);

  const workoutStats = useMemo(() => {
    const sessions = loadedSessions; // backend sessions when available, localStorage fallback
    if (!sessions.length) return null;
    const now = Date.now();
    const weekMs = 7 * 24 * 60 * 60 * 1000;
    const sessionsThisWeek = sessions.filter(
      (s) =>
        now - new Date(s.startedAt).getTime() < weekMs &&
        s.sets.some((sl) => sl.reps > 0),
    ).length;

    // Single pass over ALL sessions to compute session-level e1RM per exercise.
    // Used for both the recent-card display and delta-vs-prior-session computation.
    type SessData = {
      sess: typeof sessions[0];
      totalSets: number;
      exerciseNames: string;
      sessE1RMs: Record<string, number>;
      topSets: Record<string, { weightLb: number; reps: number; rir?: number; avgRIR: number | null }>;
    };

    const allData: SessData[] = sessions.map((sess) => {
      const sets = sess.sets;
      const working = sets.filter(
        (s) => s.setType === "working" && s.weightLb > 0 && s.reps > 0,
      );
      const exIds = Array.from(new Set(working.map((s) => s.exerciseId)));
      const exNames = exIds.map((id) => EXERCISES.find((e) => e.id === id)?.name ?? id);
      const exerciseNames =
        exNames.length > 3
          ? `${exNames.slice(0, 3).join(', ')} +${exNames.length - 3} more`
          : exNames.join(', ');

      const sessE1RMs: Record<string, number> = {};
      const topSets: Record<string, { weightLb: number; reps: number; rir?: number; avgRIR: number | null }> = {};

      for (const exId of exIds) {
        const perf = getRepresentativeSessionPerformance(sets, exId);
        if (perf.sessionE1RM === null) continue;
        sessE1RMs[exId] = perf.sessionE1RM;
        if (perf.sessionTopSet) {
          topSets[exId] = {
            weightLb: perf.sessionTopSet.weightLb,
            reps: perf.sessionTopSet.reps,
            rir: perf.sessionTopSet.rir,
            avgRIR: perf.sessionAvgRIR,
          };
        }
      }

      return { sess, totalSets: working.length, exerciseNames, sessE1RMs, topSets };
    });

    // Per-exercise all-time peak top weight — used for deload detection.
    // A session is a deload if the top weight is ≤ 75% of the exercise's all-time best.
    // Per-exercise all-time peak top weight — used by classifySession() for deload detection.
    const exercisePeakWeights: Record<string, number> = {};
    for (const d of allData) {
      for (const [exId, ts] of Object.entries(d.topSets)) {
        exercisePeakWeights[exId] = Math.max(exercisePeakWeights[exId] ?? 0, ts.weightLb);
      }
    }

    // Build enriched session cards for all sessions with working sets.
    // allData is newest-first; index i+1, i+2… are older sessions for delta lookup.
    const recentSessions = allData
      .map((d, idx) => {
        if (!d.totalSets) return null;
        const exIds = Object.keys(d.sessE1RMs);
        if (!exIds.length) return null;

        // Primary exercise: highest patternWeight, then highest e1RM as tiebreaker
        const primaryId = [...exIds].sort((a, b) => {
          const wA = patternWeight(EXERCISES.find((e) => e.id === a)?.movementPattern ?? "");
          const wB = patternWeight(EXERCISES.find((e) => e.id === b)?.movementPattern ?? "");
          if (wB !== wA) return wB - wA;
          return (d.sessE1RMs[b] ?? 0) - (d.sessE1RMs[a] ?? 0);
        })[0];

        // Delta: find the most recent prior session that also contains this exercise
        let prevE1RM: number | null = null;
        let prevSessIdx = -1;
        for (let j = idx + 1; j < allData.length; j++) {
          const v = allData[j].sessE1RMs[primaryId];
          if (v != null) { prevE1RM = v; prevSessIdx = j; break; }
        }

        // Delta guard: only surface when the comparison is recent enough
        // (within 8 sessions back, OR the prior session is within 45 days)
        let guardedDeltaE1RM: number | null = null;
        if (prevE1RM !== null && prevSessIdx !== -1) {
          const idxGap = prevSessIdx - idx;
          const daysDiff =
            (new Date(d.sess.startedAt).getTime() -
              new Date(allData[prevSessIdx].sess.startedAt).getTime()) /
            (1000 * 60 * 60 * 24);
          if (idxGap <= 8 || daysDiff <= 45) {
            guardedDeltaE1RM = Math.round(d.sessE1RMs[primaryId] - prevE1RM);
          }
        }

        const ex = EXERCISES.find((e) => e.id === primaryId);
        const topSet = d.topSets[primaryId];

        // Classify session using top weight vs all-time best + RIR:
        //   "light"     → intentional deload/technique: hide e1RM delta, show coaching note
        //   "hard_drop" → heavy effort but lighter weight (bad day/fatigue): keep delta
        //   "normal"    → regular session
        const peakWeight = exercisePeakWeights[primaryId] ?? 0;
        const currentTopWeight = topSet?.weightLb ?? 0;
        const classification: SessionClassification = classifySession(
          currentTopWeight, peakWeight, topSet?.avgRIR ?? null,
        );
        const isDeload = classification === "light";
        const dropPct = classification !== "normal"
          ? Math.round((1 - currentTopWeight / peakWeight) * 100)
          : 0;

        return {
          id: d.sess.id,
          date: d.sess.startedAt,
          goal: d.sess.goal,
          exerciseNames: d.exerciseNames,
          totalSets: d.totalSets,
          primaryExercise: topSet
            ? {
                exerciseName: ex?.name ?? primaryId,
                topSet,
                sessionE1RM: d.sessE1RMs[primaryId],
                isDeload,
                sessionClassification: classification,
                deltaE1RM: isDeload ? null : guardedDeltaE1RM,
                deltaLabel: isDeload
                  ? "Light session — recovery or technique focus"
                  : guardedDeltaE1RM === null
                    ? prevE1RM === null
                      ? "First tracked session"
                      : "No recent comparison"
                    : null,
                avgRIR: topSet.avgRIR,
                interpretation: isDeload
                  ? `${dropPct}% below your best`
                  : classification === "hard_drop"
                  ? "Hard effort — below typical load"
                  : getSessionInterpretation(topSet.avgRIR, guardedDeltaE1RM, prevE1RM !== null),
              }
            : null,
        };
      })
      .filter((s): s is NonNullable<typeof s> => s !== null);

    return { totalSessions: recentSessions.length, sessionsThisWeek, recentSessions };
  }, [loadedSessions]);

  const hasData = progressStats && progressStats.totalAnalyses > 0;
  // True only when there are genuinely no squat records in either source.
  // Used to gate the Form Analysis empty state and remove redundant CTAs.
  const formAnalysisIsEmpty =
    squatSessions.length === 0 && (!analytics || analytics.sessions.length === 0);

  return (
    <AppLayout>
      <div className="px-4 py-6 space-y-6 max-w-lg mx-auto" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 96px)" }}>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-foreground">Progress</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {hasData ? 'Track your form and strength over time.' : 'Record a squat to start tracking your progress.'}
          </p>
        </motion.div>

        {/* Progress tab switcher */}
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {(["strength", "form"] as const).map((t) => (
            <button
              key={t}
              onClick={() => handleTabChange(t)}
              className={`flex-1 rounded-md py-1.5 text-xs font-medium transition-colors ${
                progressTab === t
                  ? "bg-white dark:bg-gray-800 shadow-sm"
                  : "text-muted-foreground"
              }`}
            >
              {t === "strength" ? "Train Analysis" : "Form Analysis"}
            </button>
          ))}
        </div>

        {/* Strength tab */}
        {progressTab === "strength" && (
          <>
            {/* Strength Score */}
            {!strengthScore.isEmpty && (
              <div className="rounded-xl border px-4 py-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-1">
                      <h3 className="text-sm font-semibold">Strength Score</h3>
                      <span
                        title="Based on your recent top sets and RIR — estimated 1RM mapped to a population percentile"
                        className="text-muted-foreground cursor-help"
                      >
                        <Info className="w-3 h-3" />
                      </span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      {strengthScore.overall != null
                        ? `Stronger than ${strengthScore.overall}% of recreational lifters.`
                        : !strengthScore.hasRankableExercises
                        ? 'Machine-based lifts are excluded from percentile ranking.'
                        : 'Add bodyweight in Profile to unlock your percentile.'}
                      {totalWorkingSets > 0 && ` Based on ${totalWorkingSets} working sets.`}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    {strengthScore.overall !== null ? (
                      <>
                        <div>
                          <span className="text-xl font-bold text-primary">{strengthScore.overall}</span>
                          <span className="text-xs text-muted-foreground ml-0.5">%ile</span>
                        </div>
                        {(() => {
                          const tier = strengthTier(strengthScore.overall);
                          return tier ? (
                            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${tier.cls}`}>
                              {tier.label}
                            </span>
                          ) : null;
                        })()}
                      </>
                    ) : (
                      <span className="text-xs text-muted-foreground">Add bodyweight for score</span>
                    )}
                  </div>
                </div>
                <div className="space-y-1">
                  {(showAllExercises
                    ? strengthScore.exercises
                    : strengthScore.exercises.slice(0, EXERCISE_PREVIEW_COUNT)
                  ).map((ex) => (
                    <div key={ex.exerciseId} className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">{ex.exerciseName}</span>
                      <span className="text-xs font-medium">
                        {ex.isMachineBased
                          ? `e1RM ${ex.e1RM} lb · Machine-based`
                          : ex.score !== null
                          ? `e1RM ${ex.e1RM} lb · ${ex.score}th %ile`
                          : `e1RM ${ex.e1RM} lb`}
                      </span>
                    </div>
                  ))}
                  {strengthScore.exercises.length > EXERCISE_PREVIEW_COUNT && (
                    <button
                      onClick={() => setShowAllExercises((v) => !v)}
                      className="text-xs text-primary mt-0.5 hover:underline"
                    >
                      {showAllExercises
                        ? 'Show less'
                        : `Show all ${strengthScore.exercises.length} exercises`}
                    </button>
                  )}
                </div>
                {!strengthScore.hasBodyweight && (
                  <p className="text-xs text-muted-foreground">
                    Add your bodyweight and age in Profile → Edit Profile to unlock your strength percentile.
                  </p>
                )}
              </div>
            )}

            {/* Workout stats from training logs */}
            {workoutStats ? (
              <div className="space-y-4">

                {/* Frequency tiles */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-xl border px-4 py-3">
                    <p className="text-xs text-muted-foreground">Workouts Logged</p>
                    <p className="text-2xl font-bold">{workoutStats.totalSessions}</p>
                  </div>
                  <div className="rounded-xl border px-4 py-3">
                    <p className="text-xs text-muted-foreground">Sessions (7 days)</p>
                    <p className="text-2xl font-bold">{workoutStats.sessionsThisWeek}</p>
                  </div>
                </div>

                {/* Profile completeness tip — only when body weight is missing */}
                {missingBodyweight && (
                  <div className="flex items-start gap-2 rounded-lg bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground">
                    <Info className="w-3.5 h-3.5 mt-0.5 shrink-0 text-muted-foreground/70" />
                    <span>
                      Add your height and bodyweight in{' '}
                      <button
                        className="underline underline-offset-2 hover:text-foreground transition-colors"
                        onClick={() => navigate('/profile')}
                      >
                        Profile
                      </button>
                      {' '}to improve Strength Score accuracy.
                    </span>
                  </div>
                )}

                {/* Strength Trend */}
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Strength Trend
                  </p>

                  {strengthTrend.isEmpty ? (
                    <p className="text-xs text-muted-foreground px-0.5">
                      Log your first workout to start tracking strength trends.
                    </p>
                  ) : strengthTrend.exercises.length === 0 ? (
                    <p className="text-xs text-muted-foreground px-0.5">
                      {strengthTrend.narrative}
                    </p>
                  ) : (
                    <>
                      {strengthTrend.exercises.map((ex: ExerciseTrend) => (
                        <div
                          key={ex.exerciseId}
                          className="rounded-xl border px-4 py-3 space-y-1.5"
                        >
                          {/* Name + trend chip */}
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-medium truncate">{ex.exerciseName}</span>
                            <span className={`shrink-0 text-[10px] font-semibold px-2 py-0.5 rounded-full ${TREND_CHIP[ex.trend]}`}>
                              {TREND_LABELS[ex.trend]}
                            </span>
                          </div>

                          {/* % change — switch to absolute lb when change > 60% (avoids unrealistic-looking big numbers) */}
                          {ex.pctChange != null && (
                            <p className={`text-xs font-medium ${TREND_PCT_CLS[ex.trend]}`}>
                              {Math.abs(ex.pctChange) > 60 && ex.baselineE1RM != null
                                ? (() => {
                                    const delta = ex.recentE1RM - ex.baselineE1RM;
                                    return delta > 0
                                      ? `+${delta} lb estimated strength gain`
                                      : `${delta} lb estimated strength change`;
                                  })()
                                : `${ex.pctChange > 0 ? `+${ex.pctChange}%` : `${ex.pctChange}%`} estimated strength change`}
                            </p>
                          )}

                          {/* e1RM arrow */}
                          <p className="text-xs text-muted-foreground">
                            {ex.baselineE1RM != null && ex.baselineE1RM !== ex.recentE1RM
                              ? `e1RM: ${ex.baselineE1RM} → ${ex.recentE1RM} lb`
                              : `e1RM around ${ex.recentE1RM} lb`}
                          </p>

                          {/* Avg RIR trend */}
                          {ex.avgRIRRecent != null && (
                            <p className="text-xs text-muted-foreground">
                              {ex.avgRIRPrior != null
                                ? `Avg RIR: ${ex.avgRIRPrior} → ${ex.avgRIRRecent}`
                                : `Avg RIR: ${ex.avgRIRRecent}`}
                              {ex.rirTrend === "easier" ? " · trending easier" : ex.rirTrend === "harder" ? " · trending harder" : ""}
                            </p>
                          )}

                          {/* Frequency + consistency */}
                          <p className="text-xs text-muted-foreground">
                            {ex.frequency14d > 0
                              ? `${ex.frequency14d} session${ex.frequency14d !== 1 ? "s" : ""} / 14d`
                              : ex.frequency28d > 0
                                ? `${ex.frequency28d} session${ex.frequency28d !== 1 ? "s" : ""} / 28d`
                                : "No recent sessions"}
                            {" · "}{frequencyLabel(ex.frequency14d)}
                          </p>

                          {/* Next target */}
                          <div className="border-t border-border pt-1.5 mt-0.5">
                            <p className="text-xs font-semibold text-foreground">
                              {ex.coaching.nextTargetText}
                            </p>
                            {ex.coaching.suggestedRangeText && (
                              <p className="text-xs text-muted-foreground">
                                Suggested: {ex.coaching.suggestedRangeText}
                              </p>
                            )}
                            {ex.confidence === "low" && (
                              <p className="text-xs text-muted-foreground italic">
                                Early trend — based on limited history
                              </p>
                            )}
                          </div>
                        </div>
                      ))}

                      {/* Narrative sentence */}
                      {strengthTrend.narrative && (
                        <p className="text-xs text-muted-foreground pt-0.5 italic px-0.5">
                          {strengthTrend.narrative}
                        </p>
                      )}
                    </>
                  )}
                </div>

                {/* Recent Workouts */}
                <div className="space-y-2">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">Recent Workouts</h2>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {workoutStats.totalSessions} sessions logged
                    </p>
                  </div>
                  {(showAllSessions
                    ? workoutStats.recentSessions
                    : workoutStats.recentSessions.slice(0, 5)
                  ).map((sess) => (
                    <div key={sess.id} className="rounded-xl border px-4 py-3 space-y-2">

                      {/* Header: exercise list + date */}
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium leading-snug">
                          {sess.exerciseNames || `${sess.goal} session`}
                        </p>
                        <p className="shrink-0 text-xs text-muted-foreground">
                          {new Date(sess.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </p>
                      </div>

                      <p className="text-xs text-muted-foreground">
                        {sess.totalSets} working {sess.totalSets === 1 ? 'set' : 'sets'}
                      </p>

                      {/* Primary exercise breakdown */}
                      {sess.primaryExercise && (
                        <div className="pt-1.5 border-t border-border space-y-1">
                          <p className="text-xs font-medium text-foreground">
                            {sess.primaryExercise.exerciseName}
                          </p>
                          <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                              <p className="text-xs text-muted-foreground">
                                Top: {sess.primaryExercise.topSet.weightLb} lb × {sess.primaryExercise.topSet.reps}
                                {sess.primaryExercise.topSet.rir != null
                                  ? ` @ RIR ${sess.primaryExercise.topSet.rir}`
                                  : ''}
                              </p>
                              {/* Hide e1RM for deload sessions — the number is misleading */}
                              {!sess.primaryExercise.isDeload && (
                                <p className="text-xs text-muted-foreground">
                                  e1RM {sess.primaryExercise.sessionE1RM} lb
                                </p>
                              )}
                            </div>
                            {sess.primaryExercise.deltaE1RM != null ? (
                              <span className={`text-xs font-semibold ${
                                sess.primaryExercise.deltaE1RM > 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : sess.primaryExercise.deltaE1RM < 0
                                    ? 'text-amber-500 dark:text-amber-400'
                                    : 'text-muted-foreground'
                              }`}>
                                {sess.primaryExercise.deltaE1RM > 0
                                  ? `e1RM +${sess.primaryExercise.deltaE1RM} lb`
                                  : sess.primaryExercise.deltaE1RM === 0
                                    ? 'e1RM unchanged'
                                    : `e1RM ${sess.primaryExercise.deltaE1RM} lb`}
                              </span>
                            ) : sess.primaryExercise.deltaLabel ? (
                              <span className="text-xs text-muted-foreground italic">
                                {sess.primaryExercise.deltaLabel}
                              </span>
                            ) : null}
                          </div>
                          {/* Avg RIR + session interpretation */}
                          <div className="flex items-center justify-between gap-2">
                            {sess.primaryExercise.sessionClassification !== "light" && sess.primaryExercise.avgRIR != null ? (
                              <p className="text-xs text-muted-foreground">
                                Avg RIR {sess.primaryExercise.avgRIR}
                              </p>
                            ) : <span />}
                            {sess.primaryExercise.interpretation ? (
                              <p className="text-xs text-muted-foreground italic text-right">
                                {sess.primaryExercise.interpretation}
                              </p>
                            ) : null}
                          </div>
                        </div>
                      )}

                    </div>
                  ))}
                  {workoutStats.recentSessions.length > 5 && (
                    <button
                      onClick={() => setShowAllSessions((v) => !v)}
                      className="text-xs text-primary hover:underline w-full text-center py-1"
                    >
                      {showAllSessions
                        ? 'Show less'
                        : `Show all ${workoutStats.recentSessions.length} sessions`}
                    </button>
                  )}
                </div>

              </div>
            ) : (
              <div className="rounded-xl border border-dashed px-4 py-8 text-center">
                <p className="text-sm font-medium mb-1">No workouts logged yet</p>
                <p className="text-xs text-muted-foreground">
                  Log your first workout in the Train tab to track strength progress here.
                </p>
              </div>
            )}

          </>
        )}

        {/* Form Analysis tab */}
        {progressTab === "form" && (
          <>

        {/* Squats subsection header */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.03 }}
          className="flex items-center gap-2"
        >
          <h2 className="text-base font-semibold text-foreground">Squats</h2>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
            Exercise
          </span>
        </motion.div>

        {/* ── Form Performance ─────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
        >
          <SectionLabel>Form Performance</SectionLabel>
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              icon={<Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
              label="Best Score"
              value={hasData ? `${getBestScore()}%` : '--'}
              highlight
            />
            <StatCard
              icon={<Activity className="w-5 h-5 text-green-600 dark:text-green-400" />}
              label="Sessions"
              value={hasData ? progressStats.totalAnalyses : 0}
            />
            <StatCard
              icon={<TrendingUp className={`w-5 h-5 ${currentStreak > 0 ? 'text-orange-500 dark:text-orange-400' : 'text-gray-400'}`} />}
              label="Analysis Streak"
              value={`${currentStreak}d`}
              valueColor={currentStreak > 0 ? 'text-orange-600 dark:text-orange-400' : undefined}
            />
          </div>
        </motion.div>

        {/* ── Recent Performance ───────────────────────────────────────────────── */}
        {(formMetrics != null || (analytics && (analytics.avg_last_5 != null || analytics.improvement_since_first != null))) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.07 }}
          >
            <SectionLabel>Recent Performance</SectionLabel>
            <div className="grid grid-cols-2 gap-3">
              {(formMetrics?.avgLast5 != null || analytics?.avg_last_5 != null) && (
                <StatCard
                  icon={<BarChart2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />}
                  label="Avg Last 5"
                  value={`${formMetrics?.avgLast5 ?? analytics?.avg_last_5}%`}
                />
              )}
            </div>
          </motion.div>
        )}

        {/* ── Weight Performance ───────────────────────────────────────────────── */}
        {(analytics?.best_weight != null || getAvgWeightLast5() != null || (analytics?.weight_trend && analytics.weight_trend.length >= 2)) && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.09 }}
          >
            <SectionLabel>Weight Performance</SectionLabel>
            <div className="grid grid-cols-2 gap-3">
              {analytics?.best_weight != null && (
                <StatCard
                  icon={<Dumbbell className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
                  label="Best Weight / PR"
                  value={`${toLb(analytics.best_weight)} lb`}
                  highlight
                />
              )}
              {getAvgWeightLast5() != null && (
                <StatCard
                  icon={<Dumbbell className="w-5 h-5 text-gray-500 dark:text-gray-400" />}
                  label="Avg Last 5"
                  value={`${getAvgWeightLast5()} lb`}
                />
              )}
            </div>
          </motion.div>
        )}

        {/* PR callouts */}
        {(formMetrics?.bestScore != null || (analytics && (analytics.best_score_ever != null || analytics.best_weight != null))) && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.115 }} className="flex flex-wrap gap-2">
            {(formMetrics?.bestScore != null || analytics?.best_score_ever != null) && (() => {
              // Prefer local session data for both score and weight
              const score = formMetrics?.bestScore ?? analytics?.best_score_ever;
              const prWeightLb = formMetrics?.prSession?.workingWeight ?? null;
              const prDate = formMetrics?.prSession?.timestamp;
              const dateStr = prDate
                ? new Date(prDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                : (() => {
                    const bestSession = analytics?.sessions.reduce((best, s) =>
                      (s.posture_score ?? 0) >= (best?.posture_score ?? 0) ? s : best,
                      analytics.sessions[0]
                    );
                    return bestSession?.date
                      ? new Date(bestSession.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                      : '';
                  })();
              return (
                <span key="form-pr" className="text-xs font-semibold px-2.5 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-200 dark:border-green-700">
                  Form PR: {score}%{prWeightLb != null ? ` at ${prWeightLb} lb` : ''}{dateStr ? ` on ${dateStr}` : ''}
                </span>
              );
            })()}
            {analytics.best_weight != null && (() => {
              const weightTrend = analytics.weight_trend ?? [];
              const bestWtSession = weightTrend.reduce((best: any, w: any) =>
                w.weight_kg >= (best?.weight_kg ?? 0) ? w : best,
                weightTrend[0]
              );
              const dateStr = bestWtSession?.date
                ? new Date(bestWtSession.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                : '';
              return (
                <span key="weight-pr" className="text-xs font-semibold px-2.5 py-1 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-700">
                  Weight PR: {toLb(analytics.best_weight)} lb{dateStr ? ` on ${dateStr}` : ''}
                </span>
              );
            })()}
          </motion.div>
        )}

        {/* Technique Skill bars — derived from averaged named_scores */}
        <TechniqueSkillCard namedScores={latestNamedScores} />

        {/* Chart or empty state */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          {analytics && analytics.sessions.length >= 2 ? /* 2+ sessions — render chart */ (() => {
            // Merge score + weight by session index for a combined chart.
            const weightByIndex: Record<number, number> = {};
            (analytics.weight_trend ?? []).forEach((w, i) => {
              weightByIndex[i] = toLb(w.weight_kg) ?? 0;
            });
            const hasWeight = (analytics.weight_trend ?? []).length > 0;
            const chartData = analytics.sessions.map((s, i) => ({
              session: i + 1,
              score: s.posture_score,
              weight: weightByIndex[i] ?? null,
            }));

            // Trend badge: weight-aware (form dipped when load ↑ + score ↓)
            const { label: trendLabel, cls: trendClass } = computeWeightAwareTrendLabel(
              analytics.sessions,
              analytics.weight_trend,
            );

            return (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-semibold text-foreground">Form Score vs Working Weight</h3>
                      {hasWeight && (
                        <p className="text-xs text-muted-foreground mt-0.5">Form score + working weight per session</p>
                      )}
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${trendClass}`}>
                      {trendLabel}
                    </span>
                  </div>
                  <ResponsiveContainer width="100%" height={hasWeight ? 180 : 160}>
                    <ComposedChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="session" tick={{ fontSize: 11 }} />
                      <YAxis yAxisId="score" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}`}
                        label={{ value: 'Form Score (%)', angle: -90, position: 'insideLeft', offset: 10, style: { textAnchor: 'middle', fontSize: 10, fill: 'hsl(var(--muted-foreground))' } }} />
                      {hasWeight && (
                        <YAxis yAxisId="weight" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}lb`}
                          label={{ value: 'Working Weight (lb)', angle: 90, position: 'insideRight', offset: 10, style: { textAnchor: 'middle', fontSize: 10, fill: '#9333ea' } }} />
                      )}
                      <Tooltip
                        formatter={(value: number, name: string) =>
                          name === 'weight' ? [`${value} lb`, 'Working Weight'] : [`${value}%`, 'Form Score']
                        }
                      />
                      {hasWeight && (
                        <Legend
                          iconSize={10}
                          wrapperStyle={{ fontSize: 11 }}
                          formatter={(v) => v === 'weight' ? 'Working Weight (lb)' : 'Form Score'}
                        />
                      )}
                      <Line yAxisId="score" type="monotone" dataKey="score" name="score" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                      {hasWeight && (
                        <Line yAxisId="weight" type="monotone" dataKey="weight" name="weight" stroke="#9333ea" strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" connectNulls />
                      )}
                    </ComposedChart>
                  </ResponsiveContainer>

                  {/* Under-chart summary — three key numbers */}
                  <div className="grid grid-cols-3 gap-2 mt-3">
                    <div className="text-center">
                      <div className="text-sm font-bold">{analytics.best_score_ever ?? '—'}</div>
                      <div className="text-xs text-muted-foreground">Best ever</div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm font-bold">{formMetrics?.avgLast5 ?? analytics.avg_last_5 ?? '—'}</div>
                      <div className="text-xs text-muted-foreground">Avg last 5</div>
                    </div>
                    <div className="text-center">
                      {(() => {
                        const imp = formMetrics?.changeVsBaseline ?? analytics.improvement_since_first;
                        const display = imp == null ? '—'
                          : imp === 0 ? '—'
                          : `${imp > 0 ? '↑' : '↓'} ${Math.abs(imp)}`;
                        const cls = imp == null || imp === 0 ? ''
                          : imp > 0 ? 'text-green-600 dark:text-green-400'
                          : 'text-amber-600 dark:text-amber-400';
                        return <div className={`text-sm font-bold ${cls}`}>{display}</div>;
                      })()}
                      <div className="text-xs text-muted-foreground">Change vs Baseline</div>
                    </div>
                  </div>

                  {/* Best weight inline — shown when weight data is present */}
                  {analytics.best_weight != null && (
                    <div className="mt-3 pt-3 border-t border-border flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Dumbbell className="w-3.5 h-3.5 text-purple-500" />
                        <span className="text-xs text-muted-foreground">Best weight</span>
                      </div>
                      <span className="text-xs font-semibold text-purple-600 dark:text-purple-400">
                        {toLb(analytics.best_weight)} lb
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })() : analytics && analytics.sessions.length === 1 ? (
            /* 1 session — celebrate + nudge toward second */
            <Card className="border border-border bg-card">
              <CardContent className="p-6 text-center space-y-3">
                <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mx-auto">
                  <Activity className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">First session recorded!</p>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    Record one more session to unlock your trend chart.
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="w-full h-10 rounded-lg font-medium"
                  onClick={() => navigate('/record')}
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Record Next Session
                </Button>
              </CardContent>
            </Card>
          ) : (
            /* 0 sessions */
            <Card className="border border-border bg-card">
              <CardContent className="p-6 text-center space-y-2">
                <Activity className="w-8 h-8 text-muted-foreground mx-auto" />
                <p className="text-sm font-medium text-foreground">No sessions yet</p>
                <p className="text-xs text-muted-foreground">Record your first squat session to unlock your progress chart.</p>
              </CardContent>
            </Card>
          )}
        </motion.div>

        {/* Baseline coaching paragraph */}
        {getBaselineText() && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <Card className="border border-border bg-muted/30">
              <CardContent className="p-4">
                <p className="text-sm text-muted-foreground leading-relaxed">{getBaselineText()}</p>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* ── Local Squat Session Coaching ─────────────────────────────────────── */}

        {/* Empty state — only when there are truly no squat records in either source */}
        {formAnalysisIsEmpty && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
            <Card className="border border-dashed border-border bg-muted/20">
              <CardContent className="p-5 text-center space-y-3">
                <BookOpen className="w-6 h-6 text-muted-foreground mx-auto" />
                <p className="text-sm font-semibold text-foreground">No squat sessions yet</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Record a squat and save it to your log to unlock coaching, primary limiter tracking, and session history.
                </p>
                <Button size="sm" variant="outline" className="w-full h-9 bg-transparent"
                        onClick={() => navigate('/record')}>
                  <Camera className="w-4 h-4 mr-2" />
                  Record your first squat
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Biggest Opportunity (local sessions) */}
        {squatSessions.length >= 1 && biggestOpportunity && (() => {
          // Causal check using local sessions (sorted desc: [0]=newest)
          const localWtDelta = squatSessions.length >= 2 && squatSessions[squatSessions.length - 1].workingWeight > 0
            ? squatSessions[0].workingWeight / squatSessions[squatSessions.length - 1].workingWeight
            : null;
          const localScoreDelta = squatSessions.length >= 2
            ? squatSessions[0].overallScore - squatSessions[squatSessions.length - 1].overallScore
            : null;
          const localCausal = localWtDelta != null && localWtDelta >= 1.10
            && localScoreDelta != null && localScoreDelta < 0
            && biggestOpportunity.avgScore < 70
            ? `Heavier load is exposing weaknesses in ${(COMP_LABELS[biggestOpportunity.componentKey] ?? biggestOpportunity.componentKey).toLowerCase()}. Refine technique at this weight before pushing higher.`
            : null;
          return (
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.19 }}>
              <Card className="border border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-900/20">
                <CardContent className="p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-rose-600 dark:text-rose-400 mb-1">
                    🎯 Primary Limiter
                  </p>
                  <p className="text-sm font-semibold text-foreground">
                    {COMP_LABELS[biggestOpportunity.componentKey] ?? biggestOpportunity.componentKey}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    avg {biggestOpportunity.avgScore}% — improving this moves your total score the fastest.
                  </p>
                  {localCausal && (
                    <p className="text-sm text-muted-foreground mt-1 font-medium">{localCausal}</p>
                  )}
                  <div className="w-full bg-muted rounded-full h-1.5 mt-3">
                    <div className="bg-red-400 h-1.5 rounded-full" style={{ width: `${biggestOpportunity.avgScore}%` }} />
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })()}

        {/* Last 4 sessions list */}
        {lastFourSessions.length >= 1 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.20 }}>
            <SectionLabel>Last {lastFourSessions.length} Squat Sessions</SectionLabel>
            <div className="space-y-0 divide-y divide-border">
              {lastFourSessions.map((session, i) => {
                const prev = lastFourSessions[i + 1];
                const delta = prev != null ? session.overallScore - prev.overallScore : null;
                return (
                  <div key={session.id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {new Date(session.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        <span className="text-muted-foreground font-normal"> · {session.workingWeight} lb</span>
                      </p>
                      <span className="text-xs text-muted-foreground">
                        Limiter: {COMP_LABELS[session.primaryLimiter] ?? session.primaryLimiter}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-semibold">{session.overallScore}%</span>
                      {delta != null && (
                        <span className={`text-xs ml-1 ${delta >= 0 ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                          {delta >= 0 ? '+' : ''}{delta}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

          </>
        )}


        {/* CTA for new or first session */}
        {progressTab === "strength" && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <Button
              size="lg"
              className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl"
              onClick={() => navigate('/workouts')}
            >
              Start Workout
            </Button>
          </motion.div>
        )}
        {/* Only show the bottom CTA when not in the full empty state —
            the empty-state widget already has its own "Record your first squat" button. */}
        {progressTab === "form" && !formAnalysisIsEmpty && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <Button
              size="lg"
              className="w-full h-12 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl"
              onClick={() => navigate('/record')}
            >
              <Camera className="w-4 h-4 mr-2" />
              Record New Session
            </Button>
          </motion.div>
        )}

      </div>
    </AppLayout>
  );
}
