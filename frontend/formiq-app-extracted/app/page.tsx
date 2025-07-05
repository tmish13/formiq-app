"use client"

import { useState, useEffect } from "react"
import { motion, useInView } from "framer-motion"
import { Camera, TrendingUp, BookOpen, Brain, Target, ChevronRight, Lightbulb, Dumbbell } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { BottomNavigation } from "@/components/bottom-navigation"
import { useRouter } from "next/navigation"
import { LoadingSpinner } from "@/components/atoms/LoadingSpinner"
import { useRef } from "react"

const formTips = [
  "Keep your core engaged throughout squats",
  "Avoid letting knees collapse inward during lunges",
  "Focus on slow, controlled movement for better form",
  "Maintain neutral spine during deadlifts",
  "Keep shoulders back and chest up during rows",
  "Control the eccentric (lowering) phase of each rep",
  "Breathe out during the exertion phase",
  "Keep your feet planted firmly during upper body exercises",
  "Engage your glutes at the top of hip hinge movements",
  "Maintain consistent tempo throughout the set",
]

export default function HomePage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [onboardingComplete, setOnboardingComplete] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [currentStreak, setCurrentStreak] = useState(0)
  const [todayFormScore, setTodayFormScore] = useState(0)
  const [weeklyImprovement, setWeeklyImprovement] = useState(0)
  const [currentTip, setCurrentTip] = useState("")
  const [tipIndex, setTipIndex] = useState(0)
  const router = useRouter()

  const howItWorksRef = useRef(null)
  const isHowItWorksInView = useInView(howItWorksRef, { once: true, margin: "-100px" })

  useEffect(() => {
    // Set random tip on load
    const randomIndex = Math.floor(Math.random() * formTips.length)
    setCurrentTip(formTips[randomIndex])
    setTipIndex(randomIndex)

    // Check authentication and onboarding status
    const checkAuthStatus = () => {
      const authToken = localStorage.getItem("formiq-auth-token")
      const onboardingStatus = localStorage.getItem("formiq-onboarding-complete")

      if (!authToken) {
        router.push("/auth")
        return
      }

      setIsAuthenticated(true)

      if (!onboardingStatus) {
        router.push("/onboarding")
        return
      }

      setOnboardingComplete(true)

      // Load user progress data
      const savedProgress = localStorage.getItem("formiq-user-progress")
      if (savedProgress) {
        const progress = JSON.parse(savedProgress)
        setCurrentStreak(progress.streak || 0)
        setTodayFormScore(progress.todayScore || 0)
        setWeeklyImprovement(progress.weeklyImprovement || 0)
      }

      setIsLoading(false)
    }

    checkAuthStatus()
  }, [router])

  // Rotate tips every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setTipIndex((prev) => {
        const nextIndex = (prev + 1) % formTips.length
        setCurrentTip(formTips[nextIndex])
        return nextIndex
      })
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  const resetApp = () => {
    localStorage.removeItem("formiq-auth-token")
    localStorage.removeItem("formiq-onboarding-complete")
    localStorage.removeItem("formiq-user-progress")
    router.push("/auth")
  }

  // Show loading while checking auth status
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-blue-950/30 dark:to-purple-950/20">
        <LoadingSpinner />
      </div>
    )
  }

  // This component should only render if user is authenticated and onboarded
  if (!isAuthenticated || !onboardingComplete) {
    return null
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-blue-950/30 dark:to-purple-950/20 pb-20">
      <div className="px-4 py-4 space-y-6 max-w-4xl mx-auto">
        {/* Compact Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center space-y-3">
          <motion.h1
            className="text-3xl font-bold text-gray-900 dark:text-gray-100"
            animate={{
              textShadow: [
                "0 0 0px rgba(59, 130, 246, 0)",
                "0 0 8px rgba(59, 130, 246, 0.3)",
                "0 0 0px rgba(59, 130, 246, 0)",
              ],
            }}
            transition={{
              duration: 2,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 3,
            }}
          >
            Welcome to FormIQ
          </motion.h1>
          <p className="text-gray-600 dark:text-gray-400 text-base">
            AI-powered fitness form analysis at your fingertips
          </p>

          {/* Low-emphasis Reset Demo Link */}
          <button
            onClick={resetApp}
            className="text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400 transition-colors underline decoration-dotted underline-offset-2"
          >
            Reset Demo
          </button>
        </motion.div>

        {/* Hero Section - Enhanced */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl p-6 text-white overflow-hidden shadow-xl"
        >
          {/* Floating background elements */}
          <div className="absolute top-4 right-4 w-16 h-16 bg-white/10 rounded-full animate-float" />
          <div
            className="absolute bottom-4 left-4 w-12 h-12 bg-white/10 rounded-full animate-float"
            style={{ animationDelay: "1s" }}
          />
          <div
            className="absolute top-1/2 right-1/3 w-8 h-8 bg-white/10 rounded-full animate-float"
            style={{ animationDelay: "2s" }}
          />

          <div className="relative z-10">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-2xl font-bold mb-1">Perfect Your Form with AI</h2>
                <p className="text-blue-100">Get instant AI feedback on your exercise form</p>
              </div>
              {currentStreak > 0 && (
                <div className="flex items-center space-x-2 bg-white/20 rounded-full px-3 py-1">
                  <Target className="w-4 h-4 text-orange-300" />
                  <span className="font-semibold text-sm">{currentStreak}d streak</span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
              <div className="bg-white/20 rounded-xl p-3 backdrop-blur-sm">
                <div className="flex items-center space-x-2 mb-1">
                  <Brain className="w-4 h-4" />
                  <span className="text-sm font-medium">AI Analysis</span>
                </div>
                <p className="text-lg font-bold">Instant</p>
                <p className="text-xs text-blue-100">feedback on your form</p>
              </div>

              <div className="bg-white/20 rounded-xl p-3 backdrop-blur-sm">
                <div className="flex items-center space-x-2 mb-1">
                  <Target className="w-4 h-4" />
                  <span className="text-sm font-medium">Form Score</span>
                </div>
                <p className="text-lg font-bold">{todayFormScore > 0 ? `${todayFormScore}%` : "--"}</p>
                <p className="text-xs text-blue-100">
                  {weeklyImprovement > 0 ? `+${weeklyImprovement}% this week` : "Start your first analysis"}
                </p>
              </div>

              <div className="bg-white/20 rounded-xl p-3 backdrop-blur-sm">
                <div className="flex items-center space-x-2 mb-1">
                  <Camera className="w-4 h-4" />
                  <span className="text-sm font-medium">Get Started</span>
                </div>
                <p className="text-sm text-blue-100">Get Started</p>
              </div>
            </div>

            {/* Enhanced Primary CTA */}
            <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
              <Button
                size="lg"
                className="w-full bg-white text-blue-600 hover:bg-blue-50 font-bold text-lg py-4 shadow-lg hover:shadow-xl transition-all duration-300"
                onClick={() => router.push("/record")}
                style={{
                  boxShadow: "0 8px 32px rgba(255, 255, 255, 0.3)",
                }}
              >
                <Camera className="w-6 h-6 mr-3" />
                Start AI Form Analysis
              </Button>
            </motion.div>
          </div>
        </motion.div>

        {/* Quick Actions Grid */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-3"
        >
          <h3 className="text-xl font-bold text-gray-900 dark:text-white text-left">Quick Actions</h3>

          <div className="grid grid-cols-1 gap-3">
            {/* Start AI Analysis - Primary */}
            <motion.div whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}>
              <Card
                className="cursor-pointer transition-all duration-200 shadow-lg hover:shadow-xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm"
                onClick={() => router.push("/record")}
              >
                <CardContent className="p-5">
                  <div className="flex items-center space-x-4">
                    <div className="w-14 h-14 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                      <Camera className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Start AI Form Analysis</h3>
                      <p className="text-gray-600 dark:text-gray-400 text-sm">Record & analyze your form instantly</p>
                      <Badge variant="secondary" className="mt-1 text-xs">
                        Quick setup
                      </Badge>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Secondary Actions Grid - Reduced spacing */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
              {/* View Progress */}
              <motion.div whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}>
                <Card
                  className="cursor-pointer transition-all duration-200 shadow-md hover:shadow-lg bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm"
                  onClick={() => router.push("/progress")}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-r from-green-500 to-green-600 rounded-lg flex items-center justify-center shadow-md">
                        <TrendingUp className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-sm">View Progress</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">Track improvements</p>
                        {weeklyImprovement > 0 && (
                          <Badge variant="outline" className="mt-1 text-xs">
                            +{weeklyImprovement}% improvement
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>

              {/* Exercise Library */}
              <motion.div whileHover={{ scale: 1.02, y: -2 }} whileTap={{ scale: 0.98 }}>
                <Card
                  className="cursor-pointer transition-all duration-200 shadow-md hover:shadow-lg bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm"
                  onClick={() => router.push("/library")}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg flex items-center justify-center shadow-md">
                        <BookOpen className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-gray-900 dark:text-white text-sm">Exercise Library</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">Learn techniques</p>
                        <Badge variant="outline" className="mt-1 text-xs">
                          AI exercises
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </div>
        </motion.div>

        {/* How It Works Section - Moved below Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="space-y-4"
        >
          <div className="text-left">
            <div className="flex items-center space-x-2 mb-2">
              <Brain className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">How It Works</h2>
            </div>
            <p className="text-gray-600 dark:text-gray-400">
              Professional-grade movement analysis in three simple steps
            </p>
          </div>

          <Card className="bg-gradient-to-br from-blue-50/80 to-purple-50/80 dark:from-blue-950/30 dark:to-purple-950/30 border-blue-200/50 dark:border-blue-800/50 shadow-lg">
            <CardContent className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Steps */}
                <div className="space-y-4">
                  <div ref={howItWorksRef} className="space-y-3">
                    {[
                      {
                        step: "Record Exercise",
                        number: "1",
                        time: "30 sec",
                        color: "blue",
                        description: "Position your device and record your exercise form",
                      },
                      {
                        step: "AI Analysis",
                        number: "2",
                        time: "3 sec",
                        color: "purple",
                        description: "Our AI analyzes your movement patterns and form",
                      },
                      {
                        step: "Get Feedback",
                        number: "3",
                        time: "Instant",
                        color: "green",
                        description: "Receive detailed insights and improvement tips",
                      },
                    ].map((item, index) => (
                      <motion.div
                        key={item.step}
                        initial={{ opacity: 0, x: -20 }}
                        animate={isHowItWorksInView ? { opacity: 1, x: 0 } : {}}
                        transition={{ delay: index * 0.2 }}
                        className="flex items-start space-x-4 p-4 bg-white/80 dark:bg-gray-800/80 rounded-lg backdrop-blur-sm"
                      >
                        <div
                          className={`w-8 h-8 rounded-full bg-gradient-to-r from-${item.color}-500 to-${item.color}-600 flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}
                        >
                          {item.number}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-semibold text-gray-900 dark:text-white">{item.step}</span>
                            <Badge variant="secondary" className="text-xs">
                              {item.time}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">{item.description}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>

                  <div className="bg-blue-100/80 dark:bg-blue-900/40 rounded-lg p-4 backdrop-blur-sm">
                    <div className="flex items-center space-x-2 mb-2">
                      <Brain className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      <span className="font-semibold text-blue-900 dark:text-blue-200">AI Powered Analysis</span>
                    </div>
                    <p className="text-sm text-blue-800 dark:text-blue-300">
                      Advanced computer vision technology provides professional-grade form analysis
                    </p>
                  </div>
                </div>

                {/* Infographic */}
                <div className="space-y-4">
                  <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-xl flex items-center justify-center backdrop-blur-sm border border-gray-200/50 dark:border-gray-600/50">
                    <div className="text-center space-y-3">
                      <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto">
                        <Camera className="w-8 h-8 text-white" />
                      </div>
                      <div className="space-y-1">
                        <h4 className="font-semibold text-gray-900 dark:text-white">AI Form Analysis</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Real-time movement tracking</p>
                      </div>
                      <div className="flex justify-center space-x-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                        <div
                          className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"
                          style={{ animationDelay: "0.2s" }}
                        />
                        <div
                          className="w-2 h-2 bg-green-500 rounded-full animate-pulse"
                          style={{ animationDelay: "0.4s" }}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="bg-teal-50/80 dark:bg-teal-900/20 rounded-lg p-4 backdrop-blur-sm border border-teal-200/30 dark:border-teal-800/30">
                    <h4 className="font-semibold text-teal-800 dark:text-teal-200 mb-2">Trusted by Athletes</h4>
                    <p className="text-sm text-teal-700 dark:text-teal-300">
                      Join thousands improving their exercise form with AI guidance
                    </p>
                  </div>
                </div>
              </div>

              {/* CTA */}
              <motion.div className="mt-6" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button
                  size="lg"
                  className="w-full bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 font-bold text-lg py-4 shadow-lg hover:shadow-xl transition-all duration-300"
                  onClick={() => router.push("/record")}
                >
                  Start AI Form Analysis
                </Button>
              </motion.div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Progress Overview - Only show if user has data */}
        {(todayFormScore > 0 || currentStreak > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="space-y-4"
          >
            <h3 className="text-xl font-bold text-gray-900 dark:text-white text-left">Your Progress</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-md">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Form Score</span>
                    <TrendingUp className="w-4 h-4 text-green-500" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{todayFormScore}%</p>
                  <div className="flex items-center mt-2">
                    <Progress value={todayFormScore} className="flex-1 h-3 bg-gray-200 dark:bg-gray-700">
                      <div
                        className="h-full bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full transition-all duration-500"
                        style={{ width: `${todayFormScore}%` }}
                      />
                    </Progress>
                    {weeklyImprovement > 0 && (
                      <span className="text-sm text-green-600 ml-2">+{weeklyImprovement}%</span>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-md">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Current Streak</span>
                    <Target className="w-4 h-4 text-purple-500" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{currentStreak}d</p>
                  <p className="text-sm text-purple-600">Keep it up!</p>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        )}

        {/* Enhanced Form Tip Carousel */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}>
          <Card className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-md border border-gray-200/50 dark:border-gray-700/50">
            <CardContent className="p-5">
              <div className="flex items-start space-x-4">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full flex items-center justify-center shadow-md flex-shrink-0">
                  <Lightbulb className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <h4 className="font-semibold text-gray-900 dark:text-white">Daily Form Tip</h4>
                      <Dumbbell className="w-4 h-4 text-purple-500" />
                    </div>
                    <div className="flex space-x-1">
                      {formTips.map((_, index) => (
                        <div
                          key={index}
                          className={`w-2 h-2 rounded-full transition-all duration-300 ${
                            index === tipIndex ? "bg-purple-500 scale-110" : "bg-gray-300 dark:bg-gray-600"
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                  <motion.p
                    key={tipIndex}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                    className="text-base text-gray-700 dark:text-gray-300 leading-relaxed"
                  >
                    {currentTip}
                  </motion.p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <BottomNavigation activeTab="home" />
    </div>
  )
}
