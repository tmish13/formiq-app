"use client"

import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Camera,
  Upload,
  Pause,
  RotateCcw,
  CheckCircle,
  Eye,
  Target,
  Brain,
  Sparkles,
  AlertTriangle,
  Activity,
  Zap,
  BarChart3,
} from "lucide-react"

const exercises = [
  { value: "squat", label: "Squat", icon: "🏋️", joints: ["Hip", "Knee", "Ankle", "Spine"] },
  { value: "deadlift", label: "Deadlift", icon: "💪", joints: ["Hip", "Knee", "Spine", "Shoulder"] },
  { value: "bench-press", label: "Bench Press", icon: "🏃", joints: ["Shoulder", "Elbow", "Wrist", "Spine"] },
  { value: "overhead-press", label: "Overhead Press", icon: "🤸", joints: ["Shoulder", "Elbow", "Spine", "Hip"] },
  { value: "row", label: "Bent-Over Row", icon: "🚣", joints: ["Shoulder", "Elbow", "Spine", "Hip"] },
]

const analysisResults = {
  overallScore: 85,
  confidence: 94,
  repsAnalyzed: 5,
  totalFrames: 150,
  processingTime: 2.3,
  breakdown: [
    {
      aspect: "Depth",
      score: 92,
      feedback: "Excellent depth achieved - hitting parallel consistently",
      status: "excellent",
      frames: [45, 67, 89, 112, 134],
      improvement: "+8% from last session",
    },
    {
      aspect: "Knee Tracking",
      score: 68,
      feedback: "Knees cave inward 15° during ascent - focus on external rotation",
      status: "warning",
      frames: [23, 56, 78, 101, 123],
      improvement: "-2% from last session",
    },
    {
      aspect: "Back Position",
      score: 88,
      feedback: "Good neutral spine maintained throughout movement",
      status: "good",
      frames: [12, 34, 56, 78, 90],
      improvement: "+5% from last session",
    },
    {
      aspect: "Foot Position",
      score: 82,
      feedback: "Stance could be 2-3 inches wider for better stability",
      status: "good",
      frames: [0, 30, 60, 90, 120],
      improvement: "+3% from last session",
    },
  ],
  recommendations: [
    {
      priority: "high",
      title: "Knee Valgus Correction",
      description: "Focus on pushing knees out during the descent. Try the 'spread the floor' cue.",
      exercise: "Wall sits with external rotation focus",
      duration: "2-3 sets of 30 seconds",
    },
    {
      priority: "medium",
      title: "Stance Width Optimization",
      description: "Consider a slightly wider stance (shoulder-width + 2-3 inches) for better stability.",
      exercise: "Bodyweight squats with various stance widths",
      duration: "Find your optimal position",
    },
    {
      priority: "low",
      title: "Tempo Control",
      description: "Great job maintaining controlled tempo. Continue with 2-1-2 tempo pattern.",
      exercise: "Continue current tempo work",
      duration: "Maintain consistency",
    },
  ],
  biomechanics: {
    peakForce: "1.8x bodyweight",
    powerOutput: "850W average",
    rangeOfMotion: "95° hip flexion",
    asymmetry: "3% left-right imbalance",
  },
  comparison: {
    personalBest: 92,
    averageUser: 76,
    eliteLevel: 95,
  },
}

const poseKeypoints = [
  { joint: "Left Knee", angle: 87, optimal: "85-95°", status: "good" },
  { joint: "Right Knee", angle: 82, optimal: "85-95°", status: "warning" },
  { joint: "Hip", angle: 95, optimal: "90-100°", status: "excellent" },
  { joint: "Ankle", angle: 78, optimal: "75-85°", status: "good" },
  { joint: "Spine", angle: 12, optimal: "0-15°", status: "excellent" },
]

