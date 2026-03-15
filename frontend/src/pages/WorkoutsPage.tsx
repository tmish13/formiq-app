/**
 * Workout Mode — main page.
 * Offline-first session tracking with RIR-based next-set recommendations.
 *
 * Equipment Context system (Phase 2):
 * - Sessions: equipment stored per-set via SetLog.equipmentProfileId;
 *   current exercise equipment stored in `currentEquipment` state.
 * - Gym selector REMOVED — equipment is now first-class context.
 * - Start screen: user picks default equipment for the session.
 * - handleSelectExercise: restores last-used equipment for that exercise
 *   (gym-agnostic, via getLastEquipment); falls back to startEquipment.
 * - Next-session targets: keyed by exerciseId + equipmentProfileId
 *   (gym-agnostic since equipment profile is the identifier).
 */
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Trophy, TrendingUp, BarChart2, Camera, X } from "lucide-react";
import { AppLayout } from "../components/layout/AppLayout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import ExercisePickerModal from "../features/training/ExercisePickerModal";
import EquipmentPickerDrawer from "../features/training/EquipmentPickerDrawer";
import { EXERCISES, getExercisesForEquipmentType } from "../features/training/catalog";
import {
  createSession,
  addSetLog,
  deleteSetLog,
  listSetLogsForSession,
  listSessions,
  listEquipmentProfiles,
  saveNextTarget,
  getNextTarget,
  getLastEquipment,
  setLastEquipment,
  pushRecentEquipmentProfileId,
  EQUIPMENT_TYPE_LABELS,
} from "../features/training/storage";
import { getEquipmentDisplayName } from "../features/training/equipmentDisplay";
import { getNextSetRecommendation } from "../features/training/progressionEngine";
import { computeFatigueBudget } from "../utils/fatigueBudget";
import { getClampedWorkingRepRange } from "../utils/repClamp";
import { computeNextSessionTarget } from "../utils/nextSessionTargets";
import { getUserPrefs, mapFitnessGoalToGoal } from "../utils/userPrefs";
import { TodayPlanCard } from "../components/molecules/TodayPlanCard";
import { generateWorkoutInsights } from "../utils/workoutInsights";
import { loadSquatSessions } from "../utils/squatSessions";
import { getNextSessionRecommendation } from "../utils/trainingRecommendations";
import { makeId } from "../features/training/id";
import { trainingSessionService } from "../services/trainingSessionService";
import { useAppSelector } from "../store/hooks";
import type {
  Exercise,
  EquipmentProfile,
  Goal,
  SetLog,
  SetType,
  WorkoutSession,
  NextSetRecommendation,
  ExerciseStatus,
  FatigueSignal,
} from "../features/training/types";
import type { NextSessionTarget } from "../utils/nextSessionTargets";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Exercise IDs in the catalog whose default load type is bodyweight (increment=0).
 * Used for smart equipment default selection.
 */
const BODYWEIGHT_EXERCISE_IDS = new Set<string>([
  "pull_up", "dip", "chin_up", "push_up", "bodyweight_squat", "inverted_row", "hanging_leg_raise",
]);

const GOAL_OPTIONS: { value: Goal; label: string; description: string }[] = [
  { value: "strength",    label: "Strength",        description: "Low fatigue, heavier sets, frequent progress" },
  { value: "hypertrophy", label: "Moderate Volume",  description: "Balanced muscle-building with controlled fatigue" },
  { value: "general",     label: "Higher Volume",    description: "More reps and flexibility, easier to sustain" },
];

/** Maps internal Goal values to user-facing display labels. */
const GOAL_LABELS: Record<string, string> = Object.fromEntries(
  GOAL_OPTIONS.map(o => [o.value, o.label])
);

const SET_TYPE_OPTIONS: { value: SetType; label: string }[] = [
  { value: "warmup",  label: "Warm-up" },
  { value: "working", label: "Working" },
  { value: "backoff", label: "Back-off" },
];

const QUICK_INCREMENTS = [2.5, 5, 10, 25, 45] as const;

const ACTION_COLORS: Record<string, string> = {
  increase: "bg-emerald-100 text-emerald-800",
  hold:     "bg-blue-100 text-blue-800",
  reduce:   "bg-amber-100 text-amber-800",
  stop:     "bg-red-100 text-red-800",
};

const TARGET_RIR: Record<Goal, string> = {
  strength:    "1–2",
  hypertrophy: "2–3",
  general:     "2–3",
};

/** Human-readable recommended rest duration per goal. */
const REST_LABEL: Record<Goal, string> = {
  strength:    "Recommended rest: 3–5 min",
  hypertrophy: "Recommended rest: 90–120s",
  general:     "Recommended rest: 60–90s",
};

/** Default rest timer seconds by goal (used when no rec is cached). */
const REST_SECONDS_DEFAULT: Record<Goal, number> = {
  strength:    240,
  hypertrophy: 105,
  general:     75,
};

const STATUS_COLORS: Record<ExerciseStatus, string> = {
  continue: "text-blue-700 dark:text-blue-300",
  optional: "text-amber-700 dark:text-amber-300",
  finish:   "text-emerald-700 dark:text-emerald-300",
};

