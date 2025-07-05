"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Target,
  TrendingUp,
  RotateCcw,
  Share,
  BookOpen,
  Play,
  Sparkles,
  Brain,
} from "lucide-react"
import { BottomNavigation } from "@/components/bottom-navigation"
import { Header } from "@/components/header"

const analysisResults = {
  exercise: "Squat",
  overallScore: 85,
  date: "Today, 2:34 PM",
  repsAnalyzed: 5,
  improvement: "+8% from last session",
  breakdown: [
    {
      category: "Depth",
      score: 92,
      status: "excellent",
      feedback: "Excellent depth achieved - hitting parallel consistently",
      icon: "✅",
      improvement: "+6%",
      keyFrames: [2, 4, 6, 8, 10],
    },
    {
      category: "Knee Tracking",
      score: 68,
      status: "warning",
      feedback: "Knees cave inward during ascent - focus on external rotation",
      icon: "⚠️",
      improvement: "-2%",
      keyFrames: [3, 5, 7, 9],
    },
    {
      category: "Back Position",
      score: 88,
      status: "good",
      feedback: "Good neutral spine maintained throughout movement",
      icon: "✅",
      improvement: "+4%",
      keyFrames: [1, 3, 5, 7, 9],
    },
    {
      category: "Tempo",
      score: 90,
      status: "excellent",
      feedback: "Perfect controlled descent and explosive ascent",
      icon: "✅",
      improvement: "+3%",
      keyFrames: [1, 2, 3, 4, 5],
    },
    {
      category: "Stability",
      score: 75,
      status: "good",
      feedback: "Minor balance shifts - consider wider stance",
      icon: "⚠️",
      improvement: "+5%",
      keyFrames: [2, 4, 6, 8],
    },
  ],
  recommendations: [
    {
      icon: "🦵",
      title: "Knee Tracking",
      description: "Push knees out during descent. Try the 'spread the floor' cue with your feet.",
      priority: "high",
      exercise: "Wall sits with external rotation focus",
      duration: "2-3 sets of 30 seconds",
    },
    {
      icon: "💪",
      title: "Depth Control",
      description: "Your depth is excellent! Try adding pause squats to build strength at the bottom.",
      priority: "medium",
      exercise: "Pause squats (2-second hold)",
      duration: "3 sets of 5 reps",
    },
    {
      icon: "🔄",
      title: "Tempo Mastery",
      description: "Perfect tempo control. Continue with 2-1-2 pattern for optimal muscle engagement.",
      priority: "low",
      exercise: "Continue current tempo work",
      duration: "Maintain consistency",
    },
  ],
  poseSnapshot: "/placeholder.svg?height=200&width=150",
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case "excellent":
      return <CheckCircle className="w-5 h-5 text-green-500" />
    case "good":
      return <CheckCircle className="w-5 h-5 text-blue-500" />
    case "warning":
      return <AlertTriangle className="w-5 h-5 text-yellow-500" />
    case "poor":
      return <XCircle className="w-5 h-5 text-red-500" />
    default:
      return <CheckCircle className="w-5 h-5 text-gray-400" />
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case "excellent":
      return "text-green-600"
    case "good":
      return "text-blue-600"
    case "warning":
      return "text-yellow-600"
    case "poor":
      return "text-red-600"
    default:
      return "text-gray-600"
  }
}

const getPriorityColor = (priority: string) => {
  switch (priority) {
    case "high":
      return "border-l-red-500 bg-red-50 dark:bg-red-900/20"
    case "medium":
      return "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20"
    case "low":
      return "border-l-green-500 bg-green-50 dark:bg-green-900/20"
    default:
      return "border-l-gray-500 bg-gray-50 dark:bg-gray-900/20"
  }
}

