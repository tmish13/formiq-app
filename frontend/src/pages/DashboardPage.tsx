import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp,
  BookOpen,
  Target,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useNavigate, useLocation } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';

import { useAuth } from '../hooks/useAuth';
import { formCheckService } from '../services/formCheckService';
import { progressService } from '../services/progressService';
import { isMeaningfulScore } from '../types/formCheck';
import { setUserPrefs } from '../utils/userPrefs';
import { TodayPlanCard } from '../components/molecules/TodayPlanCard';
import { trainingSessionService } from '../services/trainingSessionService';


const timeAgo = (dateStr: string): string => {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor(diff / 3600000);
  const mins = Math.floor(diff / 60000);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  return `${Math.max(1, mins)}m ago`;
};

export default function DashboardPage() {
  const [statsError, setStatsError] = useState(false);
  const [currentStreak, setCurrentStreak] = useState(0);
  const [todayFormScore, setTodayFormScore] = useState(0);
  const [weeklyImprovement, setWeeklyImprovement] = useState(0);
  const [totalSessions, setTotalSessions] = useState(0);
  const [lastSession, setLastSession] = useState<{ score: number; date: string; weightLb: number | null } | null>(null);
  const [betaDismissed, setBetaDismissed] = useState(
    () => localStorage.getItem("formiq-beta-notice-dismissed") === "1"
  );
  // null = loading (suppress empty-state flash), false = confirmed new user, true = returning user
  const [hasTrainingSessions, setHasTrainingSessions] = useState<boolean | null>(null);

  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user } = useAuth();

  useEffect(() => {
    if (user) {
      setUserPrefs({
        ...(user.fitness_goal != null && { fitnessGoal: user.fitness_goal }),
        ...(user.fitness_level != null && { fitnessLevel: user.fitness_level }),
      });
    }
  }, [user, user?.fitness_goal, user?.fitness_level]);

  // Re-fetch every time the user navigates to this page (location.key changes
  // on every navigation, even back to the same path — fixes stale state after
  // completing a workout and pressing Done).
  // isAuthenticated in deps ensures we reload after auth hydration completes on
  // page refresh, and that we never fire unauthenticated requests.
  useEffect(() => {
    if (isAuthenticated) loadDashboardData();
  }, [location.key, isAuthenticated]);

