import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronLeft,
  Check,
  CheckCircle,
  Camera,
  Target,
  Dumbbell,
  TrendingUp,
  Zap,
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
      title: displayName ? `Hey ${displayName}` : 'Welcome to FormIQ',
      description: 'AI squat scoring + smart workout progression',
      content: (
        <div className="text-center space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto shadow-lg"
          >
            <Zap className="w-10 h-10 text-white" />
          </motion.div>

          <div className="space-y-2">
            <h3 className="text-2xl font-extrabold text-gray-900 dark:text-white leading-tight">
              Your lifts, scored by AI
            </h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm max-w-xs mx-auto">
              AI squat form scoring · smart workout progression
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-4">
            {[
              {
                icon: <Camera className="w-5 h-5 text-purple-600" />,
                bg: 'bg-purple-50 dark:bg-purple-900/20',
                title: 'AI Form Scoring',
                desc: 'Record one squat rep. Get a posture score and see where your knees travelled forward.',
              },
              {
                icon: <TrendingUp className="w-5 h-5 text-emerald-600" />,
                bg: 'bg-emerald-50 dark:bg-emerald-900/20',
                title: 'Smart Progression',
                desc: 'Log sets with RIR. FormIQ tells you when to add weight.',
              },
            ].map(({ icon, bg, title, desc }, i) => (
              <motion.div
                key={title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + i * 0.1 }}
                className={`${bg} rounded-xl p-4 text-left`}
              >
                <div className="mb-2">{icon}</div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white leading-tight">{title}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-snug">{desc}</p>
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

    // ── Step 3: Training Style ────────────────────────────────────────────────
    {
      id: 3,
      title: 'How do you train?',
      description: 'FormIQ tailors workout guidance to your setup.',
      content: (
        <div className="space-y-5">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-16 h-16 bg-gradient-to-br from-indigo-600 to-blue-600 rounded-2xl flex items-center justify-center mx-auto shadow-lg"
          >
            <Dumbbell className="w-8 h-8 text-white" />
          </motion.div>

          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              How do you usually train?
            </h3>
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
