"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Target,
  Clock,
  Award,
  Play,
  Share,
  Download,
  Lightbulb,
  CheckCircle,
  AlertTriangle,
  ChevronDown,
  ExternalLink,
} from "lucide-react"
import { BottomNavigation } from "@/components/bottom-navigation"

export default function AnalysisPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "detailed" | "tips">("overview")

  const analysisData = {
    overallScore: 87,
    date: "Today, 2:30 PM",
    exercise: "Squat",
    reps: 5,
    duration: "45 seconds",
    metrics: {
      depth: { score: 92, status: "excellent", improvement: "+8%" },
      stability: { score: 85, status: "good", improvement: "+3%" },
      tempo: { score: 89, status: "good", improvement: "+12%" },
      alignment: { score: 82, status: "fair", improvement: "-2%" },
    },
    insights: [
      {
        type: "strength",
        title: "Excellent Depth Control",
        description: "You consistently reached proper squat depth. This shows great hip mobility and strength.",
        icon: "💪",
      },
      {
        type: "improvement",
        title: "Focus on Knee Alignment",
        description: "Your knees occasionally tracked inward. Focus on pushing them out in line with your toes.",
        icon: "🎯",
        actionUrl: "/library?focus=knee-alignment",
      },
      {
        type: "tip",
        title: "Tempo Improvement",
        description: "Great progress on controlling your descent. This builds strength and stability.",
        icon: "⏱️",
      },
    ],
    recommendations: [
      {
        title: "Wall Squats",
        description: "Practice against a wall to improve knee tracking",
        difficulty: "Beginner",
        duration: "5 min",
        category: "Corrective",
      },
      {
        title: "Goblet Squats",
        description: "Add weight to challenge your form further",
        difficulty: "Intermediate",
        duration: "10 min",
        category: "Strength",
      },
    ],
  }

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-600"
    if (score >= 80) return "text-blue-600"
    if (score >= 70) return "text-yellow-600"
    return "text-red-600"
  }

  const getScoreBg = (score: number) => {
    if (score >= 90) return "bg-green-50 dark:bg-green-900/20"
    if (score >= 80) return "bg-blue-50 dark:bg-blue-900/20"
    if (score >= 70) return "bg-yellow-50 dark:bg-yellow-900/20"
    return "bg-red-50 dark:bg-red-900/20"
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      excellent: "bg-green-500 text-white px-3 py-1 text-sm font-medium",
      good: "bg-blue-500 text-white px-3 py-1 text-sm font-medium",
      fair: "bg-yellow-500 text-white px-3 py-1 text-sm font-medium",
      poor: "bg-red-500 text-white px-3 py-1 text-sm font-medium",
    }
    return styles[status as keyof typeof styles] || styles.fair
  }

  const renderOverview = () => (
    <div className="space-y-6">
      {/* Overall Score */}
      <Card className={`${getScoreBg(analysisData.overallScore)} border-2`}>
        <CardContent className="p-6 text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
            className="mb-4"
          >
            <div className={`text-6xl font-bold ${getScoreColor(analysisData.overallScore)} mb-2`}>
              {analysisData.overallScore}%
            </div>
            <Badge className="bg-green-500 text-white text-lg px-4 py-1">Great Job!</Badge>
          </motion.div>
          <p className="text-gray-600 dark:text-gray-400">Overall Form Score</p>
          <div className="flex items-center justify-center space-x-4 mt-4 text-sm text-gray-500">
            <span>{analysisData.exercise}</span>
            <span>•</span>
            <span>{analysisData.reps} reps</span>
            <span>•</span>
            <span>{analysisData.duration}</span>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(analysisData.metrics).map(([key, metric]) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-600 dark:text-gray-400 capitalize">{key}</span>
                  <div className="flex items-center space-x-2">
                    {metric.improvement.startsWith("+") ? (
                      <TrendingUp className="w-3 h-3 text-green-500" />
                    ) : (
                      <TrendingDown className="w-3 h-3 text-red-500" />
                    )}
                    <span
                      className={`text-xs font-medium ${metric.improvement.startsWith("+") ? "text-green-600" : "text-red-600"}`}
                    >
                      {metric.improvement}
                    </span>
                  </div>
                </div>
                <div className={`text-2xl font-bold ${getScoreColor(metric.score)} mb-2`}>{metric.score}%</div>
                <div className="relative mb-3">
                  <Progress value={metric.score} className="h-2" />
                  <motion.div
                    className={`absolute top-0 left-0 h-2 rounded-full ${
                      metric.score >= 90
                        ? "bg-green-500"
                        : metric.score >= 80
                          ? "bg-blue-500"
                          : metric.score >= 70
                            ? "bg-yellow-500"
                            : "bg-red-500"
                    }`}
                    initial={{ width: 0 }}
                    animate={{ width: `${metric.score}%` }}
                    transition={{ duration: 1, delay: 0.2 }}
                  />
                </div>
                <Badge className={getStatusBadge(metric.status)}>{metric.status}</Badge>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Key Insights */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Key Insights</h3>
        {analysisData.insights.map((insight, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 + index * 0.1 }}
          >
            <Card className={insight.actionUrl ? "cursor-pointer hover:shadow-md transition-shadow" : ""}>
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <div className="text-2xl">{insight.icon}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-gray-900 dark:text-white mb-1">{insight.title}</h4>
                      <div className="flex items-center space-x-2">
                        {insight.type === "strength" && <CheckCircle className="w-5 h-5 text-green-500" />}
                        {insight.type === "improvement" && <AlertTriangle className="w-5 h-5 text-yellow-500" />}
                        {insight.type === "tip" && <Lightbulb className="w-5 h-5 text-blue-500" />}
                        {insight.actionUrl && <ExternalLink className="w-4 h-4 text-gray-400" />}
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400">{insight.description}</p>
                    {insight.actionUrl && (
                      <Link href={insight.actionUrl}>
                        <Button variant="outline" size="sm" className="mt-2 bg-transparent">
                          View Exercises
                        </Button>
                      </Link>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )

  const renderDetailed = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Play className="w-5 h-5" />
            <span>Video Analysis</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative aspect-video bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center mb-4">
            <div className="text-center">
              <Play className="w-12 h-12 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">Recorded Exercise</p>
            </div>
            {/* Overlay metric */}
            <div className="absolute top-4 left-4">
              <Badge className="bg-blue-500 text-white">Depth: 92%</Badge>
            </div>
          </div>
          <div className="flex space-x-2">
            <div className="relative">
              <Button variant="outline" size="sm">
                <Play className="w-4 h-4 mr-2" />
                Play Video
                <ChevronDown className="w-3 h-3 ml-1" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Detailed Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {Object.entries(analysisData.metrics).map(([key, metric]) => (
            <div key={key} className="border-b border-gray-200 dark:border-gray-700 pb-4 last:border-b-0">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900 dark:text-white capitalize">{key}</h4>
                <div className={`text-lg font-bold ${getScoreColor(metric.score)}`}>{metric.score}%</div>
              </div>
              <div className="relative mb-2">
                <Progress value={metric.score} className="h-2" />
                <motion.div
                  className={`absolute top-0 left-0 h-2 rounded-full ${
                    metric.score >= 90
                      ? "bg-green-500"
                      : metric.score >= 80
                        ? "bg-blue-500"
                        : metric.score >= 70
                          ? "bg-yellow-500"
                          : "bg-red-500"
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${metric.score}%` }}
                  transition={{ duration: 1, delay: 0.2 }}
                />
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {key === "depth" &&
                  "Measures how low you go in your squat. Optimal depth is hip crease below knee level."}
                {key === "stability" &&
                  "Evaluates balance and control throughout the movement. Minimal wobbling is ideal."}
                {key === "tempo" &&
                  "Analyzes the speed of your movement. Controlled descent and explosive ascent is best."}
                {key === "alignment" &&
                  "Checks knee tracking, spine position, and overall body alignment during the exercise."}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )

  const renderTips = () => (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20">
        <CardContent className="p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Lightbulb className="w-6 h-6 text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Personalized Recommendations</h3>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Based on your analysis, here are specific exercises to improve your form:
          </p>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {analysisData.recommendations.map((rec, index) => (
          <Card key={index}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-semibold text-gray-900 dark:text-white">{rec.title}</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{rec.description}</p>
                </div>
                <Badge variant="outline">{rec.difficulty}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4" />
                    <span>{rec.duration}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Target className="w-4 h-4" />
                    <span>{rec.category}</span>
                  </div>
                </div>
                <Button size="sm">Try Exercise</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 cursor-pointer hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          <div className="flex items-center space-x-3">
            <Award className="w-6 h-6 text-green-600" />
            <div className="flex-1">
              <h4 className="font-semibold text-green-900 dark:text-green-100">Next Milestone</h4>
              <p className="text-sm text-green-700 dark:text-green-300">
                Reach 90% overall score to unlock the "Form Master" badge!
              </p>
            </div>
            <ExternalLink className="w-4 h-4 text-green-600" />
          </div>
        </CardContent>
      </Card>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-purple-50/30 dark:from-gray-900 dark:via-blue-950/30 dark:to-purple-950/30 pb-20">
      <div className="px-4 py-6 max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Link href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </Link>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Analysis Results</h1>
          <div className="flex space-x-2">
            <Button variant="ghost" size="sm">
              <Share className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <Download className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Date */}
        <div className="text-center mb-6">
          <p className="text-sm text-gray-500">{analysisData.date}</p>
        </div>

        {/* Tabs */}
        <div className="flex space-x-1 mb-6 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {[
            { id: "overview", label: "Overview" },
            { id: "detailed", label: "Detailed" },
            { id: "tips", label: "Tips" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm"
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === "overview" && renderOverview()}
          {activeTab === "detailed" && renderDetailed()}
          {activeTab === "tips" && renderTips()}
        </motion.div>

        {/* Action Buttons */}
        <div className="mt-8 grid grid-cols-2 gap-4">
          <Link href="/record">
            <Button variant="outline" className="w-full bg-blue-600 text-white hover:bg-blue-700 border-blue-600">
              Record Again
            </Button>
          </Link>
          <Link href="/progress">
            <Button className="w-full bg-purple-600 hover:bg-purple-700">View Progress</Button>
          </Link>
        </div>
      </div>

      <BottomNavigation activeTab="record" />
    </div>
  )
}
