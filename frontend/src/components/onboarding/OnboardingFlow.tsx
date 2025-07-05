"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronLeft, ChevronRight, CheckCircle, Camera, Target, Users, Brain, Zap, AlertCircle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/atoms/Badge"
import { CTAButton } from "@/components/atoms/CTAButton"
import { Heading2 } from "@/components/atoms/Typography"

interface OnboardingFlowProps {
  onComplete: () => void
}

const exercises = [
  {
    id: "squat",
    name: "Squat",
    difficulty: "Beginner",
    duration: "5-10 min",
    description: "Perfect for learning proper form fundamentals",
    icon: "🏋️",
    recommended: true,
  },
  {
    id: "pushup",
    name: "Push-up",
    difficulty: "Beginner",
    duration: "3-8 min",
    description: "Great for upper body strength assessment",
    icon: "💪",
  },
  {
    id: "deadlift",
    name: "Deadlift",
    difficulty: "Intermediate",
    duration: "8-12 min",
    description: "Advanced movement for experienced users",
    icon: "🏃",
  },
]

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [selectedExercise, setSelectedExercise] = useState<string | null>(null)
  const [isCompleting, setIsCompleting] = useState(false)
  const [showSkipConfirmation, setShowSkipConfirmation] = useState(false)

  const totalSteps = 4

  const canProceed = () => {
    switch (currentStep) {
      case 1:
      case 2:
        return true
      case 3:
        return selectedExercise !== null
      case 4:
        return true
      default:
        return false
    }
  }

  const handleNext = () => {
    if (currentStep < totalSteps && canProceed()) {
      setCurrentStep(currentStep + 1)
    } else if (currentStep === totalSteps) {
      handleComplete()
    }
  }

  const handleComplete = async () => {
    setIsCompleting(true)

    // Save onboarding completion
    localStorage.setItem("formiq-onboarding-complete", "true")
    if (selectedExercise) {
      localStorage.setItem("formiq-selected-exercise", selectedExercise)
    }

    // Brief delay for UX
    await new Promise((resolve) => setTimeout(resolve, 500))

    onComplete()
  }

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    setShowSkipConfirmation(true)
  }

  const confirmSkip = () => {
    localStorage.setItem("formiq-onboarding-complete", "true")
    onComplete()
  }

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <motion.div
            key="step1"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="text-center space-y-8 athletic-silhouette"
          >
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-6 animate-float">
              <Target className="w-10 h-10 text-white" />
            </div>

            <h1 className="text-4xl font-bold text-high-contrast">Welcome to FormIQ</h1>
            <p className="text-base text-soft-contrast/70 max-w-md mx-auto">
              AI-powered form analysis that helps you exercise safely and effectively
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-2xl mx-auto mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="onboarding-card"
              >
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Camera className="w-6 h-6 text-blue-600" />
                  </div>
                  <h3 className="font-semibold text-high-contrast mb-3">Real-time Analysis</h3>
                  <p className="text-sm text-soft-contrast">Get instant feedback on your form</p>
                </CardContent>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="onboarding-card"
              >
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Target className="w-6 h-6 text-green-600" />
                  </div>
                  <h3 className="font-semibold text-high-contrast mb-3">Personalized Tips</h3>
                  <p className="text-sm text-soft-contrast">AI coaching tailored to you</p>
                </CardContent>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="onboarding-card"
              >
                <CardContent className="p-6 text-center">
                  <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Users className="w-6 h-6 text-purple-600" />
                  </div>
                  <h3 className="font-semibold text-high-contrast mb-3">Track Progress</h3>
                  <p className="text-sm text-soft-contrast">Monitor your improvement over time</p>
                </CardContent>
              </motion.div>
            </div>

            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6 max-w-md mx-auto enhanced-card">
              <div className="flex items-center space-x-3 text-blue-700 dark:text-blue-300">
                <Zap className="w-5 h-5" />
                <span className="font-medium">Join our growing community of fitness enthusiasts</span>
              </div>
            </div>
          </motion.div>
        )

      case 2:
        return (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="text-center space-y-8"
          >
            <h1 className="text-4xl font-bold text-high-contrast">How AI Analysis Works</h1>
            <p className="text-base text-soft-contrast/70 max-w-md mx-auto">
              Understanding the technology behind your form feedback
            </p>

            <div className="relative max-w-lg mx-auto">
              <div className="aspect-video bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/20 dark:to-purple-900/20 rounded-xl overflow-hidden enhanced-card">
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-center">
                    <motion.div
                      animate={{ scale: [1, 1.1, 1] }}
                      transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                      className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl"
                    >
                      <Brain className="w-10 h-10 text-white" />
                    </motion.div>
                    <h3 className="text-lg font-semibold text-high-contrast mb-3">AI Computer Vision</h3>
                    <p className="text-sm text-soft-contrast">Advanced movement analysis technology</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6 max-w-md mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="text-center"
              >
                <div className="text-2xl font-bold text-blue-600 mb-2">30s</div>
                <div className="text-sm text-soft-contrast">Record Time</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-center"
              >
                <div className="text-2xl font-bold text-purple-600 mb-2">3s</div>
                <div className="text-sm text-soft-contrast">Analysis Time</div>
              </motion.div>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="text-center"
              >
                <div className="text-2xl font-bold text-green-600 mb-2">95%</div>
                <div className="text-sm text-soft-contrast">Accuracy</div>
              </motion.div>
            </div>

            <div className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg p-6 max-w-md mx-auto enhanced-card">
              <p className="text-green-700 dark:text-green-300 text-sm">
                <strong>How it works:</strong> Our AI analyzes your movement patterns and provides specific feedback to
                improve your form
              </p>
            </div>
          </motion.div>
        )

      case 3:
        return (
          <motion.div
            key="step3"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="space-y-8"
          >
            <div className="text-center">
              <h1 className="text-4xl font-bold text-high-contrast mb-3">Choose Your First Exercise</h1>
              <p className="text-base text-soft-contrast/70">Select an exercise to start your form analysis journey</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
              {exercises.map((exercise, index) => (
                <motion.div
                  key={exercise.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.02, y: -4 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setSelectedExercise(exercise.id)
                    // Add micro-interaction
                    const element = document.getElementById(`exercise-${exercise.id}`)
                    if (element) {
                      element.classList.add("animate-bounce-micro")
                      setTimeout(() => element.classList.remove("animate-bounce-micro"), 300)
                    }
                  }}
                  className={`
                    onboarding-card cursor-pointer
                    ${selectedExercise === exercise.id ? "selected" : ""}
                  `}
                  id={`exercise-${exercise.id}`}
                >
                  <CardContent className="p-0">
                    <div className="relative">
                      <div className="w-full h-32 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center">
                        <span className="text-4xl">{exercise.icon}</span>
                      </div>
                      {exercise.recommended && (
                        <div className="absolute top-3 left-3">
                          <Badge label="Recommended" variant="success" size="sm" />
                        </div>
                      )}
                      {selectedExercise === exercise.id && (
                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="absolute top-3 right-3">
                          <CheckCircle className="w-6 h-6 text-indigo-500 bg-white rounded-full" />
                        </motion.div>
                      )}
                    </div>

                    <div className="p-6">
                      <h3 className="font-bold text-lg text-high-contrast mb-3">{exercise.name}</h3>
                      <div className="flex items-center space-x-3 mb-4">
                        <Badge
                          label={exercise.difficulty}
                          variant={exercise.difficulty === "Beginner" ? "success" : "warning"}
                          size="sm"
                        />
                        <span className="text-sm text-soft-contrast">{exercise.duration}</span>
                      </div>
                      <p className="text-sm text-soft-contrast">{exercise.description}</p>
                    </div>
                  </CardContent>
                </motion.div>
              ))}
            </div>

            {selectedExercise && (
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6 max-w-md mx-auto enhanced-card">
                  <p className="text-blue-700 dark:text-blue-300">
                    Great choice! We'll start with{" "}
                    <strong>{exercises.find((e) => e.id === selectedExercise)?.name}</strong>
                  </p>
                </div>
              </motion.div>
            )}
          </motion.div>
        )

      case 4:
        return (
          <motion.div
            key="step4"
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            className="space-y-8"
          >
            <div className="text-center">
              <h1 className="text-4xl font-bold text-high-contrast mb-3">Camera Setup</h1>
              <p className="text-base text-soft-contrast/70">Position yourself for the best analysis results</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-4xl mx-auto">
              {/* Professional Image Placeholder */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.1 }}
                className="order-2 lg:order-1"
              >
                <Card className="h-full enhanced-card">
                  <CardContent className="p-8">
                    <div className="aspect-video bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg flex items-center justify-center mb-6">
                      <div className="text-center">
                        <Camera className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-float" />
                        <p className="text-soft-contrast">Professional positioning guide image will be added here</p>
                      </div>
                    </div>
                    <Heading2 className="text-high-contrast mb-3">Optimal Camera Position</Heading2>
                    <p className="text-soft-contrast">
                      Position your camera at chest height, 6-8 feet away, with your full body visible in the frame.
                    </p>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Setup Checklist */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="order-1 lg:order-2"
              >
                <Card className="h-full enhanced-card">
                  <CardContent className="p-8">
                    <Heading2 className="text-high-contrast mb-6">Setup Checklist</Heading2>
                    <div className="space-y-5">
                      {[
                        "Camera at chest height",
                        "6-8 feet distance from camera",
                        "Full body visible in frame",
                        "Good lighting on your body",
                        "Clear space around you",
                        "Phone/camera is stable",
                      ].map((item, index) => (
                        <motion.div
                          key={index}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: index * 0.1 + 0.3 }}
                          className="flex items-center space-x-4"
                        >
                          <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                          <span className="text-soft-contrast">{item}</span>
                        </motion.div>
                      ))}
                    </div>

                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.8 }}
                      className="mt-8 p-6 bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-lg enhanced-card"
                    >
                      <div className="flex items-center space-x-3 text-green-700 dark:text-green-300">
                        <CheckCircle className="w-5 h-5" />
                        <span className="font-medium">You're all set!</span>
                      </div>
                      <p className="text-sm text-green-600 dark:text-green-400 mt-2">
                        Ready to start your first form analysis
                      </p>
                    </motion.div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </motion.div>
        )

      default:
        return null
    }
  }

  return (
    <div className="min-h-screen fitness-bg flex items-center justify-center p-4">
      <div className="w-full max-w-6xl">
        {/* Progress Bar */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-12">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-soft-contrast">
              Step {currentStep} of {totalSteps}
            </span>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-soft-contrast">
                {Math.round((currentStep / totalSteps) * 100)}%
              </span>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleSkip}
                className="text-sm text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline underline-offset-2"
              >
                Skip
              </motion.button>
            </div>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <motion.div
              className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full progress-enhanced"
              initial={{ width: 0 }}
              animate={{ width: `${(currentStep / totalSteps) * 100}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            />
          </div>
        </motion.div>

        {/* Step Content */}
        <div className="mb-12">
          <AnimatePresence mode="wait">{renderStep()}</AnimatePresence>
        </div>

        {/* Navigation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex items-center justify-between"
        >
          <CTAButton
            label="Back"
            icon={<ChevronLeft className="w-4 h-4" />}
            onClick={handleBack}
            variant="outline"
            disabled={currentStep === 1}
          />

          <div className="flex space-x-2">
            {Array.from({ length: totalSteps }, (_, i) => (
              <motion.div
                key={i}
                className={`w-3 h-3 rounded-full transition-colors ${
                  i + 1 <= currentStep ? "bg-blue-500" : "bg-gray-300 dark:bg-gray-600"
                }`}
                whileHover={{ scale: 1.2 }}
              />
            ))}
          </div>

          <CTAButton
            label={currentStep === totalSteps ? "Get Started" : "Continue"}
            icon={<ChevronRight className="w-4 h-4" />}
            onClick={handleNext}
            variant="primary"
            disabled={!canProceed()}
            loading={isCompleting}
          />
        </motion.div>
      </div>

      {/* Skip Confirmation Modal */}
      <AnimatePresence>
        {showSkipConfirmation && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="loading-overlay"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="loading-content max-w-md"
            >
              <div className="w-12 h-12 bg-yellow-100 dark:bg-yellow-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-6 h-6 text-yellow-600" />
              </div>
              <h3 className="text-lg font-semibold text-high-contrast mb-3">Skip Personalization?</h3>
              <p className="text-soft-contrast mb-6">
                Are you sure you want to skip personalization? You can always set this up later in your Profile.
              </p>
              <div className="flex space-x-3">
                <CTAButton label="Go Back" onClick={() => setShowSkipConfirmation(false)} variant="outline" size="md" />
                <CTAButton label="Skip for Now" onClick={confirmSkip} variant="primary" size="md" />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
