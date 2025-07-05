"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { HelpCircle, X, CheckCircle, AlertTriangle } from "lucide-react"

interface RecordingTip {
  id: string
  title: string
  description: string
  icon: string
  type: "success" | "warning" | "info"
}

interface RecordingTipsProps {
  exercise: string
  isRecording: boolean
}

const exerciseTips: Record<string, RecordingTip[]> = {
  squat: [
    {
      id: "depth",
      title: "Proper Depth",
      description: "Lower until your hip crease is below your knee cap",
      icon: "📐",
      type: "info",
    },
    {
      id: "knees",
      title: "Knee Tracking",
      description: "Keep knees in line with toes, avoid caving inward",
      icon: "🦵",
      type: "warning",
    },
    {
      id: "back",
      title: "Neutral Spine",
      description: "Maintain natural back curve throughout movement",
      icon: "🏃",
      type: "success",
    },
  ],
  deadlift: [
    {
      id: "bar-path",
      title: "Bar Path",
      description: "Keep bar close to your body throughout the lift",
      icon: "📏",
      type: "warning",
    },
    {
      id: "hip-hinge",
      title: "Hip Hinge",
      description: "Initiate movement by pushing hips back",
      icon: "🔄",
      type: "info",
    },
  ],
}

export function RecordingTips({ exercise, isRecording }: RecordingTipsProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [currentTip, setCurrentTip] = useState(0)

  const tips = exerciseTips[exercise.toLowerCase()] || []

  if (tips.length === 0) return null

  const getTypeColor = (type: string) => {
    switch (type) {
      case "success":
        return "text-green-600 bg-green-100 dark:bg-green-900/20"
      case "warning":
        return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20"
      case "info":
        return "text-blue-600 bg-blue-100 dark:bg-blue-900/20"
      default:
        return "text-gray-600 bg-gray-100 dark:bg-gray-700"
    }
  }

  return (
    <>
      {/* Tips Toggle Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsExpanded(!isExpanded)}
        className="fixed top-20 right-4 z-40 w-12 h-12 bg-blue-600 text-white rounded-full shadow-lg flex items-center justify-center"
      >
        <HelpCircle className="w-6 h-6" />
      </motion.button>

      {/* Tips Panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            className="fixed top-0 right-0 w-80 h-full bg-white dark:bg-gray-800 shadow-2xl z-50 overflow-y-auto"
          >
            <div className="p-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{exercise} Tips</h3>
                <button
                  onClick={() => setIsExpanded(false)}
                  className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Recording Status */}
              {isRecording && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800"
                >
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                    <span className="text-sm font-medium text-red-700 dark:text-red-300">
                      Recording - Follow the tips below
                    </span>
                  </div>
                </motion.div>
              )}

              {/* Tips List */}
              <div className="space-y-4">
                {tips.map((tip, index) => (
                  <motion.div
                    key={tip.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`p-4 rounded-lg border ${getTypeColor(tip.type)}`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="text-2xl">{tip.icon}</div>
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">{tip.title}</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400">{tip.description}</p>
                      </div>
                      {tip.type === "success" && <CheckCircle className="w-5 h-5 text-green-600" />}
                      {tip.type === "warning" && <AlertTriangle className="w-5 h-5 text-yellow-600" />}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Quick Tips Carousel */}
              <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">Quick Tip</h4>
                <div className="flex items-center space-x-2">
                  {tips.map((_, index) => (
                    <button
                      key={index}
                      onClick={() => setCurrentTip(index)}
                      className={`w-2 h-2 rounded-full transition-colors ${
                        index === currentTip ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-500"
                      }`}
                    />
                  ))}
                </div>
                <motion.div
                  key={currentTip}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="mt-3"
                >
                  <p className="text-sm text-gray-600 dark:text-gray-400">{tips[currentTip]?.description}</p>
                </motion.div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