const FATIGUE_COLORS: Record<FatigueSignal, string> = {
  normal:  "text-muted-foreground",
  rising:  "text-amber-600 dark:text-amber-400",
  high:    "text-red-600 dark:text-red-400",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------


function formatElapsed(startedAt: string): string {
  const totalMin = Math.floor(
    (Date.now() - new Date(startedAt).getTime()) / 60000,
  );
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

/** Epley estimated 1RM formula. Returns null for bodyweight (weightLb = 0). */
function estimatedOneRepMax(weightLb: number, reps: number): number | null {
  if (weightLb <= 0 || reps <= 0) return null;
  return Math.round(weightLb * (1 + reps / 30));
}

/**
 * The step size used on the labeled weight buttons.
 * Uses equipment increment when available and > 0, then falls back to
 * load-type defaults already established in this codebase.
 */
function weightStep(exercise: Exercise, equipment: EquipmentProfile | null): number {
  const eqInc = equipment?.incrementLb;
  if (eqInc != null && eqInc > 0) return eqInc;
  const loadType = exercise.defaultLoadType;
  if (loadType === "barbell_plates" || loadType === "machine_plate_loaded") return 10;
  if (loadType === "dumbbell_pair") return 5;
  const exInc = exercise.defaultIncrementLb;
  return exInc > 0 ? exInc : 5;
}

function exerciseNameById(id: string): string {
  return EXERCISES.find((e) => e.id === id)?.name ?? id;
}

/**
 * Best working set from prior sessions for this exercise.
 * Scans the 20 most recent sessions; returns null when nothing exists.
 */
function getLastSessionBestSet(
  currentSessionId: string,
  exerciseId: string,
): SetLog | null {
  const sessions = listSessions(20);
  for (const s of sessions) {
    if (s.id === currentSessionId) continue;
    const working = listSetLogsForSession(s.id).filter(
      (sl) => sl.exerciseId === exerciseId && sl.setType === "working",
    );
    if (working.length === 0) continue;
    return working.reduce((best, sl) => {
      if (sl.weightLb > best.weightLb) return sl;
      if (sl.weightLb === best.weightLb && sl.reps > best.reps) return sl;
      return best;
    });
  }
  return null;
}

/** Deterministic next-session coaching line for the summary screen. */
function nextTimeLine(goal: Goal, bestSet: SetLog | null): string {
  if (!bestSet || bestSet.weightLb === 0) {
    return "Next time: add reps or try a weighted variation.";
  }
  if (goal === "strength") {
    const lastRir = bestSet.rir ?? null;
    if (lastRir !== null && lastRir >= 3) {
      return `Next time: try ${bestSet.weightLb + 5} lb × 5–6 @ RIR 2.`;
    }
    return "Next time: match today's best set at a cleaner RIR.";
  }
  if (goal === "hypertrophy") {
    return "Next time: match reps first, then add load.";
  }
  return "Next time: add 1 rep or +5 lb if it felt easy.";
}

// ---------------------------------------------------------------------------
// Types local to this file
// ---------------------------------------------------------------------------

interface ExerciseSummary {
  exerciseId: string;
  exerciseName: string;
  workingSets: SetLog[];
  bestSet: SetLog | null;
  e1RM: number | null;
  nextTimeSuggestion: string;
  nextTarget: NextSessionTarget | null;
  equipmentName: string | null;
  explanation: string | null;
}

interface WorkoutSummary {
  session: WorkoutSession;
  exercises: ExerciseSummary[];
  totalWorkingSets: number;
  totalVolumeLb: number;
  durationMin: number;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SetLogTable({
  sets,
  bestSetId,
}: {
  sets: SetLog[];
  bestSetId?: string;
}) {
  if (sets.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2 text-center">
        No sets logged yet.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-muted-foreground border-b border-border">
            <th className="text-left pb-1 font-medium w-6">#</th>
            <th className="text-left pb-1 font-medium">Type</th>
            <th className="text-right pb-1 font-medium">Weight</th>
            <th className="text-right pb-1 font-medium">Reps</th>
            <th className="text-right pb-1 font-medium">RIR</th>
          </tr>
        </thead>
        <tbody>
          {sets.map((s, i) => (
            <tr
              key={s.id}
              className={`border-b border-border/50 last:border-0 ${
                s.id === bestSetId ? "bg-muted/30" : ""
              }`}
            >
              <td className="py-1.5 text-muted-foreground">{i + 1}</td>
              <td className="py-1.5 capitalize">{s.setType}</td>
              <td className="py-1.5 text-right font-medium tabular-nums">
                {s.weightLb > 0 ? `${s.weightLb} lb` : "BW"}
              </td>
              <td className="py-1.5 text-right tabular-nums">{s.reps}</td>
              <td className="py-1.5 text-right text-muted-foreground tabular-nums">
                {s.rir != null ? s.rir : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Unlocked recommendation card — shown once ≥1 working set is logged.
 *
 * Two states:
 *  - Capped:  fatigue budget reached → "Exercise Complete" overlay
 *  - Normal:  engine recommendation with clamped rep range
 *
 * Does NOT change progressionEngine.ts — fatigue gate is a wrapper only.
 */
function NextSetCard({
  sets,
  exercise,
  equipment,
  goal,
  savedTarget,
  onApply,
  onEndExercise,
}: {
  sets: SetLog[];
  exercise: Exercise;
  equipment: EquipmentProfile | null;
  goal: Goal;
  savedTarget: NextSessionTarget | null;
  onApply: (weight: number, reps: number, rec: NextSetRecommendation) => void;
  onEndExercise: () => void;
}) {
  const rec = useMemo(
    () => getNextSetRecommendation({ goal, exercise, equipment, recentSets: sets }),
    [goal, exercise, equipment, sets],
  );

  // C: pass equipment increment so "similar load" uses the right tolerance
  const incrementLb = equipment?.incrementLb ?? exercise.defaultIncrementLb;

  const fatigue = useMemo(
    () =>
      computeFatigueBudget({
        goal,
        incrementLb,
        sets: sets.map((s) => ({
          setType: s.setType,
          weight: s.weightLb,
          reps: s.reps,
          rir: s.rir,
        })),
      }),
    [goal, incrementLb, sets],
  );

  const clampedReps = useMemo(
    () => getClampedWorkingRepRange({ goal, engineRange: rec.nextRepsRange }),
    [goal, rec.nextRepsRange],
  );

  const patchedRec = useMemo(() => {
    const workingSets = sets.filter((s) => s.setType === "working");
    const lastWorking = workingSets.at(-1);
    const lastRir = lastWorking?.rir;
    const count = workingSets.length;

    // Per-goal setsRecommended: strength=2, general=4, hypertrophy stays at 4
    const setsRecommended =
      goal === "strength" ? 2 :
      goal === "general"  ? 4 : rec.setsRecommended;

    let exerciseStatus = rec.exerciseStatus;
    let statusMessage  = rec.statusMessage;

    // STRENGTH: strict two-hard-set model
    if (goal === "strength") {
      if (count < 2) {
        exerciseStatus = "continue";
        statusMessage = count === 1
          ? "One hard set done — aim for a second working set."
          : undefined;
      } else if (lastRir != null && lastRir <= 1) {
        exerciseStatus = "finish";
        statusMessage = "Two hard sets completed — stop here to stay fresh.";
      } else if (rec.fatigueSignal === "high") {
        exerciseStatus = "finish";
        statusMessage = "High fatigue — stop here to protect next session.";
      } else {
        exerciseStatus = "optional";
        statusMessage = "Strength target reached. Finish or add an optional back-off set.";
      }
    }

    // HIGHER VOLUME (general): 3–4 set target; stop at 3 if fatigue rising
    if (goal === "general") {
      if (count < 3) {
        exerciseStatus = "continue";
        statusMessage = count > 0
          ? "Higher-volume target not yet reached — continue if form stays solid."
          : undefined;
      } else if (count === 3 && rec.fatigueSignal === "normal") {
        exerciseStatus = "optional";
        statusMessage = "Good stimulus — one more controlled set is appropriate.";
      } else {
        exerciseStatus = "finish";
        statusMessage = "Higher-volume target reached. Move to the next exercise.";
      }
    }

    return { ...rec, setsRecommended, exerciseStatus, statusMessage };
  }, [rec, goal, sets]);

  // ── Capped state: fatigue budget reached ───────────────────────────────
  if (fatigue.isCapped) {
    const workingOnly = sets.filter((s) => s.setType === "working");
    const lastWorking = workingOnly.slice(-1)[0];

    // E: back-off only for strength + high fatigue + exactly 2 working sets
    const showBackOff =
      goal === "strength" &&
      fatigue.isHighFatigue &&
      workingOnly.length === 2 &&
      lastWorking &&
      lastWorking.weightLb > 0;
    const backOffWeight = showBackOff
      ? Math.round((lastWorking!.weightLb * 0.9) / 5) * 5
      : null;

    return (
      <Card className="border-amber-200 dark:border-amber-800">
        <CardHeader className="py-3 px-4">
          {/* D: no icon, updated title */}
          <CardTitle className="text-sm text-amber-600 dark:text-amber-400">
            Finish Exercise
          </CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4 space-y-3">
          {/* D: frequency-first copy */}
          <p className="text-sm text-muted-foreground">
            Stop here to stay fresh for your next session.
          </p>

          {fatigue.reasons.length > 0 && (
            <ul className="space-y-1">
              {fatigue.reasons.map((r, i) => (
                <li key={i} className="text-xs text-muted-foreground flex gap-1.5">
                  <span className="text-amber-500 shrink-0">•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          )}

          {/* E: conditional back-off */}
          {backOffWeight != null && (
            <p className="text-xs text-muted-foreground border-t border-border/50 pt-2">
              Optional back-off:{" "}
              <strong className="text-foreground">
                {backOffWeight} lb × 6–8 @ RIR 2–3
              </strong>
            </p>
          )}

          <Button
            variant="outline"
            size="sm"
            className="w-full border-amber-200 dark:border-amber-800"
            onClick={onEndExercise}
          >
            End Exercise
          </Button>
        </CardContent>
      </Card>
    );
  }

  // ── Normal recommendation state ────────────────────────────────────────
  const weightText = patchedRec.nextWeightLb > 0 ? `${patchedRec.nextWeightLb} lb` : "BW";
  const repText    = `${clampedReps.min}–${clampedReps.max} reps`;
  const midReps    = Math.round((clampedReps.min + clampedReps.max) / 2);

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm flex items-center justify-between">
          <span>Next Set Recommendation</span>
          <span className="text-xs font-normal text-muted-foreground tabular-nums">
            Working: {patchedRec.setsCompleted} / {patchedRec.setsRecommended}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-3">
        {/* Action badge */}
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
              ACTION_COLORS[patchedRec.action] ?? "bg-muted text-foreground"
            }`}
          >
            {patchedRec.action.charAt(0).toUpperCase() + patchedRec.action.slice(1)}
          </span>
        </div>

        {/* Explicit next set line */}
        <p className="text-base font-semibold">
          Next set:{" "}
          <span className="font-bold">
            {weightText} × {repText}
          </span>
        </p>

        {/* Rep clamp coach line */}
        {clampedReps.wasClamped && clampedReps.coachLine && (
          <p className="text-xs text-muted-foreground">{clampedReps.coachLine}</p>
        )}

        {/* Target RIR */}
        <p className="text-sm text-muted-foreground">
          Target RIR: <strong>{TARGET_RIR[goal]}</strong>
        </p>

        {/* Engine fatigue signal (non-normal) */}
        {patchedRec.fatigueSignal !== "normal" && (
          <p className={`text-xs font-medium ${FATIGUE_COLORS[patchedRec.fatigueSignal]}`}>
            {patchedRec.fatigueSignal === "rising" ? "⚠ Fatigue rising" : "🔴 High fatigue"}
          </p>
        )}

        {/* Exercise status coaching message */}
        {patchedRec.statusMessage && (
          <p className={`text-xs font-medium ${STATUS_COLORS[patchedRec.exerciseStatus]}`}>
            {patchedRec.statusMessage}
          </p>
        )}

        {/* Primary reason */}
        {patchedRec.reasons.length > 0 && (
          <p className="text-xs text-muted-foreground">{patchedRec.reasons[0]}</p>
        )}

        {/* Last saved target — context from previous session */}
        {savedTarget && (
          <p className="text-xs text-muted-foreground">
            Last target: {savedTarget.targetWeightLb} lb × {savedTarget.targetRepsRange.min}–{savedTarget.targetRepsRange.max} @ RIR {savedTarget.targetRir}
          </p>
        )}

        {/* Fill inputs — does NOT log the set */}
        <Button
          size="sm"
          className="w-full"
          onClick={() => onApply(patchedRec.nextWeightLb, midReps, patchedRec)}
        >
          Fill inputs
        </Button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Squat form nudge helpers
// ---------------------------------------------------------------------------

/** True if any exercise in the session is a squat-pattern movement. */
function sessionContainsSquat(summary: WorkoutSummary): boolean {
  return summary.exercises.some((ex) => {
    const catalogEx = EXERCISES.find((e) => e.id === ex.exerciseId);
    return catalogEx?.movementPattern === 'squat';
  });
}

/**
 * True if a squat form analysis was already saved today via the AnalysisPage drawer.
 * Reads localStorage squat sessions (formiq-squat-sessions-v1).
 */
function hasRecentSquatAnalysis(): boolean {
  try {
    const sessions = loadSquatSessions();
    const today = new Date().toDateString();
    return sessions.some((s) => new Date(s.date).toDateString() === today);
  } catch {
    return false;
  }
}

function nudgeSuppressionKey(sessionId: string): string {
  return `formiq-squat-nudge-v1-${sessionId}`;
}

function isNudgeSuppressed(sessionId: string): boolean {
  try {
    return !!localStorage.getItem(nudgeSuppressionKey(sessionId));
  } catch {
    return false;
  }
}

function suppressNudge(sessionId: string, reason: 'dismissed' | 'acted'): void {
  try {
    localStorage.setItem(nudgeSuppressionKey(sessionId), reason);
  } catch {
    // storage failure — ignore
  }
}

// ---------------------------------------------------------------------------
// Workout Summary screen
// ---------------------------------------------------------------------------

function WorkoutSummaryScreen({
  summary,
  onDone,
}: {
  summary: WorkoutSummary;
  onDone: () => void;
}) {
  const navigate = useNavigate();
  const [showNudge, setShowNudge] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    if (isNudgeSuppressed(summary.session.id)) return false;
    if (!sessionContainsSquat(summary)) return false;
    if (hasRecentSquatAnalysis()) return false;
    return true;
  });

  function handleDismissNudge() {
    suppressNudge(summary.session.id, 'dismissed');
    setShowNudge(false);
  }

  function handleRecordSquat() {
    suppressNudge(summary.session.id, 'acted');
    navigate('/record');
  }

  const durationLabel =
    summary.durationMin < 60
      ? `${summary.durationMin}m`
      : `${Math.floor(summary.durationMin / 60)}h ${summary.durationMin % 60}m`;

  const volumeLabel = summary.totalVolumeLb > 0
    ? ` · ${summary.totalVolumeLb.toLocaleString()} lb volume`
    : "";

  return (
    <div className="px-4 pt-4 pb-32 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Trophy className="h-6 w-6 text-amber-500" />
        <div>
          <h1 className="text-lg font-bold">Workout Complete</h1>
          <p className="text-xs text-muted-foreground">
            {GOAL_LABELS[summary.session.goal] ?? summary.session.goal} · {durationLabel} · {summary.totalWorkingSets} sets{volumeLabel}
          </p>
        </div>
      </div>

      {/* Per-exercise summary */}
      {summary.exercises.map((ex) => (
        <Card key={ex.exerciseId}>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-sm flex items-center justify-between">
              <div>
                <span>{ex.exerciseName}</span>
                {ex.equipmentName && (
                  <p className="text-xs font-normal text-muted-foreground mt-0.5">
                    {ex.equipmentName}
                  </p>
                )}
              </div>
              <span className="text-xs font-normal text-muted-foreground shrink-0">
                {ex.workingSets.length} working set{ex.workingSets.length !== 1 ? "s" : ""}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-4 space-y-2">
            {/* Sets table */}
            <SetLogTable sets={ex.workingSets} bestSetId={ex.bestSet?.id} />

            {/* Best set + e1RM */}
            {ex.bestSet && (
              <div className="pt-1 border-t border-border/50 space-y-1">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />
                  <p className="text-xs font-medium">
                    Best set:{" "}
                    <span className="text-foreground">
                      {ex.bestSet.weightLb > 0 ? `${ex.bestSet.weightLb} lb` : "BW"} × {ex.bestSet.reps}
                    </span>
                  </p>
                </div>
                {ex.e1RM != null && (
                  <div className="flex items-center gap-2">
                    <BarChart2 className="h-3.5 w-3.5 text-blue-600" />
                    <p className="text-xs text-muted-foreground">
                      Estimated 1RM:{" "}
                      <strong className="text-foreground">{ex.e1RM} lb</strong>
                    </p>
                  </div>
                )}
                {/* Next session target */}
                {ex.nextTarget && (
                  <div className="mt-1 space-y-0.5">
                    <p className="text-xs font-semibold text-primary">
                      Next time:{" "}
                      {ex.nextTarget.targetWeightLb > 0 ? `${ex.nextTarget.targetWeightLb} lb × ` : "BW × "}
                      {ex.nextTarget.targetRepsRange.min}–{ex.nextTarget.targetRepsRange.max} @ RIR {ex.nextTarget.targetRir}
                    </p>
                    {ex.explanation && (
                      <p className="text-xs text-muted-foreground">{ex.explanation}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      ))}

      {summary.exercises.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-8">
          No sets logged yet.
        </p>
      )}

      {/* AI Workout Insights — RIR-based coaching feedback */}
      {(() => {
        const insights = generateWorkoutInsights({
          exercises: summary.exercises.map((ex) => ({
            exerciseName: ex.exerciseName,
            workingSets: ex.workingSets,
          })),
          totalVolumeLb: summary.totalVolumeLb,
          totalWorkingSets: summary.totalWorkingSets,
        });
        if (insights.length === 0) return null;
        return (
          <div className="space-y-2">
            {insights.map((insight, i) => (
              <div
                key={i}
                className={`rounded-xl px-4 py-3 space-y-0.5 border ${
                  insight.type === "warning"
                    ? "bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800"
                    : "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800"
                }`}
              >
                <p className={`text-xs font-semibold ${insight.type === "warning" ? "text-amber-700 dark:text-amber-400" : "text-emerald-700 dark:text-emerald-400"}`}>
                  {insight.headline}
                </p>
                <p className="text-xs text-muted-foreground">{insight.detail}</p>
                <p className="text-xs text-muted-foreground">{insight.recommendation}</p>
              </div>
            ))}
          </div>
        );
      })()}

      {/* Squat form analysis nudge */}
      {showNudge && (
        <div className="rounded-xl border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 px-4 py-4 space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <Camera className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm font-semibold text-blue-700 dark:text-blue-300">Track your squat form</p>
            </div>
            <button
              onClick={handleDismissNudge}
              className="text-muted-foreground hover:text-foreground transition-colors flex-shrink-0"
              aria-label="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground">
            You trained squat today. Record a set to see how your technique is trending.
          </p>
          <Button size="sm" className="w-full" onClick={handleRecordSquat}>
            <Camera className="w-4 h-4 mr-2" />
            Record squat analysis
          </Button>
        </div>
      )}

      <Button className="w-full" size="lg" onClick={onDone}>
        Done
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// History tab
// ---------------------------------------------------------------------------

function HistoryTab() {
  const [visibleCount, setVisibleCount] = React.useState(20);
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  // Initialized from localStorage synchronously; upgraded to backend data after fetch.
  const [sessions, setSessions] = React.useState(() =>
    listSessions().map((s) => ({
      session: { id: s.id, startedAt: s.startedAt, goal: s.goal },
      sets: listSetLogsForSession(s.id),
    }))
  );

  // Re-runs when isAuthenticated transitions to true (e.g. after logout → login).
  // Using [] alone caused the fetch to silently fail with no retry on re-login.
  React.useEffect(() => {
    if (!isAuthenticated) return;
    trainingSessionService.list().then((records) => {
      if (records.length > 0) {
        setSessions(
          records.map((r) => ({
            session: { id: r.id, startedAt: r.started_at, goal: r.goal },
            sets: r.sets_json,
          }))
        );
      }
      // else: backend empty — keep localStorage data already in state
    }).catch(() => {
      // Network error — localStorage fallback already loaded in state
    });
  }, [isAuthenticated]);

  const sessionsWithSets = sessions.filter(({ sets }) => sets.length > 0);
  const pagedSessions = sessionsWithSets.slice(0, visibleCount);
  const hasMore = sessionsWithSets.length > visibleCount;
  const allProfiles = listEquipmentProfiles();

  return (
    <div className="space-y-4">
      {pagedSessions.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-8">
          No past workouts yet.
        </p>
      )}
      {pagedSessions.map(({ session: s, sets }) => {
        const date = new Date(s.startedAt).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        });
        const exerciseIds = Array.from(new Set(sets.map((sl) => sl.exerciseId)));
        return (
          <Card key={s.id}>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm flex justify-between">
                <span>{GOAL_LABELS[s.goal] ?? s.goal}</span>
                <span className="text-muted-foreground font-normal">{date}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {exerciseIds.map((exId) => {
                const exSets = sets.filter((sl) => sl.exerciseId === exId);
                // Show equipment name if any set has an equipment profile
                const equipId = exSets.find((sl) => sl.equipmentProfileId)?.equipmentProfileId;
                const equipProfile = equipId ? allProfiles.find((p) => p.id === equipId) : null;
                const equipName = equipProfile ? getEquipmentDisplayName(equipProfile) : null;
                return (
                  <div key={exId} className="mb-2">
                    <p className="text-xs font-medium mb-0.5">{exerciseNameById(exId)}</p>
                    {equipName && (
                      <p className="text-xs text-muted-foreground mb-1">{equipName}</p>
                    )}
                    <SetLogTable sets={exSets} />
                  </div>
                );
              })}
            </CardContent>
          </Card>
        );
      })}
      {hasMore && (
        <div className="flex justify-center mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setVisibleCount((v) => v + 20)}
          >
            Load older workouts
          </Button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function WorkoutsPage() {
  const navigate = useNavigate();
  const [session,          setSession]          = useState<WorkoutSession | null>(null);
  const [goal,             setGoal]             = useState<Goal>(() => {
    const { fitnessGoal } = getUserPrefs();
    return fitnessGoal ? mapFitnessGoalToGoal(fitnessGoal) : "hypertrophy";
  });
  const [currentExercise,  setCurrentExercise]  = useState<Exercise | null>(null);
  const [currentEquipment, setCurrentEquipment] = useState<EquipmentProfile | null>(null);
  const [setsForExercise,  setSetsForExercise]  = useState<SetLog[]>([]);

  const [exercisePickerOpen,  setExercisePickerOpen]  = useState(false);
  const [equipmentPickerOpen, setEquipmentPickerOpen] = useState(false);
  const [elapsed,             setElapsed]             = useState("");

  // Numeric log state
  const [logWeight,   setLogWeight]   = useState<number>(45);
  const [logReps,     setLogReps]     = useState<number>(8);
  const [logRir,      setLogRir]      = useState<number | null>(null);
  const [logSetType,  setLogSetType]  = useState<SetType>("working");
  // Inline weight step — user-adjustable per session; resets when equipment/exercise changes
  const [customStep,  setCustomStep]  = useState<number>(5);
  const [nextIndex,   setNextIndex]   = useState(0);
  const [didApplyRec, setDidApplyRec] = useState(false);

  // Timer / UX state
  const [restTimer,   setRestTimer]   = useState<{ total: number; remaining: number; running: boolean } | null>(null);
  const [undoNotice,  setUndoNotice]  = useState<string | null>(null);
  const [tab,         setTab]         = useState<"active" | "history">("active");
  const [rirHelpOpen, setRirHelpOpen] = useState(false);

  // Workout summary (shown instead of clearing immediately on End Workout)
  const [summary, setSummary] = useState<WorkoutSummary | null>(null);

  // Equipment context — default equipment for the session (start screen picker)
  const [startEquipment, setStartEquipment] = useState<EquipmentProfile | null>(null);
  const [equipmentPickerOpenStart, setEquipmentPickerOpenStart] = useState(false);
  // Hint shown under equipment line: why was this equipment auto-selected?
  const [equipmentHint, setEquipmentHint] = useState<string | null>(null);

  const lastRecRef   = useRef<NextSetRecommendation | null>(null);
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Elapsed timer
  useEffect(() => {
    if (!session) return;
    setElapsed(formatElapsed(session.startedAt));
    const id = setInterval(
      () => setElapsed(formatElapsed(session.startedAt)),
      30_000,
    );
    return () => clearInterval(id);
  }, [session]);

  // Sync customStep when equipment or exercise changes
  useEffect(() => {
    if (currentExercise) {
      setCustomStep(weightStep(currentExercise, currentEquipment));
    }
  }, [currentEquipment, currentExercise]);

  // Rest timer countdown
  useEffect(() => {
    if (!restTimer?.running) return;
    const id = setInterval(() => {
      setRestTimer((t) =>
        !t ? null
        : t.remaining <= 1 ? { ...t, remaining: 0, running: false }
        : { ...t, remaining: t.remaining - 1 },
      );
    }, 1000);
    return () => clearInterval(id);
  }, [restTimer?.running]);

  const reloadSets = useCallback((sessionId: string, exerciseId: string) => {
    const all = listSetLogsForSession(sessionId).filter(
      (s) => s.exerciseId === exerciseId,
    );
    setSetsForExercise(all);
    setNextIndex(all.length);
  }, []);

  const lastSessionPreview = useMemo(() => {
    if (session) return null; // only show on start screen
    const sessions = listSessions(1);
    if (!sessions.length) return null;
    const sess = sessions[0];
    const sets = listSetLogsForSession(sess.id);
    const exIds = Array.from(new Set(sets.map((s) => s.exerciseId)));
    return {
      date: sess.startedAt,
      goal: sess.goal as Goal,
      items: exIds.slice(0, 3).map((exId) => {
        const equipId = sets.find((s) => s.exerciseId === exId)?.equipmentProfileId;
        const target = getNextTarget(exId, equipId, undefined);
        return { exerciseId: exId, target };
      }),
    };
  }, [session]); // recompute when session changes (returns null during active session)

  function handleStartWorkout() {
    const s = createSession(goal);
    setSession(s);
    setCurrentExercise(null);
    setSetsForExercise([]);
    setTab("active");
    setSummary(null);
    // Carry start-screen equipment into the session so the exercise picker filters immediately
    const allProfiles = listEquipmentProfiles();
    const initialEquip =
      startEquipment ??
      allProfiles.find((p) => p.isDefault || p.type === "barbell") ??
      allProfiles[0] ??
      null;
    setCurrentEquipment(initialEquip);
  }

  function handleContinueSession() {
    const sessions = listSessions(1);
    if (!sessions.length) return;
    const prev = sessions[0];
    const prevGoal = (prev.goal as Goal) ?? goal;
    setGoal(prevGoal);
    const s = createSession(prevGoal);
    setSession(s);
    setSetsForExercise([]);
    setTab("active");
    setSummary(null);
    setLogRir(null);
    setDidApplyRec(false);

    const allProfiles = listEquipmentProfiles();

    // Pre-select the first exercise from the last session so the user lands ready to log,
    // not on a blank screen. Pre-fill weight/reps from the stored next-session target.
    const prevSets = listSetLogsForSession(prev.id);
    const firstExId = Array.from(new Set(prevSets.map((sl) => sl.exerciseId)))[0] ?? null;
    const firstEx = firstExId ? (EXERCISES.find((e) => e.id === firstExId) ?? null) : null;

    if (firstEx) {
      setCurrentExercise(firstEx);

      // Equipment: prefer last-used for this exercise, else session default
      const lastEquipId = getLastEquipment(firstEx.id);
      const resolvedEquip =
        (lastEquipId ? allProfiles.find((p) => p.id === lastEquipId) : null) ??
        startEquipment ??
        allProfiles.find((p) => p.isDefault || p.type === "barbell") ??
        allProfiles[0] ??
        null;
      setCurrentEquipment(resolvedEquip);

      // Pre-fill from saved next-session target if available
      const firstEquipId = prevSets.find((sl) => sl.exerciseId === firstExId)?.equipmentProfileId;
      const nextTarget = getNextTarget(firstExId, firstEquipId, undefined);
      if (nextTarget && nextTarget.targetWeightLb > 0) {
        setLogWeight(nextTarget.targetWeightLb);
        setLogReps(nextTarget.targetRepsRange.min);
      } else {
        setLogWeight(firstEx.defaultIncrementLb === 0 ? 0 : 45);
        setLogReps(8);
      }
    } else {
      // No prior exercise data — fall back to session equipment default
      const initialEquip =
        startEquipment ??
        allProfiles.find((p) => p.isDefault || p.type === "barbell") ??
        allProfiles[0] ??
        null;
      setCurrentEquipment(initialEquip);
    }
  }

  function buildSummary(sess: WorkoutSession): WorkoutSummary {
    const allSets = listSetLogsForSession(sess.id);
    const durationMin = Math.max(
      1,
      Math.round((Date.now() - new Date(sess.startedAt).getTime()) / 60000),
    );
    const exerciseIds = Array.from(new Set(allSets.map((s) => s.exerciseId)));
    const exercises: ExerciseSummary[] = exerciseIds.map((exId) => {
      const exSets = allSets.filter((s) => s.exerciseId === exId);
      const workingSets = exSets.filter((s) => s.setType === "working");
      // Best set = highest estimated 1RM (or highest reps for BW)
      const bestSet = workingSets.reduce<SetLog | null>((best, s) => {
        if (!best) return s;
        const e1 = estimatedOneRepMax(s.weightLb, s.reps) ?? s.reps;
        const e2 = estimatedOneRepMax(best.weightLb, best.reps) ?? best.reps;
        return e1 > e2 ? s : best;
      }, null);

      // Compute and persist next-session target
      const exercise = EXERCISES.find((e) => e.id === exId) ?? null;
      const eqProfile = exSets[0]?.equipmentProfileId
        ? listEquipmentProfiles(undefined, exId as any).find(
            (p) => p.id === exSets[0].equipmentProfileId,
          ) ?? null
        : null;
      const incrementLb = eqProfile?.incrementLb ?? exercise?.defaultIncrementLb ?? 5;
      const repClampRange = getClampedWorkingRepRange({
        goal: sess.goal,
        engineRange: exercise?.defaultRepIntent,
      });
      // FIX 2: pass all sets — function filters for working + selects best internally
      // Equipment-scoped target key (gymId removed — equipment is the identifier now)
      const nextTarget = computeNextSessionTarget({
        goal: sess.goal,
        sets: exSets,
        incrementLb,
        repClampRange,
      });
      if (nextTarget) {
        try {
          saveNextTarget(exId, eqProfile?.id, undefined, nextTarget);
        } catch {
          // storage failure — ignore
        }
      }

      const equipProfile = eqProfile;
      const explanation = bestSet
        ? getNextSessionRecommendation({
            lastWeightLb: bestSet.weightLb,
            lastReps: bestSet.reps,
            lastRir: bestSet.rir,
            incrementLb,
            goal: sess.goal as Goal,
          }).explanation
        : null;
      return {
        exerciseId: exId,
        exerciseName: exerciseNameById(exId),
        workingSets,
        bestSet,
        e1RM: bestSet ? estimatedOneRepMax(bestSet.weightLb, bestSet.reps) : null,
        nextTimeSuggestion: nextTimeLine(sess.goal, bestSet),
        nextTarget,
        equipmentName: equipProfile ? getEquipmentDisplayName(equipProfile) : null,
        explanation,
      };
    });
    const workingSets = allSets.filter((s) => s.setType === "working");
    const totalVolumeLb = workingSets.reduce((sum, s) => sum + s.weightLb * s.reps, 0);
    return {
      session: sess,
      exercises,
      totalWorkingSets: workingSets.length,
      totalVolumeLb,
      durationMin,
    };
  }

  function handleEndWorkout() {
    if (!session) return;
    setSummary(buildSummary(session));
    // Persist to backend — fire-and-forget, never blocks the summary screen.
    // localStorage remains intact as the immediate source of truth.
    trainingSessionService.sync(session, listSetLogsForSession(session.id));
  }

  function handleDismissSummary() {
    setSession(null);
    setCurrentExercise(null);
    setCurrentEquipment(null);
    setSetsForExercise([]);
    setLogWeight(45);
    setLogReps(8);
    setLogRir(null);
    setNextIndex(0);
    setRestTimer(null);
    setUndoNotice(null);
    setDidApplyRec(false);
    setSummary(null);
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    navigate("/");
  }

  function handleSelectExercise(ex: Exercise) {
    setCurrentExercise(ex);
    setEquipmentHint(null);

    const allProfiles = listEquipmentProfiles();
    const lastEquipId = getLastEquipment(ex.id);
    const lastEquip = lastEquipId
      ? allProfiles.find((p) => p.id === lastEquipId) ?? null
      : null;

    const isCompatible =
      currentEquipment != null &&
      (currentEquipment.type === "other" || ex.allowedEquipment.includes(currentEquipment.type));

    if (lastEquip) {
      // 1. Last-used equipment for this exercise wins
      setCurrentEquipment(lastEquip);
      setEquipmentHint(`Last used for ${ex.name}: ${getEquipmentDisplayName(lastEquip)}`);
    } else if (isCompatible) {
      // 2. Keep currently selected equipment — it's compatible; no hint needed
    } else {
      // 3. Smart default: bodyweight exercises → Bodyweight profile; others → Barbell/default
      //    (Fires when no current equipment, or current equipment is incompatible with exercise)
      const defaultEquip = BODYWEIGHT_EXERCISE_IDS.has(ex.id)
        ? (allProfiles.find((p) => p.type === "bodyweight") ?? null)
        : (allProfiles.find((p) => p.isDefault || p.type === "barbell") ?? allProfiles[0] ?? startEquipment ?? null);
      setCurrentEquipment(defaultEquip);
      if (defaultEquip) {
        setLastEquipment(ex.id, defaultEquip.id); // persist auto-selection so next visit restores it
        setEquipmentHint(`Recommended for ${ex.name}`);
      }
    }

    if (session) reloadSets(session.id, ex.id);
    setLogWeight(ex.defaultIncrementLb === 0 ? 0 : 45);
    setLogReps(8);
    setLogRir(null);
    setDidApplyRec(false);
  }

  function handleApplyRec(weight: number, reps: number, rec: NextSetRecommendation) {
    lastRecRef.current = rec;
    setLogWeight(weight > 0 ? weight : logWeight);
    setLogReps(reps);
    setDidApplyRec(true);
  }

  function handleLogSet() {
    if (!session || !currentExercise) return;
    if (logWeight < 0 || logReps <= 0) return;
    if (logSetType === "working" && logRir === null) return;

    const setLog: SetLog = {
      id: makeId(),
      sessionId: session.id,
      exerciseId: currentExercise.id,
      equipmentProfileId: currentEquipment?.id,
      setIndex: nextIndex,
      setType: logSetType,
      weightLb: logWeight,
      reps: logReps,
      rir: logRir ?? undefined,
      createdAt: new Date().toISOString(),
    };

    addSetLog(setLog);
    reloadSets(session.id, currentExercise.id);
    setNextIndex((n) => n + 1);
    setLogRir(null);
    setLogSetType("working");
    setDidApplyRec(false);

    // Start rest timer — use goal-based default; lastRec is a hint only
    const restSecs = REST_SECONDS_DEFAULT[goal];
    setRestTimer({ total: restSecs, remaining: restSecs, running: true });

    // Undo notice (5s)
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
    setUndoNotice(setLog.id);
    undoTimerRef.current = setTimeout(() => setUndoNotice(null), 5000);
  }

  function handleUndo(setId: string) {
    deleteSetLog(setId);
    if (session && currentExercise) reloadSets(session.id, currentExercise.id);
    setNextIndex((n) => Math.max(0, n - 1));
    setUndoNotice(null);
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
  }

  /** Clear the current exercise — used by NextSetCard's "End Exercise" button. */
  function handleEndExercise() {
    setCurrentExercise(null);
    setCurrentEquipment(null);
    setEquipmentHint(null);
    setSetsForExercise([]);
    setLogRir(null);
    setDidApplyRec(false);
    setRestTimer(null);
    setUndoNotice(null);
    setNextIndex(0);
    if (undoTimerRef.current) clearTimeout(undoTimerRef.current);
  }

  // Derived values for weight controls
  const inc          = currentEquipment?.incrementLb ?? currentExercise?.defaultIncrementLb ?? 5;
  // Pure bodyweight: equipment type is explicitly "bodyweight" OR increment is 0 with no equipment
  const isBodyweight = (currentEquipment?.type === "bodyweight") || (inc === 0 && !currentEquipment);
  const hasWorkingSet = setsForExercise.some((s) => s.setType === "working");

  // Best working set id for table highlight
  const bestWorkingSetId = setsForExercise
    .filter((s) => s.setType === "working")
    .reduce<{ id: string; score: number } | null>((best, s) => {
      const score = estimatedOneRepMax(s.weightLb, s.reps) ?? s.reps;
      if (!best || score > best.score) return { id: s.id, score };
      return best;
    }, null)?.id;

  // "Last best" display: current session > previous session
  const displayBestSet = (() => {
    if (!currentExercise || !session) return null;
    const currentBest = setsForExercise
      .filter((s) => s.setType === "working")
      .reduce<SetLog | null>((best, s) => {
        if (!best || s.weightLb > best.weightLb) return s;
        if (s.weightLb === best.weightLb && s.reps > best.reps) return s;
        return best;
      }, null);
    if (currentBest) return { set: currentBest, source: "current" as const };
    const lastBest = getLastSessionBestSet(session.id, currentExercise.id);
    return lastBest ? { set: lastBest, source: "previous" as const } : null;
  })();

  // Saved next-session target for the current exercise + equipment (equipment-scoped)
  const savedTarget = useMemo(
    () =>
      currentExercise
        ? getNextTarget(currentExercise.id, currentEquipment?.id, undefined)
        : null,
    [currentExercise, currentEquipment],
  );

  // ── Workout summary (shown after End Workout) ─────────────────────────────
  if (summary) {
    return (
      <AppLayout>
        <WorkoutSummaryScreen summary={summary} onDone={handleDismissSummary} />
      </AppLayout>
    );
  }

  // ── Main layout: always-visible tab bar ───────────────────────────────────
  return (
    <AppLayout>
      <div className="px-4 pt-4 pb-32 space-y-4">

        {/* Session header — only during active session */}
        {session && (
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-base font-semibold">{GOAL_LABELS[goal] ?? goal} session</h1>
              <p className="text-xs text-muted-foreground">{elapsed}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleEndWorkout}
              className="text-xs"
            >
              End Workout
            </Button>
          </div>
        )}

        {/* Tab bar — ALWAYS shown */}
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          {(["active", "history"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 rounded-md py-1.5 text-xs font-medium transition-colors ${
                tab === t
                  ? "bg-white dark:bg-gray-800 shadow-sm"
                  : "text-muted-foreground"
              }`}
            >
              {t === "active" ? "Active" : "History"}
            </button>
          ))}
        </div>

        {tab === "history" ? (
          <HistoryTab />
        ) : session ? (
          // ── Active session content ────────────────────────────────────────
          <>
            {/* Equipment selector — always visible so exercise picker can filter */}
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Equipment</p>
              <button
                type="button"
                onClick={() => setEquipmentPickerOpen(true)}
                className="w-full flex items-center justify-between rounded-xl border border-border px-4 py-3 text-left hover:bg-muted/50 transition-colors"
              >
                <span className="text-sm font-medium">
                  {currentEquipment
                    ? getEquipmentDisplayName(currentEquipment)
                    : "Select equipment…"}
                </span>
                <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
              </button>
              {equipmentHint && (
                <p className="text-xs text-muted-foreground px-1 italic">{equipmentHint}</p>
              )}
            </div>

            {/* C — Exercise selector */}
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">Exercise</p>
              <button
                type="button"
                onClick={() => setExercisePickerOpen(true)}
                className="w-full flex items-center justify-between rounded-xl border border-border px-4 py-3 text-left hover:bg-muted/50 transition-colors"
              >
                {currentExercise ? (
                  <span className="text-sm font-medium">{currentExercise.name}</span>
                ) : (
                  <span className="text-sm text-muted-foreground">Pick exercise…</span>
                )}
                <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
              </button>
            </div>

            {currentExercise && (
              <>

                {/* 3.4 — Last best set (subtle retention line) */}
                {displayBestSet && (
                  <p className="text-xs text-muted-foreground px-1 -mt-1">
                    {displayBestSet.source === "current" ? "Best today:" : "Last best:"}{" "}
                    <strong className="text-foreground">
                      {displayBestSet.set.weightLb > 0
                        ? `${displayBestSet.set.weightLb} lb`
                        : "BW"}{" "}
                      × {displayBestSet.set.reps}
                    </strong>
                  </p>
                )}

                {/* B — ORDER: Sets logged → Recommendation → Log a set */}

                {/* 1. Sets logged */}
                <Card>
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span>Sets logged</span>
                      {setsForExercise.filter(s => s.setType === "working").length > 0 && (
                        <span className="text-xs font-normal text-muted-foreground">
                          {setsForExercise.filter(s => s.setType === "working").length} working
                        </span>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-4">
                    <SetLogTable sets={setsForExercise} bestSetId={bestWorkingSetId} />
                  </CardContent>
                </Card>

                {/* Undo notice */}
                {undoNotice && (
                  <div className="flex items-center justify-between rounded-lg bg-muted px-3 py-2 text-xs">
                    <span>Set logged</span>
                    <button
                      onClick={() => handleUndo(undoNotice)}
                      className="font-semibold text-primary underline"
                    >
                      Undo
                    </button>
                  </div>
                )}

                {/* 2. Next Set Recommendation (gated) */}
                {hasWorkingSet ? (
                  <NextSetCard
                    sets={setsForExercise}
                    exercise={currentExercise}
                    equipment={currentEquipment}
                    goal={goal}
                    savedTarget={savedTarget}
                    onApply={handleApplyRec}
                    onEndExercise={handleEndExercise}
                  />
                ) : (
                  <p className="text-sm text-muted-foreground px-1">
                    Log your first working set to unlock AI coaching.
                  </p>
                )}

                {/* Rest timer (enhanced) */}
                {restTimer && (
                  <div className="rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 px-4 py-3 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-blue-800 dark:text-blue-200">
                        Rest
                      </p>
                      <p className="text-2xl font-bold tabular-nums text-blue-900 dark:text-blue-100">
                        {Math.floor(restTimer.remaining / 60)}:{String(restTimer.remaining % 60).padStart(2, "0")}
                      </p>
                      <p className="text-xs text-blue-600 dark:text-blue-300 mt-0.5">
                        {REST_LABEL[goal]}
                      </p>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => setRestTimer(null)}>
                      Skip
                    </Button>
                  </div>
                )}

                {/* 3. Log a set */}
                <Card>
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-sm">Log a set</CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-4 space-y-4">
                    {/* Set type */}
                    <div className="flex gap-1.5">
                      {SET_TYPE_OPTIONS.map((t) => (
                        <button
                          key={t.value}
                          type="button"
                          onClick={() => {
                            setLogSetType(t.value);
                            setDidApplyRec(false);
                          }}
                          className={`flex-1 rounded-lg border py-1.5 text-xs font-medium transition-colors ${
                            logSetType === t.value
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-border hover:bg-muted/50"
                          }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    {/* D — Weight stepper */}
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">Weight (lb)</p>
                      {isBodyweight ? (
                        <div className="rounded-lg border border-border px-4 py-3 text-center">
                          <span className="text-2xl font-bold">Bodyweight</span>
                        </div>
                      ) : (
                        <>
                          {/* Inline step selector */}
                          <div className="flex gap-1.5">
                            {QUICK_INCREMENTS.map((v) => (
                              <button
                                key={v}
                                type="button"
                                onClick={() => setCustomStep(v)}
                                className={`flex-1 rounded-lg border py-1.5 text-xs font-semibold transition-colors ${
                                  customStep === v
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : "border-border text-muted-foreground hover:bg-muted/50"
                                }`}
                              >
                                {v}
                              </button>
                            ))}
                          </div>
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => setLogWeight((w) => Math.max(0, w - customStep))}
                              className="flex-1 h-12 rounded-lg border border-border font-semibold text-sm hover:bg-muted/50 transition-colors"
                            >
                              −{customStep}
                            </button>
                            <div className="w-24 text-center">
                              <span className="text-2xl font-bold tabular-nums">{logWeight}</span>
                              <span className="text-sm text-muted-foreground ml-1">lb</span>
                            </div>
                            <button
                              type="button"
                              onClick={() => setLogWeight((w) => w + customStep)}
                              className="flex-1 h-12 rounded-lg border border-border font-semibold text-sm hover:bg-muted/50 transition-colors"
                            >
                              +{customStep}
                            </button>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Reps stepper */}
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">Reps</p>
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => setLogReps((r) => Math.max(1, r - 1))}
                          className="flex-1 h-12 rounded-lg border border-border font-semibold text-sm hover:bg-muted/50 transition-colors"
                        >
                          −1
                        </button>
                        <span className="w-24 text-2xl font-bold tabular-nums text-center">{logReps}</span>
                        <button
                          type="button"
                          onClick={() => setLogReps((r) => Math.min(30, r + 1))}
                          className="flex-1 h-12 rounded-lg border border-border font-semibold text-sm hover:bg-muted/50 transition-colors"
                        >
                          +1
                        </button>
                      </div>
                    </div>

                    {/* E — RIR chips */}
                    <div className="space-y-1">
                      <p className="text-xs text-muted-foreground">
                        RIR
                        {logSetType === "working" && (
                          <span className="text-destructive ml-1">*</span>
                        )}
                      </p>
                      <div className="flex gap-2 flex-wrap">
                        {[0, 1, 2, 3, 4, 5].map((v) => (
                          <button
                            key={v}
                            type="button"
                            onClick={() => setLogRir(logRir === v ? null : v)}
                            className={`w-10 h-10 rounded-lg border text-sm font-semibold transition-colors ${
                              logRir === v
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border hover:bg-muted/50"
                            }`}
                          >
                            {v}
                          </button>
                        ))}
                        <button
                          type="button"
                          onClick={() => setRirHelpOpen(true)}
                          className="text-xs text-muted-foreground underline ml-1 self-center"
                        >
                          What's RIR?
                        </button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        0 = failure • 2 = challenging • 4 = easy
                      </p>
                    </div>

                    {/* A3 — Applied helper */}
                    {didApplyRec && (
                      <p className="text-xs text-muted-foreground">
                        Applied recommendation — edit if needed.
                      </p>
                    )}

                    <Button
                      className="w-full"
                      onClick={handleLogSet}
                      disabled={logSetType === "working" && logRir === null}
                    >
                      Log Set
                    </Button>
                  </CardContent>
                </Card>
              </>
            )}
          </>
        ) : (
          // ── Start screen ────────────────────────────────────────────────────
          <div className="space-y-6">
            <div>
              <h1 className="text-xl font-bold">Train</h1>
              <p className="text-sm text-muted-foreground mt-1">
                Log your sets. Get AI load recommendations based on your RIR.
              </p>
            </div>

            {/* Last session preview */}
            {lastSessionPreview && (
              <div className="rounded-xl border border-border bg-muted/30 px-4 py-3 space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium">Continue from last workout</p>
                  <p className="text-xs text-muted-foreground">{GOAL_LABELS[lastSessionPreview.goal] ?? lastSessionPreview.goal}</p>
                </div>
                {lastSessionPreview.items.map(
                  ({ exerciseId, target }) =>
                    target && (
                      <div key={exerciseId} className="space-y-0.5">
                        <div className="flex items-center justify-between text-sm">
                          <span>{exerciseNameById(exerciseId)}</span>
                          <span className="text-xs font-medium text-primary">
                            {target.targetWeightLb > 0 ? `${target.targetWeightLb} lb × ` : "BW × "}
                            {target.targetRepsRange.min}–{target.targetRepsRange.max} @ RIR {target.targetRir}
                          </span>
                        </div>
                        {target.rationale && (
                          <p className="text-xs text-muted-foreground">{target.rationale}</p>
                        )}
                      </div>
                    )
                )}
                <Button className="w-full mt-1" size="sm" onClick={handleContinueSession}>
                  Start Session
                </Button>
              </div>
            )}

            {/* Today's recommended training plan — only when no prior session to continue */}
            {!lastSessionPreview && <TodayPlanCard onStart={handleStartWorkout} />}

            {/* Equipment selector */}
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Equipment</label>
              <button
                type="button"
                onClick={() => setEquipmentPickerOpenStart(true)}
                className="w-full flex items-center justify-between rounded-xl border border-border px-4 py-3 text-left hover:bg-muted/50 transition-colors"
              >
                <div>
                  <p className="text-sm font-medium">
                    {startEquipment
                      ? getEquipmentDisplayName(startEquipment)
                      : "Barbell (standard)"}
                  </p>
                  {startEquipment ? (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {EQUIPMENT_TYPE_LABELS[startEquipment.type] ?? startEquipment.type}
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Tap to change
                    </p>
                  )}
                </div>
                <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
              </button>
            </div>

            {/* Goal selector */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Training goal</p>
              {GOAL_OPTIONS.map((g) => (
                <button
                  key={g.value}
                  type="button"
                  onClick={() => setGoal(g.value)}
                  className={`w-full rounded-xl border px-4 py-3 text-left transition-colors ${
                    goal === g.value
                      ? "border-primary bg-primary/5"
                      : "border-border hover:bg-muted/50"
                  }`}
                >
                  <p className="text-sm font-medium">{g.label}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{g.description}</p>
                </button>
              ))}
            </div>

            <Button className="w-full" size="lg" onClick={handleStartWorkout}>
              Start Workout
            </Button>
          </div>
        )}
      </div>

      {/* Modals — only during active session */}
      {session && (
        <>
          <ExercisePickerModal
            open={exercisePickerOpen}
            equipmentType={currentEquipment?.type}
            onSelect={handleSelectExercise}
            onClose={() => setExercisePickerOpen(false)}
          />

          {/* Equipment picker — always available (not gated on currentExercise) */}
          <EquipmentPickerDrawer
            open={equipmentPickerOpen}
            selectedId={currentEquipment?.id}
            onSelect={(p) => {
              setCurrentEquipment(p);
              setEquipmentHint(null);
              // If an exercise is already selected, check compatibility and invalidate if needed
              if (p && currentExercise && p.type !== "other") {
                setLastEquipment(currentExercise.id, p.id);
                pushRecentEquipmentProfileId(p.id);
                const valid = getExercisesForEquipmentType(p.type);
                if (!valid.some((e) => e.id === currentExercise.id)) {
                  setCurrentExercise(null);
                  setEquipmentHint("Choose an exercise that matches this equipment.");
                }
              }
            }}
            onClose={() => setEquipmentPickerOpen(false)}
          />
        </>
      )}

      {/* Start-screen equipment picker (no active session needed) */}
      <EquipmentPickerDrawer
        open={equipmentPickerOpenStart}
        selectedId={startEquipment?.id}
        onSelect={(p) => {
          setStartEquipment(p);
        }}
        onClose={() => setEquipmentPickerOpenStart(false)}
      />

      {/* RIR explanation dialog */}
      <Dialog open={rirHelpOpen} onOpenChange={setRirHelpOpen}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle>What's RIR?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            <strong>Reps In Reserve</strong> — how many more reps you could have
            done before failure.
          </p>
          <ul className="text-sm space-y-1 mt-2">
            <li><strong>0</strong> — couldn't do one more (max effort)</li>
            <li><strong>1–2</strong> — very close to failure</li>
            <li><strong>3–4</strong> — moderate challenge</li>
            <li><strong>5+</strong> — felt easy</li>
          </ul>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
