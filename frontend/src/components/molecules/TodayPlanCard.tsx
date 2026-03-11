import React, { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../ui/button";
import { generateDailyPlan } from "../../utils/trainingPlan";
import { getUserPrefs, mapFitnessGoalToGoal } from "../../utils/userPrefs";
import { useAuth } from "../../hooks/useAuth";

/**
 * Self-contained "Today's Training" card.
 *
 * Derives goal from localStorage prefs (set during onboarding / profile save),
 * falling back to user.fitness_goal from auth context.
 * Computes plan from last session in localStorage — no network calls.
 */
export function TodayPlanCard({ onStart }: { onStart?: () => void }) {
  const navigate = useNavigate();
  const { user } = useAuth();

  const goal = mapFitnessGoalToGoal(
    getUserPrefs().fitnessGoal ?? (user as any)?.fitness_goal,
  );

  const plan = useMemo(() => generateDailyPlan(goal), [goal]);

  return (
    <div className="rounded-2xl border border-primary/20 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Today's Training</h2>
        <span className="text-xs text-muted-foreground capitalize">{goal} focus</span>
      </div>

      {plan.isEmpty ? (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {(user as any)?.has_completed_onboarding
              ? 'Continue building from your recent sessions with AI-guided load recommendations.'
              : 'Log your first workout to unlock personalized session recommendations.'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Main lift */}
          {plan.mainLift && (
            <div className="space-y-1">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Main Lift
              </p>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{plan.mainLift.exerciseName}</span>
                <span className="text-xs font-semibold text-primary">
                  {plan.mainLift.sets} × {plan.mainLift.repsMin}–{plan.mainLift.repsMax} @ RIR{" "}
                  {plan.mainLift.targetRir}
                </span>
              </div>
              {plan.mainLift.targetWeightLb !== null && plan.mainLift.targetWeightLb > 0 && (
                <p className="text-xs text-muted-foreground">
                  Suggested load: {plan.mainLift.targetWeightLb} lb
                </p>
              )}
            </div>
          )}

          {/* Accessories */}
          {plan.accessories.length > 0 && (
            <div className="space-y-1 pt-1 border-t border-border/30">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Accessories
              </p>
              {plan.accessories.map((ex) => (
                <div key={ex.exerciseId} className="flex items-center justify-between">
                  <span className="text-sm text-foreground/80">{ex.exerciseName}</span>
                  <span className="text-xs text-muted-foreground">
                    {ex.sets} × {ex.repsMin}–{ex.repsMax}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <Button className="w-full" size="sm" onClick={() => onStart ? onStart() : navigate("/workouts")}>
        Start Workout
      </Button>
    </div>
  );
}