export default function FormAnalysis() {
  const [selectedExercise, setSelectedExercise] = useState("")
  const [isRecording, setIsRecording] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasResults, setHasResults] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [currentFrame, setCurrentFrame] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isAnalyzing) {
      const interval = setInterval(() => {
        setAnalysisProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval)
            setIsAnalyzing(false)
            setHasResults(true)
            return 100
          }
          return prev + 2
        })
      }, 100)
      return () => clearInterval(interval)
    }
  }, [isAnalyzing])

  const handleStartRecording = () => {
    if (!selectedExercise) return
    setIsRecording(true)
    const timer = setInterval(() => {
      setRecordingTime((prev) => prev + 1)
    }, 1000)

    setTimeout(() => {
      clearInterval(timer)
      setIsRecording(false)
      setIsAnalyzing(true)
      setAnalysisProgress(0)
    }, 8000)
  }

  const handleFileUpload = () => {
    fileInputRef.current?.click()
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "excellent":
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case "good":
        return <CheckCircle className="w-4 h-4 text-blue-500" />
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      case "poor":
        return <AlertTriangle className="w-4 h-4 text-red-500" />
      default:
        return <CheckCircle className="w-4 h-4 text-gray-400" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "bg-red-100 text-red-800 border-red-200"
      case "medium":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "low":
        return "bg-green-100 text-green-800 border-green-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Enhanced Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Brain className="w-5 h-5 text-purple-600" />
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">AI Form Analysis</h1>
              </div>
              {hasResults && (
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  <Sparkles className="w-3 h-3 mr-1" />
                  {analysisResults.confidence}% AI Confidence
                </Badge>
              )}
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="outline" size="sm">
                <BarChart3 className="w-4 h-4 mr-2" />
                Analysis History
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!hasResults ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Enhanced Recording Section */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Eye className="w-5 h-5 text-blue-600" />
                    <span>AI-Powered Form Analysis</span>
                  </CardTitle>
                  <CardDescription>Advanced pose detection with real-time biomechanical feedback</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Exercise Selection with Joint Info */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Select Exercise for Analysis
                    </label>
                    <Select value={selectedExercise} onValueChange={setSelectedExercise}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose exercise to analyze with AI" />
                      </SelectTrigger>
                      <SelectContent>
                        {exercises.map((exercise) => (
                          <SelectItem key={exercise.value} value={exercise.value}>
                            <div className="flex items-center justify-between w-full">
                              <div className="flex items-center space-x-2">
                                <span>{exercise.icon}</span>
                                <span>{exercise.label}</span>
                              </div>
                              <Badge variant="outline" className="ml-2 text-xs">
                                {exercise.joints.length} joints tracked
                              </Badge>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedExercise && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {exercises
                          .find((e) => e.value === selectedExercise)
                          ?.joints.map((joint, index) => (
                            <Badge key={index} variant="secondary" className="text-xs">
                              {joint}
                            </Badge>
                          ))}
                      </div>
                    )}
                  </div>

                  {/* Enhanced Video Preview Area */}
                  <div className="aspect-video bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center border-2 border-dashed border-gray-300 dark:border-gray-600 relative overflow-hidden">
                    {isRecording ? (
                      <div className="text-center">
                        <div className="relative">
                          <div className="w-20 h-20 bg-red-500 rounded-full flex items-center justify-center mb-4 mx-auto animate-pulse">
                            <div className="w-8 h-8 bg-white rounded-full" />
                          </div>
                          <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                            <Eye className="w-3 h-3 text-white" />
                          </div>
                        </div>
                        <p className="text-lg font-medium text-gray-900 dark:text-white">AI Recording...</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">{formatTime(recordingTime)}</p>
                        <div className="mt-2 flex items-center justify-center space-x-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                          <span className="text-xs text-green-600">30+ joints tracking</span>
                        </div>
                      </div>
                    ) : isAnalyzing ? (
                      <div className="text-center">
                        <div className="w-20 h-20 bg-purple-500 rounded-full flex items-center justify-center mb-4 mx-auto">
                          <Brain className="w-10 h-10 text-white animate-pulse" />
                        </div>
                        <p className="text-lg font-medium text-gray-900 dark:text-white">AI Processing...</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                          Analyzing {analysisResults.totalFrames} frames • {analysisResults.repsAnalyzed} reps detected
                        </p>
                        <div className="w-64 mx-auto space-y-2">
                          <Progress value={analysisProgress} className="h-2" />
                          <div className="flex justify-between text-xs text-gray-500">
                            <span>Pose Detection</span>
                            <span>{analysisProgress}%</span>
                          </div>
                        </div>
                        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                          <div className="flex items-center justify-center space-x-1">
                            <div className="w-2 h-2 bg-blue-500 rounded-full" />
                            <span>Joint Tracking</span>
                          </div>
                          <div className="flex items-center justify-center space-x-1">
                            <div className="w-2 h-2 bg-green-500 rounded-full" />
                            <span>Biomechanics</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center">
                        <div className="relative">
                          <Camera className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                          <div className="absolute -top-1 -right-1 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                            <Sparkles className="w-3 h-3 text-white" />
                          </div>
                        </div>
                        <p className="text-lg font-medium text-gray-900 dark:text-white">Ready for AI Analysis</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Position yourself in frame for real-time pose detection
                        </p>
                        {selectedExercise && (
                          <div className="mt-3 inline-flex items-center space-x-2 px-3 py-1 bg-purple-100 dark:bg-purple-900/20 rounded-full">
                            <Brain className="w-3 h-3 text-purple-600" />
                            <span className="text-xs text-purple-700 dark:text-purple-300">
                              AI optimized for {exercises.find((e) => e.value === selectedExercise)?.label}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Enhanced Action Buttons */}
                  <div className="flex space-x-4">
                    <Button
                      onClick={handleStartRecording}
                      disabled={!selectedExercise || isRecording || isAnalyzing}
                      className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                    >
                      {isRecording ? (
                        <>
                          <Pause className="w-4 h-4 mr-2" />
                          Stop Recording
                        </>
                      ) : (
                        <>
                          <Brain className="w-4 h-4 mr-2" />
                          Start AI Analysis
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleFileUpload}
                      disabled={isRecording || isAnalyzing}
                      className="flex-1 bg-transparent"
                    >
                      <Upload className="w-4 h-4 mr-2" />
                      Upload Video
                    </Button>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        setIsAnalyzing(true)
                        setAnalysisProgress(0)
                      }
                    }}
                  />
                </CardContent>
              </Card>
            </div>

            {/* Enhanced Instructions & AI Features */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Sparkles className="w-5 h-5 text-purple-600" />
                    <span>AI Analysis Features</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 gap-4">
                    <div className="flex items-start space-x-3 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                      <Brain className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">Real-time Pose Detection</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          30+ joint tracking with sub-degree accuracy
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <BarChart3 className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">Biomechanical Analysis</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Force vectors, power output, and movement efficiency
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                      <Target className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">Personalized Corrections</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          AI-generated cues based on your specific movement patterns
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Eye className="w-5 h-5 text-blue-600" />
                    <span>Recording Guidelines</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-start space-x-3">
                      <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-xs font-medium text-blue-600 dark:text-blue-400">1</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">Full Body Visibility</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Ensure your entire body is visible with good lighting for optimal AI tracking
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3">
                      <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-xs font-medium text-blue-600 dark:text-blue-400">2</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">Optimal Camera Angle</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Side view for squats/deadlifts, front view for overhead movements
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3">
                      <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                        <span className="text-xs font-medium text-blue-600 dark:text-blue-400">3</span>
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white text-sm">Rep Quality</h4>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Perform 3-5 controlled reps for comprehensive AI analysis
                        </p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          /* Enhanced Analysis Results */
          <div className="space-y-8">
            {/* AI Analysis Header */}
            <Card className="bg-gradient-to-r from-purple-500 to-blue-600 text-white border-0">
              <CardContent className="p-8">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center">
                        <Brain className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h2 className="text-2xl font-bold">AI Analysis Complete</h2>
                        <p className="text-purple-100">
                          Processed in {analysisResults.processingTime}s • {analysisResults.confidence}% confidence
                        </p>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold">{analysisResults.repsAnalyzed}</div>
                        <div className="text-xs text-purple-100">Reps Analyzed</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold">{analysisResults.totalFrames}</div>
                        <div className="text-xs text-purple-100">Frames Processed</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold">30+</div>
                        <div className="text-xs text-purple-100">Joints Tracked</div>
                      </div>
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="inline-flex items-center justify-center w-24 h-24 bg-white/20 rounded-full mb-4">
                      <span className="text-3xl font-bold text-white">{analysisResults.overallScore}</span>
                    </div>
                    <p className="text-purple-100">Overall Form Score</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Detailed Breakdown with AI Insights */}
              <div className="lg:col-span-2 space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Target className="w-5 h-5 text-purple-600" />
                      <span>Detailed Form Breakdown</span>
                    </CardTitle>
                    <CardDescription>AI-powered analysis of each movement component</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {analysisResults.breakdown.map((item, index) => (
                      <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center space-x-3">
                            {getStatusIcon(item.status)}
                            <div>
                              <h4 className="font-medium text-gray-900 dark:text-white">{item.aspect}</h4>
                              <p className="text-xs text-gray-500 dark:text-gray-400">
                                Analyzed across {item.frames.length} key frames
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-xl font-semibold text-gray-900 dark:text-white">{item.score}%</div>
                            <div className="text-xs text-green-600">{item.improvement}</div>
                          </div>
                        </div>
                        <Progress value={item.score} className="h-2 mb-3" />
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">{item.feedback}</p>

                        {/* Frame Analysis */}
                        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Key Frames:</p>
                          <div className="flex space-x-2">
                            {item.frames.map((frame, idx) => (
                              <div key={idx} className="text-xs bg-white dark:bg-gray-600 px-2 py-1 rounded">
                                {frame}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                {/* AI Recommendations */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Sparkles className="w-5 h-5 text-blue-600" />
                      <span>AI-Generated Recommendations</span>
                    </CardTitle>
                    <CardDescription>Personalized corrections based on your movement patterns</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {analysisResults.recommendations.map((rec, index) => (
                        <div key={index} className={`border-l-4 p-4 rounded-lg ${getPriorityColor(rec.priority)}`}>
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="font-medium">{rec.title}</h4>
                            <Badge variant="outline" className="text-xs">
                              {rec.priority} priority
                            </Badge>
                          </div>
                          <p className="text-sm mb-3">{rec.description}</p>
                          <div className="bg-white/50 dark:bg-gray-800/50 rounded p-3">
                            <p className="text-xs font-medium mb-1">Recommended Exercise:</p>
                            <p className="text-xs">{rec.exercise}</p>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{rec.duration}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Enhanced Sidebar */}
              <div className="space-y-6">
                {/* Pose Keypoints */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Activity className="w-5 h-5 text-green-600" />
                      <span>Joint Analysis</span>
                    </CardTitle>
                    <CardDescription>Real-time joint angle measurements</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {poseKeypoints.map((point, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded"
                        >
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(point.status)}
                            <div>
                              <span className="text-sm font-medium">{point.joint}</span>
                              <p className="text-xs text-gray-500">{point.optimal}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <span className="text-sm font-semibold">{point.angle}°</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Biomechanics Data */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Zap className="w-5 h-5 text-yellow-600" />
                      <span>Biomechanics</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-center p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                      <div className="text-lg font-bold text-yellow-600">{analysisResults.biomechanics.peakForce}</div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Peak Force</div>
                    </div>
                    <div className="text-center p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                      <div className="text-lg font-bold text-blue-600">{analysisResults.biomechanics.powerOutput}</div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Power Output</div>
                    </div>
                    <div className="text-center p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                      <div className="text-lg font-bold text-purple-600">
                        {analysisResults.biomechanics.rangeOfMotion}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400">Range of Motion</div>
                    </div>
                  </CardContent>
                </Card>

                {/* Performance Comparison */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <BarChart3 className="w-5 h-5 text-indigo-600" />
                      <span>Performance Comparison</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Your Best</span>
                      <span className="font-semibold">{analysisResults.comparison.personalBest}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Average User</span>
                      <span className="font-semibold">{analysisResults.comparison.averageUser}%</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm">Elite Level</span>
                      <span className="font-semibold">{analysisResults.comparison.eliteLevel}%</span>
                    </div>
                    <div className="mt-3">
                      <div className="text-xs text-gray-500 mb-2">Your Position</div>
                      <Progress
                        value={(analysisResults.overallScore / analysisResults.comparison.eliteLevel) * 100}
                        className="h-2"
                      />
                    </div>
                  </CardContent>
                </Card>

                {/* Action Buttons */}
                <div className="flex space-x-4">
                  <Button className="flex-1">
                    <Target className="w-4 h-4 mr-2" />
                    Save Analysis
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1 bg-transparent"
                    onClick={() => {
                      setHasResults(false)
                      setRecordingTime(0)
                      setSelectedExercise("")
                      setAnalysisProgress(0)
                    }}
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    New Analysis
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
