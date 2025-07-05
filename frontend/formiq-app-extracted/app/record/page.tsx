"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import {
  Camera,
  Square,
  RotateCcw,
  CheckCircle,
  ArrowLeft,
  Lightbulb,
  Target,
  Timer,
  Video,
  Eye,
  Info,
  X,
  Play,
  CheckSquare,
  User,
  Zap,
} from "lucide-react"
import { BottomNavigation } from "@/components/bottom-navigation"
import { CTAButton } from "@/components/atoms/CTAButton"
import Link from "next/link"

type RecordingState = "setup" | "ready" | "countdown" | "recording" | "processing" | "complete"

export default function RecordPage() {
  const [recordingState, setRecordingState] = useState<RecordingState>("setup")
  const [countdown, setCountdown] = useState(3)
  const [recordingTime, setRecordingTime] = useState(0)
  const [processingProgress, setProcessingProgress] = useState(0)
  const [setupChecklist, setSetupChecklist] = useState({
    distance: false,
    lighting: false,
    visibility: false,
    stability: false,
  })
  const [currentSetupStep, setCurrentSetupStep] = useState(0)
  const [showTooltip, setShowTooltip] = useState(false)
  const [cameraError, setCameraError] = useState(false)
  const [positionGood, setPositionGood] = useState(true)
  const [processingStage, setProcessingStage] = useState(0)

  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const setupSteps = [
    {
      key: "distance" as const,
      label: "Position camera 6 feet away",
      description: "Full body should be visible",
      icon: "📏",
    },
    {
      key: "lighting" as const,
      label: "Ensure good lighting",
      description: "Avoid shadows on your body",
      icon: "💡",
    },
    {
      key: "visibility" as const,
      label: "Clear view of your form",
      description: "No obstructions in the way",
      icon: "👁️",
    },
    {
      key: "stability" as const,
      label: "Phone is stable",
      description: "Use a tripod or stable surface",
      icon: "📱",
    },
  ]

  const processingStages = [
    "Reviewing your posture and alignment...",
    "Analyzing movement patterns...",
    "Calculating your form score...",
    "Generating personalized feedback...",
  ]

  useEffect(() => {
    // Initialize camera
    initializeCamera()
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
    }
  }, [])

  useEffect(() => {
    let interval: NodeJS.Timeout

    if (recordingState === "countdown" && countdown > 0) {
      interval = setTimeout(() => setCountdown(countdown - 1), 1000)
    } else if (recordingState === "countdown" && countdown === 0) {
      setRecordingState("recording")
      setRecordingTime(0)
    }

    if (recordingState === "recording") {
      interval = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
      }, 1000)
    }

    if (recordingState === "processing") {
      interval = setInterval(() => {
        setProcessingProgress((prev) => {
          const newProgress = prev + 1.5

          // Update processing stage based on progress
          if (newProgress > 25 && processingStage < 1) setProcessingStage(1)
          if (newProgress > 50 && processingStage < 2) setProcessingStage(2)
          if (newProgress > 75 && processingStage < 3) setProcessingStage(3)

          if (newProgress >= 100) {
            setRecordingState("complete")
            return 100
          }
          return newProgress
        })
      }, 80)
    }

    return () => clearInterval(interval)
  }, [recordingState, countdown, processingStage])

  const initializeCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setCameraError(false)
    } catch (error) {
      console.error("Camera access denied:", error)
      setCameraError(true)
    }
  }

  const handleSetupCheck = (item: keyof typeof setupChecklist) => {
    setSetupChecklist((prev) => ({ ...prev, [item]: !prev[item] }))

    // Auto-advance to next step
    const completedSteps = Object.values({ ...setupChecklist, [item]: !setupChecklist[item] }).filter(Boolean).length
    setCurrentSetupStep(Math.min(completedSteps, setupSteps.length - 1))
  }

  const completedCount = Object.values(setupChecklist).filter(Boolean).length
  const isSetupComplete = completedCount === 4

  const startCountdown = () => {
    setRecordingState("countdown")
    setCountdown(3)
  }

  const stopRecording = () => {
    setRecordingState("processing")
    setProcessingProgress(0)
    setProcessingStage(0)
  }

  const cancelCountdown = () => {
    setRecordingState("ready")
    setCountdown(3)
  }

  const resetRecording = () => {
    setRecordingState("setup")
    setRecordingTime(0)
    setProcessingProgress(0)
    setProcessingStage(0)
    setCurrentSetupStep(0)
    setSetupChecklist({
      distance: false,
      lighting: false,
      visibility: false,
      stability: false,
    })
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const getSetupItemClass = (index: number, completed: boolean) => {
    if (completed) return "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
    if (index === currentSetupStep) return "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800"
    return "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700"
  }

  const renderSetupScreen = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="space-y-8"
    >
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Setup Your Recording</h2>
        <div className="flex items-center justify-between">
          <p className="text-gray-600 dark:text-gray-400">Follow the checklist for best AI analysis results</p>
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            {completedCount}/4 Complete
          </Badge>
        </div>
      </div>

      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20">
        <CardContent className="p-6">
          <div className="flex items-center space-x-4 mb-4">
            <Target className="w-6 h-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Exercise: Squat</h3>
            <Badge variant="secondary">Beginner</Badge>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            The AI will analyze your squat form including depth, stability, and tempo.
          </p>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <h3 className="font-semibold text-gray-900 dark:text-white">Setup Checklist:</h3>

        {setupSteps.map((item, index) => (
          <motion.div
            key={item.key}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
          >
            <Card
              className={`cursor-pointer transition-all duration-300 border-2 ${getSetupItemClass(index, setupChecklist[item.key])}`}
              onClick={() => handleSetupCheck(item.key)}
            >
              <CardContent className="p-4">
                <div className="flex items-center space-x-4">
                  <div
                    className={`w-12 h-12 rounded-lg flex items-center justify-center transition-all duration-300 ${
                      setupChecklist[item.key]
                        ? "bg-green-500 text-white shadow-lg"
                        : index === currentSetupStep
                          ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600"
                          : "bg-gray-200 dark:bg-gray-700 text-gray-400"
                    }`}
                  >
                    {setupChecklist[item.key] ? (
                      <CheckCircle className="w-6 h-6" />
                    ) : (
                      <span className="text-2xl">{item.icon}</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <h4
                      className={`font-medium transition-colors duration-300 ${
                        setupChecklist[item.key]
                          ? "text-green-900 dark:text-green-100"
                          : "text-gray-900 dark:text-white"
                      }`}
                    >
                      {item.label}
                    </h4>
                    <p
                      className={`text-sm transition-colors duration-300 ${
                        setupChecklist[item.key]
                          ? "text-green-700 dark:text-green-300"
                          : "text-gray-600 dark:text-gray-400"
                      }`}
                    >
                      {item.description}
                    </p>
                  </div>
                  {index === currentSetupStep && !setupChecklist[item.key] && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"
                    />
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
        <div className="bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <Lightbulb className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-900 dark:text-yellow-100 mb-1">Pro Tip</h4>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 opacity-80">
                Record 3-5 reps for the most accurate AI analysis. Focus on controlled movement.
              </p>
            </div>
          </div>
        </div>
      </div>

      <CTAButton
        label={
          isSetupComplete ? (
            <span className="flex items-center">
              <CheckSquare className="w-4 h-4 mr-2" />
              I'm Ready to Record
            </span>
          ) : (
            `Complete Setup (${completedCount}/4)`
          )
        }
        onClick={() => setRecordingState("ready")}
        variant="primary"
        size="lg"
        fullWidth
        disabled={!isSetupComplete}
      />
    </motion.div>
  )

  const renderReadyScreen = () => (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="space-y-8"
    >
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Ready to Record</h2>
        <p className="text-gray-600 dark:text-gray-400">Position yourself and start when ready</p>
      </div>

      {cameraError ? (
        <Card className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <CardContent className="p-6 text-center">
            <div className="text-red-500 mb-4">
              <Camera className="w-12 h-12 mx-auto mb-2" />
              <h3 className="font-semibold">🚫 Couldn't access camera</h3>
            </div>
            <p className="text-red-700 dark:text-red-300 mb-4">Please check permissions and try again.</p>
            <Button onClick={initializeCamera} variant="outline" className="border-red-300 text-red-700 bg-transparent">
              Try Again
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="relative aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl">
          <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />

          {/* Position guide with silhouette */}
          <div className="absolute inset-0 flex items-center justify-center">
            <motion.div
              animate={{ opacity: [0.2, 0.4, 0.2] }}
              transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
              className="relative"
            >
              {/* Human silhouette guide */}
              <div className="w-24 h-40 border-2 border-white/50 rounded-t-full rounded-b-lg flex flex-col items-center justify-end pb-2">
                <User className="w-8 h-8 text-white/50 mb-2" />
                <span className="text-white/70 text-xs bg-black/50 px-2 py-1 rounded">Stand Here</span>
              </div>
            </motion.div>
          </div>

          {/* Real-time feedback */}
          <div className="absolute top-4 left-4 right-4">
            <div className="flex items-center justify-between">
              <div className="relative">
                <motion.div
                  animate={positionGood ? { scale: [1, 1.05, 1] } : {}}
                  transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                >
                  <Badge
                    className={`${positionGood ? "bg-green-500" : "bg-yellow-500"} text-white shadow-lg cursor-pointer`}
                    onClick={() => setShowTooltip(!showTooltip)}
                  >
                    <CheckCircle className="w-3 h-3 mr-1" />
                    {positionGood ? "Good Position" : "Adjust Position"}
                    <Info className="w-3 h-3 ml-1" />
                  </Badge>
                </motion.div>

                {showTooltip && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="absolute top-full left-0 mt-2 w-64 bg-black/80 text-white p-3 rounded-lg text-xs z-10"
                  >
                    <p>
                      {positionGood
                        ? "Perfect! Your full body is visible and properly positioned for analysis."
                        : "Move back slightly so your full body is visible in the frame."}
                    </p>
                  </motion.div>
                )}
              </div>
              <Badge variant="outline" className="bg-black/50 text-white border-white/30">
                <Camera className="w-3 h-3 mr-1" />
                Ready
              </Badge>
            </div>
          </div>

          {/* Enhanced Recording Button */}
          <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2">
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 1.05 }}
              onClick={startCountdown}
              className="w-20 h-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center shadow-2xl"
            >
              <Video className="w-10 h-10 text-white" />
            </motion.button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: Timer, label: "Duration", value: "10-30 seconds", color: "blue", satisfied: true },
          { icon: Eye, label: "Visibility", value: "Full body in frame", color: "green", satisfied: positionGood },
          { icon: Target, label: "Focus", value: "Proper form", color: "purple", satisfied: true },
        ].map((item, index) => (
          <motion.div
            key={index}
            animate={
              item.satisfied
                ? {
                    boxShadow: [
                      "0 0 0 rgba(34, 197, 94, 0)",
                      "0 0 20px rgba(34, 197, 94, 0.3)",
                      "0 0 0 rgba(34, 197, 94, 0)",
                    ],
                  }
                : {}
            }
            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            className={`text-center p-4 rounded-lg transition-all duration-300 ${
              item.satisfied
                ? `bg-${item.color}-50 dark:bg-${item.color}-950/20 border border-${item.color}-200 dark:border-${item.color}-800`
                : "bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
            }`}
          >
            <item.icon
              className={`w-6 h-6 mx-auto mb-2 ${item.satisfied ? `text-${item.color}-500` : "text-gray-400"}`}
            />
            <p
              className={`font-medium mb-1 ${item.satisfied ? "text-gray-900 dark:text-white" : "text-gray-600 dark:text-gray-400"}`}
            >
              {item.label}
            </p>
            <p
              className={`text-sm ${item.satisfied ? "text-gray-600 dark:text-gray-300" : "text-gray-500 dark:text-gray-500"}`}
            >
              {item.value}
            </p>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <CTAButton
          label="Back to Setup"
          icon={<ArrowLeft className="w-4 h-4" />}
          onClick={() => setRecordingState("setup")}
          variant="outline"
          size="md"
        />
        <CTAButton
          label="Start Recording"
          icon={<Camera className="w-4 h-4" />}
          onClick={startCountdown}
          variant="accent"
          size="md"
        />
      </div>
    </motion.div>
  )

  const renderCountdownScreen = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="space-y-8"
    >
      <div className="text-center">
        <div className="flex items-center justify-between mb-4">
          <div></div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Get Ready!</h2>
          <Button variant="ghost" size="sm" onClick={cancelCountdown} className="text-gray-500 hover:text-gray-700">
            <X className="w-5 h-5" />
          </Button>
        </div>
        <p className="text-gray-600 dark:text-gray-400">Recording starts in...</p>
      </div>

      <div className="relative aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl">
        <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />

        {/* Countdown overlay - better centered */}
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/50">
          <motion.div
            key={countdown}
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 1.5, opacity: 0 }}
            className="text-8xl font-bold text-white mb-4"
          >
            {countdown}
          </motion.div>
          <p className="text-white text-lg font-medium">Get ready to move</p>
        </div>
      </div>

      <div className="text-center">
        <p className="text-gray-600 dark:text-gray-400">Stay in position and prepare to perform your squats</p>
      </div>
    </motion.div>
  )

  const renderRecordingScreen = () => (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      className="space-y-8"
    >
      <div className="text-center">
        <div className="flex items-center justify-center space-x-2 mb-3">
          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Recording</h2>
        </div>
        <p className="text-gray-600 dark:text-gray-400">Perform 3-5 controlled squats</p>
      </div>

      <div className="relative aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl">
        <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover" />

        {/* Recording indicators */}
        <div className="absolute top-4 left-4 right-4">
          <div className="flex items-center justify-between">
            <Badge className="bg-red-500 text-white animate-pulse shadow-lg">
              <div className="w-2 h-2 bg-white rounded-full mr-2" />
              REC
            </Badge>
            <Badge variant="outline" className="bg-black/50 text-white border-white/30">
              <Timer className="w-3 h-3 mr-1" />
              {formatTime(recordingTime)}
            </Badge>
          </div>
        </div>

        {/* Form hints */}
        <div className="absolute bottom-4 left-4 right-4">
          <div className="bg-black/70 rounded-lg p-4">
            <p className="text-white text-sm text-center">
              Keep your back straight • Go down slowly • Push through your heels
            </p>
          </div>
        </div>

        {/* Enhanced Stop Button */}
        <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 1.05 }}
            onClick={stopRecording}
            className="w-20 h-20 bg-gradient-to-r from-red-600 to-red-700 rounded-full flex items-center justify-center shadow-2xl"
          >
            <Square className="w-10 h-10 text-white" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  )

  const renderProcessingScreen = () => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="space-y-8"
    >
      <div className="text-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
          className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl"
        >
          <Camera className="w-8 h-8 text-white" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Analyzing Your Form</h2>
        <p className="text-gray-600 dark:text-gray-400">AI is processing your movement data...</p>
      </div>

      <div className="space-y-6">
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
          <span>Analysis Progress</span>
          <span className="font-semibold">{Math.round(processingProgress)}%</span>
        </div>
        <div className="relative">
          <Progress value={processingProgress} className="h-4" />
          <motion.div
            className="absolute top-0 left-0 h-4 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${processingProgress}%` }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          />
        </div>

        {/* Dynamic processing text */}
        <div className="text-center">
          <motion.p
            key={processingStage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-blue-600 dark:text-blue-400 font-medium"
          >
            {processingStages[processingStage]}
          </motion.p>
        </div>
      </div>

      <div className="space-y-4">
        {[
          { step: "Analyzing movement patterns", complete: processingProgress > 20 },
          { step: "Checking form alignment", complete: processingProgress > 40 },
          { step: "Measuring depth and stability", complete: processingProgress > 60 },
          { step: "Generating personalized feedback", complete: processingProgress > 80 },
        ].map((item, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
            className="flex items-center space-x-4"
          >
            <div
              className={`w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300 ${
                item.complete ? "bg-green-500 text-white shadow-lg" : "bg-gray-200 dark:bg-gray-600"
              }`}
            >
              {item.complete ? (
                <CheckCircle className="w-3 h-3" />
              ) : (
                <div className="w-2 h-2 bg-gray-400 rounded-full" />
              )}
            </div>
            <span
              className={`text-sm transition-colors duration-300 ${
                item.complete ? "text-gray-900 dark:text-white font-medium" : "text-gray-600 dark:text-gray-400"
              }`}
            >
              {item.step}
            </span>
          </motion.div>
        ))}
      </div>

      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6">
        <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-3">Did You Know?</h4>
        <p className="text-sm text-blue-700 dark:text-blue-300">
          Most users see a 20% improvement in form after their first AI analysis session!
        </p>
      </div>
    </motion.div>
  )

  const renderCompleteScreen = () => (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.1 }}
      transition={{ duration: 0.4, ease: "easeInOut" }}
      className="space-y-8"
    >
      <div className="text-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200 }}
          className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-6 shadow-xl"
        >
          <CheckCircle className="w-8 h-8 text-white" />
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">Analysis Complete!</h2>
        <p className="text-gray-600 dark:text-gray-400">Your form has been analyzed by AI</p>
      </div>

      <Card className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20">
        <CardContent className="p-8">
          <div className="flex items-center justify-between mb-4">
            <div className="text-center flex-1">
              <div className="text-5xl font-bold text-green-600 mb-2">87%</div>
              <p className="text-gray-600 dark:text-gray-400 mb-4">Overall Form Score</p>
              <Badge className="bg-green-500 text-white">Great Job!</Badge>
            </div>
            <div className="ml-4">
              <div className="w-16 h-16 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                <Play className="w-8 h-8 text-gray-500" />
              </div>
              <p className="text-xs text-gray-500 mt-1 text-center">Your recording</p>
            </div>
          </div>

          <div className="text-center">
            <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
              <Zap className="w-3 h-3 mr-1" />
              Improved by +8% from last session
            </Badge>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <CTAButton
          label="Record Again"
          icon={<RotateCcw className="w-4 h-4" />}
          onClick={resetRecording}
          variant="outline"
          size="md"
        />
        <Link href="/analysis/latest">
          <CTAButton
            label="View Analysis"
            icon={<ArrowLeft className="w-4 h-4 rotate-180" />}
            onClick={() => {}}
            variant="primary"
            size="md"
            fullWidth
          />
        </Link>
      </div>
    </motion.div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-purple-50/30 dark:from-gray-900 dark:via-blue-950/30 dark:to-purple-950/30 pb-20">
      <div className="px-4 py-6 max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Form Analysis</h1>
          <div className="w-16" />
        </div>

        {/* Content */}
        <Card className="shadow-xl border-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
          <CardContent className="p-8">
            <AnimatePresence mode="wait">
              <motion.div key={recordingState}>
                {recordingState === "setup" && renderSetupScreen()}
                {recordingState === "ready" && renderReadyScreen()}
                {recordingState === "countdown" && renderCountdownScreen()}
                {recordingState === "recording" && renderRecordingScreen()}
                {recordingState === "processing" && renderProcessingScreen()}
                {recordingState === "complete" && renderCompleteScreen()}
              </motion.div>
            </AnimatePresence>
          </CardContent>
        </Card>
      </div>

      <BottomNavigation activeTab="record" />
    </div>
  )
}
