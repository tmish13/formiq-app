import React from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Video,
  CheckCircle,
  ArrowRight,
  ChevronDown,
  Dumbbell,
  TrendingUp,
  Target,
  BookOpen,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useAppSelector } from '../store/hooks';

const STEPS = [
  {
    icon: Video,
    title: 'Record your lift',
    desc: 'Upload a squat video or record directly in the app.',
  },
  {
    icon: Target,
    title: 'Get a form score',
    desc: 'Depth, stability, and posture — scored automatically.',
  },
  {
    icon: TrendingUp,
    title: 'Track your progress',
    desc: 'Log sessions, see trends, and know when to push harder.',
  },
];

const VALUES = [
  {
    icon: Target,
    color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    title: 'Form feedback without a coach',
    desc: 'Objective analysis on every rep — depth, balance, and posture scored from video.',
  },
  {
    icon: TrendingUp,
    color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    title: 'Know when to progress',
    desc: 'Load recommendations based on your recent sessions and form quality.',
  },
  {
    icon: BookOpen,
    color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    title: 'Training history in one place',
    desc: 'Log sessions, track PRs, and see your progression over time.',
  },
  {
    icon: Dumbbell,
    color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    title: 'Built for solo training',
    desc: 'Most lifters train without a coach. FormIQ gives you the feedback they would.',
  },
];

const MOCK_BREAKDOWN = [
  { label: 'Depth', status: 'Good', color: 'text-emerald-600 dark:text-emerald-400' },
  { label: 'Stability', status: 'Good', color: 'text-emerald-600 dark:text-emerald-400' },
  { label: 'Posture', status: 'Needs work', color: 'text-amber-600 dark:text-amber-400' },
];

export default function LandingPage() {
  const { isAuthenticated, isLoading } = useAppSelector((state) => state.auth);
  const user = useAppSelector((state) => state.auth.user);
  const navigate = useNavigate();

  // Redirect authenticated users — don't block render while loading
  if (!isLoading && isAuthenticated) {
    if (!user?.has_completed_onboarding) return <Navigate to="/onboarding" replace />;
    return <Navigate to="/dashboard" replace />;
  }

  const toAuth = () => navigate('/auth');

  return (
    <div className="min-h-screen bg-background text-foreground">

      {/* Minimal nav */}
      <nav className="flex items-center justify-between px-5 py-4 max-w-2xl mx-auto">
        <span className="font-bold text-lg">FormIQ</span>
        <Button variant="ghost" size="sm" onClick={toAuth}>
          Sign in
        </Button>
      </nav>

      {/* ── Hero ───────────────────────────────────────────────── */}
      <section className="px-5 pt-10 pb-12 max-w-2xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="space-y-5"
        >
          <Badge variant="secondary" className="text-xs">
            Beta · Squat analysis available now
          </Badge>

          <h1 className="text-3xl sm:text-4xl font-bold leading-tight text-balance">
            Form analysis and workout tracking for lifters who train alone.
          </h1>

          <p className="text-muted-foreground text-base max-w-md mx-auto">
            Record a squat, get a form score, and track your training — all in one place.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Button size="lg" className="w-full sm:w-auto px-8 h-12" onClick={toAuth}>
              Get started free
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors py-2"
            >
              See how it works <ChevronDown className="w-4 h-4" />
            </a>
          </div>
        </motion.div>
      </section>

      {/* ── Product mock ────────────────────────────────────────── */}
      <section className="px-5 pb-16 max-w-xs mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.45 }}
          className="rounded-2xl border border-border bg-card p-5 shadow-lg"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-[11px] text-muted-foreground uppercase tracking-wide">
                Form Analysis · Squat
              </p>
              <p className="text-2xl font-bold mt-0.5">
                84{' '}
                <span className="text-sm font-normal text-muted-foreground">/ 100</span>
              </p>
            </div>
            <div className="w-11 h-11 rounded-full bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
          </div>

          <div className="w-full bg-muted rounded-full h-1.5 mb-4">
            <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: '84%' }} />
          </div>

          <div className="space-y-2.5">
            {MOCK_BREAKDOWN.map(({ label, status, color }) => (
              <div key={label} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{label}</span>
                <span className={`font-medium ${color}`}>{status}</span>
              </div>
            ))}
          </div>

          <p className="text-[10px] text-muted-foreground/40 mt-3.5">
            Analysed in 18s · 1 rep detected
          </p>
        </motion.div>
      </section>

      {/* ── How it works ─────────────────────────────────────────── */}
      <section
        id="how-it-works"
        className="px-5 py-14 max-w-2xl mx-auto border-t border-border"
      >
        <h2 className="text-2xl font-bold text-center mb-10">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={i} className="flex flex-col items-center text-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Icon className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="font-semibold text-sm">
                    <span className="text-muted-foreground mr-1">{i + 1}.</span>
                    {step.title}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                    {step.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Value cards ──────────────────────────────────────────── */}
      <section className="px-5 py-10 max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-8">Built for solo training</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {VALUES.map((v) => {
            const Icon = v.icon;
            return (
              <div
                key={v.title}
                className="rounded-xl border border-border bg-card p-4 space-y-2"
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${v.color}`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <p className="font-semibold text-sm">{v.title}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{v.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Scope / roadmap ──────────────────────────────────────── */}
      <section className="px-5 py-10 max-w-2xl mx-auto">
        <div className="rounded-2xl border border-border bg-card p-6 text-center space-y-4">
          <h2 className="font-bold text-lg">What's available now</h2>
          <div>
            <Badge className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 border-0 text-xs px-3 py-1">
              ✓ Squat
            </Badge>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-2">Coming soon</p>
            <div className="flex flex-wrap justify-center gap-2">
              {['OHP', 'Row', 'Bench'].map((lift) => (
                <Badge key={lift} variant="secondary" className="text-xs opacity-50">
                  {lift}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust ────────────────────────────────────────────────── */}
      <section className="px-5 py-8 max-w-2xl mx-auto text-center">
        <p className="text-sm text-muted-foreground">
          Built for lifters who train without a coach.
        </p>
        <p className="text-xs text-muted-foreground/50 mt-1">
          Early beta — actively improving with real user feedback.
        </p>
      </section>

      {/* ── Footer CTA ───────────────────────────────────────────── */}
      <section className="px-5 py-16 max-w-2xl mx-auto text-center border-t border-border">
        <h2 className="text-2xl font-bold mb-2">Start with squat analysis</h2>
        <p className="text-sm text-muted-foreground mb-7">
          Free to use during beta. No credit card required.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            className="w-full sm:w-auto px-8 h-12"
            onClick={toAuth}
          >
            Create your account
            <ArrowRight className="w-4 h-4 ml-1.5" />
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="w-full sm:w-auto h-12"
            onClick={toAuth}
          >
            Sign in
          </Button>
        </div>
        <div className="flex items-center justify-center gap-5 mt-10 text-xs text-muted-foreground/50">
          <a href="/terms" className="hover:text-muted-foreground transition-colors">
            Terms
          </a>
          <a href="/privacy" className="hover:text-muted-foreground transition-colors">
            Privacy
          </a>
        </div>
      </section>

    </div>
  );
}
