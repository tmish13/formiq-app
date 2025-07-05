import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, Check, Camera, Target, Dumbbell, CheckCircle, User } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { useAuth } from '../hooks/useAuth';

interface OnboardingStep {
  id: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedGoal, setSelectedGoal] = useState<string | null>(null);
  const [selectedExercises, setSelectedExercises] = useState<string[]>([]);
  const navigate = useNavigate();
  const user = useSelector((state: RootState) => state.auth.user);
  const isAuthenticated = useSelector((state: RootState) => state.auth.isAuthenticated);
  const { completeOnboarding } = useAuth();

  useEffect(() => {
    // Check authentication
    if (!isAuthenticated) {
      navigate('/auth');
      return;
    }

    // Check if onboarding is already complete
    if (user?.has_completed_onboarding) {
      navigate('/dashboard');
      return;
    }

    setIsLoading(false);
  }, [isAuthenticated, navigate]);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    try {
      setIsLoading(true);
      
      // Save onboarding preferences locally
      const preferences = {
        goal: selectedGoal,
        exercises: selectedExercises,
        completedAt: new Date().toISOString(),
      };
      localStorage.setItem('formiq-onboarding-preferences', JSON.stringify(preferences));
      
      // Complete onboarding via API
      await completeOnboarding();
      
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
      // Fallback: still allow navigation on error
      navigate('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkip = async () => {
    try {
      setIsLoading(true);
      
      // Complete onboarding via API even when skipped
      await completeOnboarding();
      
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
      // Fallback: still allow navigation on error
      navigate('/dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoalSelect = (goal: string) => {
    setSelectedGoal(goal);
  };

  const handleExerciseToggle = (exercise: string) => {
    setSelectedExercises(prev => 
      prev.includes(exercise) 
        ? prev.filter(e => e !== exercise)
        : [...prev, exercise]
    );
  };

  const steps: OnboardingStep[] = [
    {
      id: 1,
      title: `Welcome${user?.firstName ? `, ${user.firstName}` : ''}`,
      description: "Let's get you started with FormIQ and perfect your exercise form with AI.",
      icon: <User className="w-8 h-8 text-blue-600" />,
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
          <div className="space-y-4">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white text-center">
              Ready to transform your workouts?
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto">
              FormIQ uses advanced AI to analyze your exercise form in real-time, providing instant feedback to help you
              train safer and more effectively.
            </p>
            <div className="grid grid-cols-3 gap-4 mt-8">
              <motion.div
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
              >
                <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Camera className="w-6 h-6 text-blue-600" />
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">AI Analysis</p>
              </motion.div>
              <motion.div
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <div className="w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Target className="w-6 h-6 text-green-600" />
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Track Progress</p>
              </motion.div>
              <motion.div
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
              >
                <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-lg flex items-center justify-center mx-auto mb-2">
                  <Dumbbell className="w-6 h-6 text-purple-600" />
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Get Stronger</p>
              </motion.div>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 2,
      title: 'Set Your Goals',
      description: 'Tell us what you want to achieve so we can personalize your experience.',
      icon: <Target className="w-8 h-8 text-green-600" />,
      content: (
        <div className="space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-24 h-24 bg-gradient-to-br from-green-600 to-blue-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <Target className="w-12 h-12 text-white" />
          </motion.div>
          <div className="space-y-4">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white text-center">
              What's your primary fitness goal?
            </h3>
            <p className="text-base text-gray-600 dark:text-gray-400 text-center mb-6">
              Select the goal that best matches your current fitness journey
            </p>
            <div className="grid gap-3">
              {[
                { title: 'Build Strength', desc: 'Focus on progressive overload and muscle building' },
                { title: 'Improve Endurance', desc: 'Enhance cardiovascular fitness and stamina' },
                { title: 'Lose Weight', desc: 'Burn calories and improve body composition' },
                { title: 'Perfect Form', desc: 'Master proper technique and prevent injuries' },
              ].map((goal, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleGoalSelect(goal.title)}
                  className={`p-4 border-2 rounded-lg transition-all duration-200 text-left group ${
                    selectedGoal === goal.title
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex-1">
                      <h4 className={`font-medium ${
                        selectedGoal === goal.title
                          ? 'text-blue-600 dark:text-blue-400'
                          : 'text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400'
                      }`}>
                        {goal.title}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{goal.desc}</p>
                    </div>
                    {selectedGoal === goal.title && (
                      <Check className="w-5 h-5 text-blue-600" />
                    )}
                  </div>
                </motion.button>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 3,
      title: 'Choose Your Focus',
      description: 'Select the exercises you want to improve with AI-powered form analysis.',
      icon: <Dumbbell className="w-8 h-8 text-purple-600" />,
      content: (
        <div className="space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-24 h-24 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <Dumbbell className="w-12 h-12 text-white" />
          </motion.div>
          <div className="space-y-4">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white text-center">
              Which exercises interest you most?
            </h3>
            <p className="text-base text-gray-600 dark:text-gray-400 text-center mb-6">
              Pick exercises you'd like to master with AI-powered form analysis
            </p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { name: 'Squats' },
                { name: 'Deadlifts' },
                { name: 'Push-ups' },
                { name: 'Pull-ups' },
                { name: 'Bench Press' },
                { name: 'Planks' },
              ].map((exercise, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleExerciseToggle(exercise.name)}
                  className={`p-3 border-2 rounded-lg transition-all duration-200 text-center group ${
                    selectedExercises.includes(exercise.name)
                      ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-purple-500 dark:hover:border-purple-400'
                  }`}
                >
                  <div className="space-y-2">
                    <span className={`text-sm font-medium ${
                      selectedExercises.includes(exercise.name)
                        ? 'text-purple-600 dark:text-purple-400'
                        : 'text-gray-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400'
                    }`}>
                      {exercise.name}
                    </span>
                    {selectedExercises.includes(exercise.name) && (
                      <Check className="w-4 h-4 text-purple-600 mx-auto" />
                    )}
                  </div>
                </motion.button>
              ))}
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 4,
      title: 'Setup Complete',
      description: "You're all set! Here's what you can do next to get the most out of FormIQ.",
      icon: <CheckCircle className="w-8 h-8 text-green-600" />,
      content: (
        <div className="space-y-6">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-24 h-24 bg-gradient-to-br from-green-600 to-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-lg"
          >
            <CheckCircle className="w-12 h-12 text-white" />
          </motion.div>
          <div className="space-y-6">
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white text-center">
              Ready to start your journey
            </h3>

            {/* Professional Setup Guide */}
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl p-6 border border-blue-200 dark:border-blue-800">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
                <Camera className="w-5 h-5 mr-2 text-blue-600" />
                Quick Setup Guide
              </h4>

              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Position your camera</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Place your device 6-8 feet away at chest height
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Ensure good lighting</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Natural light works best, avoid backlighting
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">Clear your space</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Make sure you have room to move freely</p>
                  </div>
                </div>
              </div>

              {/* Camera positioning placeholder */}
              <div className="mt-6 bg-white dark:bg-gray-800 rounded-lg p-4 border-2 border-dashed border-gray-300 dark:border-gray-600">
                <div className="text-center space-y-2">
                  <Camera className="w-8 h-8 text-gray-400 mx-auto" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Camera positioning guide image will appear here
                  </p>
                </div>
              </div>
            </div>

            {/* Next Steps */}
            <div className="grid gap-3">
              <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Record your first exercise</span>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Get AI-powered form analysis</span>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <Check className="w-5 h-5 text-green-600 flex-shrink-0" />
                <span className="text-sm text-gray-600 dark:text-gray-400">Track your progress over time</span>
              </div>
            </div>
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

          <div className="space-y-2">
            <Progress value={progress} className="w-full h-3" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Step {currentStep + 1} of {steps.length}
            </p>
          </div>
        </motion.div>

        {/* Main Content */}
        <motion.div
          className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl shadow-2xl p-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{
                duration: 0.4,
                ease: 'easeInOut',
                type: 'tween',
              }}
            >
              <div className="text-center mb-6">
                <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">{steps[currentStep].title}</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">{steps[currentStep].description}</p>
              </div>

              <div className="mb-8">{steps[currentStep].content}</div>
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Navigation */}
        <motion.div
          className="flex items-center justify-between mt-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <div className="flex space-x-3">
            {currentStep > 0 && (
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  onClick={handlePrevious}
                  variant="outline"
                  className="flex items-center space-x-2 h-12 px-6 bg-transparent"
                >
                  <ChevronLeft className="w-4 h-4" />
                  <span>Previous</span>
                </Button>
              </motion.div>
            )}

            <motion.button
              whileHover={{ scale: 1.02 }}
              onClick={handleSkip}
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-sm underline underline-offset-2"
            >
              Skip for now
            </motion.button>
          </div>

          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            {currentStep === steps.length - 1 ? (
              <Button
                onClick={handleComplete}
                className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:scale-105 hover:shadow-xl flex items-center space-x-2 h-12 px-8 rounded-lg"
              >
                <span>Get Started</span>
                <CheckCircle className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                onClick={handleNext}
                className="bg-gradient-to-r from-purple-500 to-indigo-600 hover:scale-105 hover:shadow-xl flex items-center space-x-2 h-12 px-6 rounded-lg"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </Button>
            )}
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}