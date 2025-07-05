"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Brain, Sparkles, ChevronLeft, ChevronRight, ExternalLink, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { designSystem } from "@/lib/design-system"

interface AITip {
  id: string
  icon: string
  tip: string
  actionText?: string
  actionUrl?: string
  priority: "high" | "medium" | "low"
}

interface EnhancedAICoachCardProps {
  tips: AITip[]
  userName?: string
  recentMetrics?: {
    improvement: string
    exercise: string
  }
}

export function EnhancedAICoachCard({ tips, userName = "User", recentMetrics }: EnhancedAICoachCardProps) {
  const [currentTipIndex, setCurrentTipIndex] = useState(0)
  const [isAutoPlaying, setIsAutoPlaying] = useState(true)

  const currentTip = tips[currentTipIndex]

  // Auto-rotate tips every 8 seconds
  useEffect(() => {
    if (!isAutoPlaying || tips.length <= 1) return

    const interval = setInterval(() => {
      setCurrentTipIndex((prev) => (prev + 1) % tips.length)
    }, 8000)

    return () => clearInterval(interval)
  }, [isAutoPlaying, tips.length])

  const nextTip = () => {
    setCurrentTipIndex((prev) => (prev + 1) % tips.length)
    setIsAutoPlaying(false)
  }

  const prevTip = () => {
    setCurrentTipIndex((prev) => (prev - 1 + tips.length) % tips.length)
    setIsAutoPlaying(false)
  }

  const handleAction = () => {
    if (currentTip.actionUrl) {
      window.location.href = currentTip.actionUrl
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className={`
        relative overflow-hidden rounded-2xl
        bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900
        ${designSystem.spacing.cardInternal}
        ${designSystem.shadows.aiGlow}
        border border-slate-700/50
      `}
    >
      {/* AI Neural Network Background */}
      <div className="absolute inset-0 opacity-10">
        <svg className="w-full h-full" viewBox="0 0 400 200">
          <defs>
            <pattern id="neural" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
              <circle cx="20" cy="20" r="2" fill="currentColor" className="text-teal-400" />
              <line
                x1="20"
                y1="20"
                x2="35"
                y2="10"
                stroke="currentColor"
                strokeWidth="1"
                className="text-teal-400"
                opacity="0.5"
              />
              <line
                x1="20"
                y1="20"
                x2="5"
                y2="30"
                stroke="currentColor"
                strokeWidth="1"
                className="text-teal-400"
                opacity="0.5"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#neural)" />
        </svg>
      </div>

      {/* AI Glow Effect */}
      <motion.div
        animate={{
          opacity: [0.3, 0.6, 0.3],
          scale: [1, 1.05, 1],
        }}
        transition={{
          duration: 4,
          repeat: Number.POSITIVE_INFINITY,
          ease: "easeInOut",
        }}
        className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-teal-500/30 via-blue-500/20 to-purple-500/30 rounded-full blur-2xl"
      />

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <motion.div
              animate={{
                rotate: [0, 360],
                scale: [1, 1.1, 1],
              }}
              transition={{
                rotate: { duration: 20, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
                scale: { duration: 2, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
              }}
              className="relative w-16 h-16 bg-gradient-to-br from-teal-400 to-blue-500 rounded-2xl flex items-center justify-center"
            >
              <Brain className="w-8 h-8 text-white" />
              <motion.div
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                className="absolute inset-0 bg-white/20 rounded-2xl"
              />
            </motion.div>

            <div>
              <div className="flex items-center space-x-2 mb-1">
                <h3 className="text-xl font-bold text-white">AI Coach</h3>
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY }}
                >
                  <Sparkles className="w-5 h-5 text-teal-400" />
                </motion.div>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4 text-teal-400" />
                <span className="text-sm text-slate-300">Personalized for {userName}</span>
              </div>
            </div>
          </div>

          {/* Navigation Controls */}
          {tips.length > 1 && (
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="sm" onClick={prevTip} className="text-white hover:bg-white/10 w-8 h-8 p-0">
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <div className="flex space-x-1">
                {tips.map((_, index) => (
                  <motion.div
                    key={index}
                    className={`w-2 h-2 rounded-full transition-colors ${
                      index === currentTipIndex ? "bg-teal-400" : "bg-white/30"
                    }`}
                    animate={index === currentTipIndex ? { scale: [1, 1.3, 1] } : {}}
                    transition={{ duration: 0.3 }}
                  />
                ))}
              </div>
              <Button variant="ghost" size="sm" onClick={nextTip} className="text-white hover:bg-white/10 w-8 h-8 p-0">
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Recent Metrics */}
        {recentMetrics && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/10 backdrop-blur-sm rounded-lg p-3 mb-4"
          >
            <div className="flex items-center space-x-2 text-sm text-slate-300">
              <span>Recent improvement:</span>
              <span className="text-teal-400 font-semibold">{recentMetrics.improvement}</span>
              <span>in {recentMetrics.exercise}</span>
            </div>
          </motion.div>
        )}

        {/* Tip Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentTip.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
            className="space-y-4"
          >
            <div className="flex items-start space-x-3">
              <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                className="text-3xl flex-shrink-0"
              >
                {currentTip.icon}
              </motion.div>
              <p className="text-white/95 leading-relaxed text-lg">{currentTip.tip}</p>
            </div>

            {currentTip.actionText && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                <Button onClick={handleAction} className="bg-teal-500 hover:bg-teal-600 text-white border-0" size="sm">
                  {currentTip.actionText}
                  <ExternalLink className="w-4 h-4 ml-2" />
                </Button>
              </motion.div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Priority Indicator */}
        {currentTip.priority === "high" && (
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
            className="absolute top-4 right-4 w-3 h-3 bg-red-400 rounded-full"
          />
        )}
      </div>
    </motion.div>
  )
}