const loadDashboardData = async () => {
    try {
      // Fire all requests in parallel — they are independent
      const [analyticsData, progressData, historyData, trainingSessions] = await Promise.all([
        formCheckService.getAnalyticsOverview('30d'),
        progressService.getProgressOverview(),
        formCheckService.getHistory().catch(() => [] as any[]),
        trainingSessionService.list(1).catch(() => [] as any[]),
      ]);
      setHasTrainingSessions(trainingSessions.length > 0);

      setTotalSessions(analyticsData.totalSessions ?? 0);
      setTodayFormScore(Math.round(analyticsData.averageScore ?? 0));
      setWeeklyImprovement(Math.round(analyticsData.weeklyProgress ?? 0));
      setCurrentStreak(progressData.currentStreak || 0);

      // Find the most recent completed session with a meaningful score
      if (historyData && historyData.length > 0) {
        const sorted = [...historyData]
          .filter((fc: any) => fc.status === 'completed' && isMeaningfulScore(fc.posture_score ?? fc.score))
          .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        if (sorted.length > 0) {
          const fc = sorted[0];
          const effectiveScore = fc.posture_score ?? fc.score;
          const weightLb = fc.weight_kg != null ? Math.round(fc.weight_kg * 2.20462) : null;
          setLastSession({ score: Math.round(effectiveScore), date: fc.created_at, weightLb });
        }
      }
    } catch (error: any) {
      console.warn('Failed to load dashboard data', error);
      // Don't surface an error banner for 401s — the token interceptor either
      // retries successfully (no exception reaches here) or triggers a redirect.
      const httpStatus = error?.status ?? error?.response?.status;
      if (httpStatus !== 401) setStatsError(true);
      // Ensure hasTrainingSessions resolves so we don't show "Loading…" forever.
      setHasTrainingSessions((prev) => prev ?? false);
    }
  };

  /** Days since the last recorded session, or null if no sessions yet / session was today. */
  const daysSinceLastSession: number | null = lastSession
    ? Math.floor((Date.now() - new Date(lastSession.date).getTime()) / 86400000)
    : null

  /** Subtle nudge copy. Returns null when no nudge should show (today or no sessions). */
  const getNudgeText = (): string | null => {
    if (daysSinceLastSession === null || daysSinceLastSession === 0) return null
    if (daysSinceLastSession <= 3) {
      return "Consistency builds better form. When you're ready, record your next rep."
    }
    if (daysSinceLastSession > 7) {
      return "It's been a little while — record a session to see where you're at now."
    }
    return null
  }

  if (!isAuthenticated) {
    navigate('/auth');
    return null;
  }

  return (
    <AppLayout>
      <div className="px-4 py-6 space-y-8 max-w-4xl mx-auto" style={{ paddingBottom: "max(env(safe-area-inset-bottom), 96px)" }}>

        {/* Stats load error — subtle non-blocking notice; rest of page still renders */}
        {statsError && (
          <p className="text-xs text-muted-foreground text-center">
            Stats temporarily unavailable.{' '}
            <button
              className="underline"
              onClick={() => { setStatsError(false); loadDashboardData(); }}
            >
              Retry
            </button>
          </p>
        )}

        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-700 rounded-2xl p-5 text-white overflow-hidden"
          style={{ boxShadow: "0 8px 30px rgba(37, 99, 235, 0.2)" }}
        >
          {/* Subtle floating accents */}
          <div className="absolute top-3 right-3 w-20 h-20 bg-white/5 rounded-full blur-xl" />
          <div className="absolute bottom-2 left-6 w-14 h-14 bg-white/5 rounded-full blur-lg" />

          <div className="relative z-10">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-xl font-bold mb-0.5 text-balance">
                  {hasTrainingSessions === false
                    ? 'Ready to Train'
                    : 'Keep the Momentum'}
                </h1>
                <p className="text-blue-200 text-sm">
                  {hasTrainingSessions === false
                    ? 'Log your first session to start tracking progress'
                    : hasTrainingSessions === null
                      ? 'Loading your training history\u2026'
                      : totalSessions === 0
                        ? 'No form analyses yet \u2014 record a rep to get started'
                        : `${totalSessions} form ${totalSessions === 1 ? 'analysis' : 'analyses'} logged \u00b7 view below`}
                </p>
              </div>
              {currentStreak > 0 && (
                <div className="flex items-center gap-1.5 bg-white/15 rounded-full px-2.5 py-1 flex-shrink-0">
                  <Target className="w-3.5 h-3.5 text-orange-300" />
                  <span className="font-semibold text-xs">{currentStreak}d</span>
                </div>
              )}
            </div>

            {/* Stat chips — only when data exists */}
            {todayFormScore > 0 && (
              <div className="flex items-center gap-3 mb-4 text-sm">
                <div className="flex items-center gap-1.5 bg-white/10 rounded-lg px-3 py-1.5">
                  <Target className="w-3.5 h-3.5" />
                  <span className="font-medium">{todayFormScore}%</span>
                  <span className="text-blue-200 text-xs">score</span>
                </div>
                {weeklyImprovement > 0 && (
                  <div className="flex items-center gap-1.5 bg-white/10 rounded-lg px-3 py-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-green-300" />
                    <span className="font-medium text-green-200">+{weeklyImprovement}%</span>
                    <span className="text-blue-200 text-xs">this week</span>
                  </div>
                )}
              </div>
            )}

            {lastSession && (
              <p className="text-xs text-blue-200/80 mt-2">
                Last squat: {lastSession.score}%{lastSession.weightLb != null ? ` · ${lastSession.weightLb} lb` : ''} · {timeAgo(lastSession.date)}
              </p>
            )}
          </div>
        </motion.div>

        {/* AI Workout Recommendation — key forces remount on each navigation so
            useMemo inside recomputes from fresh localStorage data */}
        <TodayPlanCard key={location.key} />

        {/* AI Form Analysis */}
        <div className="rounded-xl border border-border px-4 py-3 space-y-1.5">
          <h3 className="text-sm font-semibold">AI Form Analysis</h3>
          <p className="text-xs text-muted-foreground">
            Technique feedback on key compound lifts. Currently available for squats — overhead
            press and row analysis coming soon.
          </p>
          <Button variant="outline" size="sm" className="mt-1" onClick={() => navigate("/record")}>
            Analyze New Lift
          </Button>
        </div>

        {/* Motivation nudge — only when ≥1 day since last session */}
        {getNudgeText() && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08, duration: 0.35 }}
          >
            <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
              <TrendingUp className="w-4 h-4 text-slate-500 dark:text-slate-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{getNudgeText()}</p>
            </div>
          </motion.div>
        )}

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="space-y-3"
        >
          <h2 className="text-base font-semibold text-foreground">Quick Actions</h2>

          <div className="grid grid-cols-2 gap-3">
            <Card
              className="cursor-pointer border border-border bg-card hover:bg-accent/50 transition-colors duration-150"
              onClick={() => navigate('/progress')}
            >
              <CardContent className="p-4">
                <div className="flex flex-col gap-2.5">
                  <div className="w-9 h-9 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-green-600 dark:text-green-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground text-sm">Progress</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">Track improvements</p>
                  </div>
                  {weeklyImprovement > 0 && (
                    <Badge variant="secondary" className="text-[10px] w-fit px-1.5 py-0">
                      +{weeklyImprovement}%
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card
              className="cursor-pointer border border-border bg-card hover:bg-accent/50 transition-colors duration-150"
              onClick={() => navigate('/analysis')}
            >
              <CardContent className="p-4">
                <div className="flex flex-col gap-2.5">
                  <div className="w-9 h-9 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                    <BookOpen className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground text-sm">Analysis History</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">View past analyses</p>
                  </div>
                  {totalSessions > 0 && (
                    <Badge variant="secondary" className="text-[10px] w-fit px-1.5 py-0">
                      {totalSessions} sessions
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </motion.div>

        {!betaDismissed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="flex items-start justify-between gap-2 px-2 pb-2"
          >
            <p className="text-[11px] text-muted-foreground/60">
              You're using the FormIQ Beta. Expect fast changes and occasional glitches — please send
              feedback if something feels off.
            </p>
            <button
              className="text-[11px] text-muted-foreground/50 hover:text-muted-foreground shrink-0 mt-0.5"
              onClick={() => {
                localStorage.setItem("formiq-beta-notice-dismissed", "1");
                setBetaDismissed(true);
              }}
              aria-label="Dismiss"
            >
              ✕
            </button>
          </motion.div>
        )}

      </div>
    </AppLayout>
  );
}