export default function AnalysisResults() {
  const [showDetails, setShowDetails] = useState<number | null>(null)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      <Header />

      <div className="px-4 py-6 space-y-6">
        {/* Analysis Header */}
        <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-2xl font-bold mb-1">Analysis Complete</h1>
                <p className="text-blue-100">{analysisResults.date}</p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2">
                  <span className="text-2xl font-bold">{analysisResults.overallScore}</span>
                </div>
                <p className="text-sm text-blue-100">Form Score</p>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="text-center">
                  <p className="text-lg font-bold">{analysisResults.repsAnalyzed}</p>
                  <p className="text-xs text-blue-100">Reps</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold">🏋️</p>
                  <p className="text-xs text-blue-100">{analysisResults.exercise}</p>
                </div>
              </div>
              <div className="text-right">
                <Badge className="bg-green-500/20 text-green-100 border-green-400">
                  <TrendingUp className="w-3 h-3 mr-1" />
                  {analysisResults.improvement}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Form Breakdown */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Form Breakdown</h2>
          <div className="space-y-3">
            {analysisResults.breakdown.map((item, index) => (
              <Card key={index} className="border-0 shadow-sm">
                <CardContent className="p-4">
                  <div
                    className="flex items-center justify-between cursor-pointer"
                    onClick={() => setShowDetails(showDetails === index ? null : index)}
                  >
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(item.status)}
                      <div>
                        <h4 className="font-medium text-gray-900 dark:text-white">{item.category}</h4>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {item.feedback.length > 40 && showDetails !== index
                            ? item.feedback.substring(0, 40) + "..."
                            : item.feedback}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center space-x-2">
                        <span className={`text-lg font-bold ${getStatusColor(item.status)}`}>{item.score}%</span>
                        <span className="text-sm text-green-600 font-medium">{item.improvement}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3">
                    <Progress value={item.score} className="h-2" />
                  </div>

                  {showDetails === index && (
                    <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                      <div className="space-y-3">
                        <div>
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            Key Analysis Points:
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">{item.feedback}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Analyzed Frames:</p>
                          <div className="flex space-x-2">
                            {item.keyFrames.map((frame, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">
                                Frame {frame}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Brain className="w-5 h-5 text-purple-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">AI Recommendations</h2>
            <Badge variant="secondary" className="bg-purple-100 text-purple-800 text-xs">
              Personalized
            </Badge>
          </div>
          <div className="space-y-4">
            {analysisResults.recommendations.map((rec, index) => (
              <Card key={index} className={`border-l-4 ${getPriorityColor(rec.priority)} border-0 shadow-sm`}>
                <CardContent className="p-4">
                  <div className="flex items-start space-x-3">
                    <div className="text-2xl">{rec.icon}</div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-gray-900 dark:text-white">{rec.title}</h4>
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            rec.priority === "high"
                              ? "border-red-200 text-red-700"
                              : rec.priority === "medium"
                                ? "border-yellow-200 text-yellow-700"
                                : "border-green-200 text-green-700"
                          }`}
                        >
                          {rec.priority} priority
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 leading-relaxed">{rec.description}</p>
                      <div className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-3">
                        <div className="flex items-center space-x-2 mb-2">
                          <Play className="w-4 h-4 text-blue-600" />
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Recommended Exercise:</p>
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{rec.exercise}</p>
                        <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">{rec.duration}</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Pose Analysis */}
        <Card className="border-0 shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-base">
              <Target className="w-5 h-5 text-blue-600" />
              <span>Pose Analysis</span>
            </CardTitle>
            <CardDescription>Key movement patterns identified</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-4">
              <div className="w-24 h-32 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                <img
                  src={analysisResults.poseSnapshot || "/placeholder.svg"}
                  alt="Pose analysis"
                  className="w-20 h-28 object-cover rounded"
                />
              </div>
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Hip Angle</span>
                  <span className="text-sm text-green-600">95° ✓</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Knee Angle</span>
                  <span className="text-sm text-yellow-600">87° ⚠️</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Ankle Angle</span>
                  <span className="text-sm text-green-600">78° ✓</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Spine Angle</span>
                  <span className="text-sm text-green-600">12° ✓</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <Button className="h-12 bg-blue-600 hover:bg-blue-700">
            <Target className="w-4 h-4 mr-2" />
            Save Analysis
          </Button>
          <Button variant="outline" className="h-12 bg-transparent">
            <Share className="w-4 h-4 mr-2" />
            Share Results
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Button variant="outline" className="h-12 bg-transparent">
            <BookOpen className="w-4 h-4 mr-2" />
            Learn More
          </Button>
          <Button
            variant="outline"
            className="h-12 bg-transparent"
            onClick={() => {
              // Navigate back to record screen
            }}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            New Analysis
          </Button>
        </div>

        {/* Celebration Banner */}
        <Card className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-green-200 dark:border-green-800">
          <CardContent className="p-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <h4 className="font-semibold text-green-900 dark:text-green-100">Great Progress!</h4>
                <p className="text-sm text-green-700 dark:text-green-200">
                  Your form improved 8% since last session. Keep up the excellent work!
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <BottomNavigation activeTab="record" />
    </div>
  )
}
