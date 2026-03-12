import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronLeft,
  Check,
  Camera,
  Target,
  Dumbbell,
  CheckCircle,
  User,
  TrendingUp,
  Zap,
  Layers,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { useAuth } from '../hooks/useAuth';
import { logEvent } from '../utils/logEvent';
import { getUserPrefs, setUserPrefs } from '../utils/userPrefs';

interface OnboardingStep {
  id: number;
  title: string;
  description: string;
  content: React.ReactNode;
}

const TRAINING_STYLE_OPTIONS = [
  'Barbell & Free Weights',
  'Machines',
  'Dumbbells',
  'Mixed Equipment',
  'Bodyweight',
] as const;

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [selectedTrainingStyle, setSelectedTrainingStyle] = useState<string | null>(null);
  const [selectedExercises] = useState<string[]>(['Squats']);
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isReplay = searchParams.get('replay') === 'true';
  const user = useSelector((state: RootState) => state.auth.user);
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);
  const { completeOnboarding } = useAuth();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth');
      return;
    }
    if (user?.has_completed_onboarding && !isReplay) {
      navigate('/dashboard');
      return;
    }
    setIsLoading(false);
  }, [isAuthenticated, user, navigate, isReplay]);

  // Prefill from saved data when replaying
  useEffect(() => {
    if (isReplay && user) {
      if (user.fitness_goal) setSelectedGoal(user.fitness_goal);
      const prefs = getUserPrefs();
      if (prefs.trainingStyle) setSelectedTrainingStyle(prefs.trainingStyle);
    }
  }, [isReplay, user]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) setCurrentStep(currentStep + 1);
  };

  const handlePrevious = () => {
    if (currentStep > 0) setCurrentStep(currentStep - 1);
  };

  const handleComplete = async () => {
    try {
      setIsLoading(true);
      // Persist training style to localStorage (backend doesn't have this field yet)
      if (selectedTrainingStyle) {
        setUserPrefs({ trainingStyle: selectedTrainingStyle });
      }
      await completeOnboarding({
        fitness_goal: selectedGoal ?? undefined,
        preferred_exercises: selectedExercises.length > 0 ? selectedExercises : undefined,
      });
      logEvent('onboarding_completed', { replay: isReplay });
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
      navigate('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = async () => {
    try {
      setIsLoading(true);
      await completeOnboarding();
      logEvent('onboarding_skipped', { replay: isReplay });
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
      navigate('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const displayName: string | null = user
    ? user.full_name?.trim()
      ? user.full_name.trim().split(' ')[0]
      : user.email
      ? user.email.split('@')[0]
      : null
    : null;

  // ── Step definitions ──────────────────────────────────────────────────────

  const steps: OnboardingStep[] = [
    // ── Step 1: Welcome ─────────────────────────────────────────────────────
    {
      id: 1,
      title: displayName ? `Welcome, ${displayName}` : 'Welcome to FormIQ',
      description: 'Your AI training partner',
      content: (
        <div className="text-center space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-24 h-24 bg-gradient-to-br from-blue-600 to-purple-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <User className="w-12 h-12 text-white" />
          </motion.div>

          <div className="space-y-3">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
              Your AI training partner
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto">
              Plan workouts, track strength, and improve your form with smarter training guidance.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-6">
            {[
              { icon: <Layers className="w-6 h-6 text-blue-600" />, bg: 'bg-blue-100 dark:bg-blue-900/20', label: 'AI Training Plan' },
              { icon: <TrendingUp className="w-6 h-6 text-green-600" />, bg: 'bg-green-100 dark:bg-green-900/20', label: 'Strength Progress' },
              { icon: <Camera className="w-6 h-6 text-purple-600" />, bg: 'bg-purple-100 dark:bg-purple-900/20', label: 'Form Analysis' },
            ].map(({ icon, bg, label }, i) => (
              <motion.div
                key={label}
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 + i * 0.1 }}
              >
                <div className={`w-12 h-12 ${bg} rounded-xl flex items-center justify-center mx-auto mb-2`}>
                  {icon}
                </div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 leading-tight">{label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      ),
    },

    // ── Step 2: Primary Goal ─────────────────────────────────────────────────
    {
      id: 2,
      title: 'Set Your Goal',
      description: 'FormIQ will tailor your training guidance to your goal.',
      content: (
        <div className="space-y-5">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-green-600 to-blue-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <Target className="w-10 h-10 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              What's your primary goal?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              FormIQ will tailor your training guidance to your goal.
            </p>
          </div>

          <div className="grid gap-3">
            {[
              { title: 'Build Strength', desc: 'Progressive overload and muscle building' },
              { title: 'Improve Endurance', desc: 'Cardiovascular fitness and stamina' },
              { title: 'Lose Weight', desc: 'Burn calories and improve body composition' },
              { title: 'Perfect Form', desc: 'Master technique and prevent injuries' },
            ].map((goal, index) => (
              <motion.button
                key={goal.title}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.08 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedGoal(goal.title)}
                className={`p-4 border-2 rounded-xl transition-all duration-200 text-left group ${
                  selectedGoal === goal.title
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className={`font-semibold text-sm ${
                      selectedGoal === goal.title
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-gray-900 dark:text-white'
                    }`}>
                      {goal.title}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{goal.desc}</p>
                  </div>
                  {selectedGoal === goal.title && (
                    <Check className="w-4 h-4 text-blue-600 flex-shrink-0" />
                  )}
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      ),
    },

    // ── Step 3: Training Style Setup (NEW) ───────────────────────────────────
    {
      id: 3,
      title: 'How do you train?',
      description: 'Choose the setup that best matches how you log your workouts.',
      content: (
        <div className="space-y-5">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-indigo-600 to-blue-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <Dumbbell className="w-10 h-10 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              How do you usually train?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Choose the setup that best matches how you log your workouts.
            </p>
          </div>

          <div className="grid gap-2.5">
            {TRAINING_STYLE_OPTIONS.map((style, index) => (
              <motion.button
                key={style}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.07 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSelectedTrainingStyle(style)}
                className={`p-4 border-2 rounded-xl transition-all duration-200 text-left ${
                  selectedTrainingStyle === style
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-indigo-400 dark:hover:border-indigo-500'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`font-semibold text-sm ${
                    selectedTrainingStyle === style
                      ? 'text-indigo-600 dark:text-indigo-400'
                      : 'text-gray-900 dark:text-white'
                  }`}>
                    {style}
                  </span>
                  {selectedTrainingStyle === style && (
                    <Check className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                  )}
                </div>
              </motion.button>
            ))}
          </div>
        </div>
      ),
    },

    // ── Step 4: AI Training Guidance (NEW) ───────────────────────────────────
    {
      id: 4,
      title: 'AI Training Guidance',
      description: 'FormIQ learns from your sessions to guide your progression.',
      content: (
        <div className="space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <TrendingUp className="w-10 h-10 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              AI Training Guidance
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 max-w-xs mx-auto">
              Log your sets with exercise, equipment, weight, and reps in reserve — FormIQ does the rest.
            </p>
          </div>

          {/* What you log */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-3">
              What you log per set
            </p>
            <div className="grid grid-cols-2 gap-2">
              {[
                'Exercise type',
                'Equipment used',
                'Working weight',
                'Reps in reserve (RIR)',
              ].map(item => (
                <div key={item} className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                  <span className="text-xs text-gray-700 dark:text-gray-300">{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* What FormIQ guides */}
          <div className="grid gap-3">
            {[
              {
                icon: <Zap className="w-5 h-5 text-amber-500" />,
                bg: 'bg-amber-100 dark:bg-amber-900/20',
                title: 'Smart Progression',
                desc: 'Knows when to add load, reps, or hold steady',
              },
              {
                icon: <TrendingUp className="w-5 h-5 text-emerald-600" />,
                bg: 'bg-emerald-100 dark:bg-emerald-900/20',
                title: 'Progress Intelligence',
                desc: 'Surfaces trends across sessions automatically',
              },
              {
                icon: <Layers className="w-5 h-5 text-blue-600" />,
                bg: 'bg-blue-100 dark:bg-blue-900/20',
                title: 'Exercise Tracking',
                desc: 'Equipment-aware history for every lift',
              },
            ].map(({ icon, bg, title, desc }, i) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className="flex items-start gap-3 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              >
                <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center flex-shrink-0`}>
                  {icon}
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{title}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      ),
    },

    // ── Step 5: AI Form Analysis ─────────────────────────────────────────────
    {
      id: 5,
      title: 'AI Form Analysis',
      description: 'Record one rep to get a detailed form score and movement feedback.',
      content: (
        <div className="space-y-5">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <Camera className="w-10 h-10 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              AI Form Analysis
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 max-w-xs mx-auto">
              Record one rep to get a detailed squat form score and movement feedback.
            </p>
          </div>

          {/* Currently supported */}
          <div className="rounded-xl border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20 p-4 flex items-start gap-3">
            <Check className="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-sm text-gray-900 dark:text-white">
                Squat — available now
              </p>
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                AI scores depth, trunk stability, knee symmetry, and forward lean. Side or back angle, full body in frame.
              </p>
            </div>
          </div>

          {/* Coming later */}
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1.5">
              Coming later
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Deadlift · Bench Press · Overhead Press · Barbell Row · and more
            </p>
          </div>
        </div>
      ),
    },

    // ── Step 6: Setup Complete ───────────────────────────────────────────────
    {
      id: 6,
      title: 'Setup Complete',
      description: "You're ready to train smart.",
      content: (
        <div className="space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <CheckCircle className="w-10 h-10 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              You're ready to train smart
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Here's how to get the most out of FormIQ.
            </p>
          </div>

          {/* Checklist */}
          <div className="grid gap-3">
            {[
              {
                icon: <Layers className="w-4 h-4 text-blue-600" />,
                bg: 'bg-blue-50 dark:bg-blue-900/20',
                text: 'Log your workouts and working sets',
              },
              {
                icon: <Zap className="w-4 h-4 text-amber-500" />,
                bg: 'bg-amber-50 dark:bg-amber-900/20',
                text: 'Use RIR to guide your progression each session',
              },
              {
                icon: <Camera className="w-4 h-4 text-purple-600" />,
                bg: 'bg-purple-50 dark:bg-purple-900/20',
                text: 'Record one squat rep when you want form feedback',
              },
            ].map(({ icon, bg, text }) => (
              <div
                key={text}
                className="flex items-center gap-3 p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              >
                <div className={`w-8 h-8 ${bg} rounded-lg flex items-center justify-center flex-shrink-0`}>
                  {icon}
                </div>
                <span className="text-sm text-gray-700 dark:text-gray-300">{text}</span>
              </div>
            ))}
          </div>

          {/* Squat recording tip */}
          <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl p-4 border border-blue-200 dark:border-blue-800">
            <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
              <Camera className="w-3.5 h-3.5 text-blue-600" />
              Squat form analysis tip
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
              Side or back angle · full body visible · 3–6 seconds · one rep · steady camera · good lighting
            </p>
          </div>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const progress = ((currentStep + 1) / steps.length) * 100;
  const isLastStep = currentStep === steps.length - 1;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">

        {/* Header */}
        <motion.div className="text-center mb-8" initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="inline-flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="24" cy="24" r="20" fill="white" />
                <path
                  d="M16 22L20 26L32 14"
                  stroke="#8B5CF6"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <span className="text-2xl font-bold text-gray-900 dark:text-white">FormIQ</span>
          </div>

          <div className="space-y-1.5">
            <Progress value={progress} className="w-full h-2" />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Step {currentStep + 1} of {steps.length}
            </p>
          </div>
        </motion.div>

        {/* Main Card */}
        <motion.div
          className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl shadow-2xl p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
            >
              {/* Step header */}
              <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                  {steps[currentStep].title}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {steps[currentStep].description}
                </p>
              </div>

              <div className="mb-8">{steps[currentStep].content}</div>
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Navigation */}
        <motion.div
          className="flex items-center justify-between mt-6"
          style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 16px)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="flex items-center gap-3">
            {currentStep > 0 && (
              <Button
                onClick={handlePrevious}
                variant="outline"
                className="flex items-center gap-1.5 h-11 px-5 bg-transparent"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </Button>
            )}
            <button
              onClick={handleSkip}
              className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-sm underline underline-offset-2 transition-colors"
            >
              Skip
            </button>
          </div>

          {isLastStep ? (
            <Button
              onClick={handleComplete}
              className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:opacity-90 flex items-center gap-2 h-11 px-8 rounded-xl"
            >
              Start Training
              <CheckCircle className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              onClick={handleNext}
              className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:opacity-90 flex items-center gap-2 h-11 px-6 rounded-xl"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          )}
        </motion.div>
      </div>
    </div>
  );
}
