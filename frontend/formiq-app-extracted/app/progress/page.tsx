"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { TrendingUp, Target, Activity, Info, Camera } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BottomNavigation } from "@/components/bottom-navigation"
import { Badge } from "@/components/ui/badge"

export default function ProgressPage() {
  const [hasData, setHasData] = useState(false)

  useEffect(() => {
    // Check if user has any progress data
    const savedProgress = localStorage.getItem("formiq-user-progress")
    if (savedProgress) {
      const progress = JSON.parse(savedProgress)
      setHasData(progress.totalAnalyses > 0)
    }
  }, [])

  // Mock data for preview
  const mockData = {
    bestScore: 85,
    sessions: 12,
    streak: 7,
    weeklyData: [
      { week: "Week 1", score: 65 },
      { week: "Week 2", score: 72 },
      { week: "Week 3", score: 78 },
      { week: "Week 4", score: 82 },
      { week: "Week 5", score: 85 },
    ],
  }

  const MetricCard = ({
    icon,
    label,
    value,
    tooltip,
  }: { icon: React.ReactNode; label: string; value: string | number; tooltip: string }) => (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02, y: -2 }}
      className="group relative"
    >
      <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-md hover:shadow-lg transition-all duration-300">
        <CardContent className="p-6 text-center">
          <div className="flex items-center justify-center space-x-2 mb-3">
            {icon}
            <Info className="w-4 h-4 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <div className="flex items-baseline justify-center">
            <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
          </div>
          <div className="text-sm font-medium text-gray-600 dark:text-gray-400">{label}</div>

          {/* Tooltip */}
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
            {tooltip}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900 dark:border-t-gray-700"></div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )

  if (hasData) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
        <div className="px-4 py-6 space-y-6 max-w-4xl mx-auto">
          {/* Header */}
          <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">Your Progress</h1>
            <p className="text-gray-600 dark:text-gray-400">Track your form improvement journey</p>
          </motion.div>

          {/* Metrics */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-3 gap-6"
          >
            <MetricCard
              icon={<Target className="w-6 h-6 text-blue-600" />}
              label="Best Score"
              value={`${mockData.bestScore}%`}
              tooltip="Your highest form analysis score"
            />
            <MetricCard
              icon={<Activity className="w-6 h-6 text-green-600" />}
              label="Sessions"
              value={mockData.sessions}
              tooltip="Total number of recorded sessions"
            />
            <MetricCard
              icon={<TrendingUp className="w-6 h-6 text-orange-600" />}
              label="Streak"
              value={`${mockData.streak}d`}
              tooltip="Consecutive days with recorded sessions"
            />
          </motion.div>

          {/* Progress Chart */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
              <CardContent className="p-8">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">Weekly Progress</h3>
                <div className="flex items-end justify-between h-48 px-2">
                  {mockData.weeklyData.map((week, index) => (
                    <motion.div
                      key={week.week}
                      initial={{ height: 0 }}
                      animate={{ height: `${(week.score / 100) * 100}%` }}
                      transition={{ delay: index * 0.2, duration: 0.8, ease: "easeOut" }}
                      className="flex-1 mx-2 bg-gradient-to-t from-purple-500 to-blue-500 rounded-t-lg opacity-80 hover:opacity-100 transition-opacity relative group"
                    >
                      <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 text-sm font-semibold text-gray-700 dark:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
                        {week.score}%
                      </div>
                    </motion.div>
                  ))}
                </div>
                <div className="flex justify-between mt-4 px-2">
                  {mockData.weeklyData.map((week) => (
                    <div key={week.week} className="flex-1 text-center text-sm text-gray-600 dark:text-gray-400">
                      {week.week}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <BottomNavigation activeTab="progress" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      <div className="px-4 py-6 space-y-8 max-w-4xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">Your Progress</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Start recording your exercises to track your progress and improvements.
            <br />
            Your personal stats will show up like this once you get started!
          </p>
        </motion.div>

        {/* Enhanced Metrics Preview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-3 gap-6"
        >
          <MetricCard
            icon={<Target className="w-6 h-6 text-blue-600" />}
            label="Best Score"
            value="85%"
            tooltip="Your highest form analysis score"
          />
          <MetricCard
            icon={<Activity className="w-6 h-6 text-green-600" />}
            label="Sessions"
            value="12"
            tooltip="Total number of recorded sessions"
          />
          <MetricCard
            icon={<TrendingUp className="w-6 h-6 text-orange-600" />}
            label="Streak"
            value="7d"
            tooltip="Consecutive days with recorded sessions"
          />
        </motion.div>

        {/* Enhanced Progress Chart Preview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-12"
        >
          <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
            <CardContent className="p-8">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                  Soon, you'll see your form progress here!
                </h3>
                <Badge variant="secondary" className="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
                  Preview
                </Badge>
              </div>

              <div className="flex items-end justify-between h-48 px-2 mb-8">
                {mockData.weeklyData.map((week, index) => (
                  <motion.div
                    key={week.week}
                    initial={{ height: 0 }}
                    animate={{ height: `${(week.score / 100) * 100}%` }}
                    transition={{ delay: index * 0.3, duration: 0.8, ease: "easeOut" }}
                    className="flex-1 mx-2 bg-gradient-to-t from-purple-500/60 to-blue-500/60 rounded-t-lg relative group"
                  >
                    <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 text-sm font-semibold text-gray-700 dark:text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
                      {week.score}%
                    </div>
                  </motion.div>
                ))}
              </div>

              <div className="flex justify-between px-2 mb-8">
                {mockData.weeklyData.map((week) => (
                  <div key={week.week} className="flex-1 text-center text-sm text-gray-600 dark:text-gray-400">
                    {week.week}
                  </div>
                ))}
              </div>

              {/* Enhanced CTA Section */}
              <div className="border-t border-gray-200/50 dark:border-gray-700/30 pt-8">
                <Button
                  size="lg"
                  className="w-[95%] mx-auto h-14 text-lg font-semibold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white shadow-lg hover:shadow-xl transition-all duration-200 flex"
                  onClick={() => (window.location.href = "/record")}
                >
                  <Camera className="w-5 h-5 mr-2" />
                  Record Exercise
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <BottomNavigation activeTab="progress" />
    </div>
  )
}
