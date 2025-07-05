"use client"

import { motion } from "framer-motion"
import { Trophy, CheckCircle, Target, Award } from "lucide-react"
import { ProgressBar } from "@/components/atoms/ProgressBar"
import { Button } from "@/components/ui/button"
import { designSystem } from "@/lib/design-system"

interface Challenge {
  id: string
  title: string
  description: string
  progressPercent: number
  completed: boolean
  type: "daily" | "weekly" | "monthly"
  reward?: string
  encouragement?: string
}

interface EnhancedChallengeBannerProps {
  challenge: Challenge
  onCelebrate?: () => void
}

export function EnhancedChallengeBanner({ challenge, onCelebrate }: EnhancedChallengeBannerProps) {
  const { title, description, progressPercent, completed, type, reward, encouragement } = challenge

  const typeColors = {
    daily: "from-blue-500 to-blue-600",
    weekly: "from-purple-500 to-purple-600",
    monthly: "from-orange-500 to-orange-600",
  }

  const typeIcons = {
    daily: "🌅",
    weekly: "📅",
    monthly: "🗓️",
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      whileHover={{ scale: 1.01, y: -2 }}
      className={`
        relative overflow-hidden rounded-2xl
        ${designSystem.spacing.cardInternal}
        ${designSystem.shadows.cardElevated}
        ${
          completed
            ? "bg-gradient-to-br from-emerald-500 to-teal-600 text-white"
            : "bg-gradient-to-br from-slate-50 to-white dark:from-slate-800 dark:to-slate-900 border border-slate-200/50 dark:border-slate-700/50"
        }
        transition-all duration-300
      `}
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className={`absolute inset-0 bg-gradient-to-br ${typeColors[type]}`} />
      </div>

      {/* Challenge Badge/Sticker Overlay */}
      <motion.div
        animate={{ rotate: [0, 5, -5, 0] }}
        transition={{ duration: 3, repeat: Number.POSITIVE_INFINITY }}
        className="absolute -top-2 -right-2 w-16 h-16 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-full flex items-center justify-center shadow-lg"
      >
        <span className="text-2xl">{typeIcons[type]}</span>
      </motion.div>

      <div className="relative z-10">
        <div className="flex items-start space-x-4">
          {/* Icon */}
          <motion.div
            whileHover={{ rotate: 360 }}
            transition={{ duration: 0.5 }}
            className={`
              w-16 h-16 rounded-2xl flex items-center justify-center flex-shrink-0
              ${
                completed
                  ? "bg-white/20 backdrop-blur-sm"
                  : "bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-700 dark:to-slate-800"
              }
            `}
          >
            {completed ? (
              <CheckCircle className="w-8 h-8 text-white" />
            ) : (
              <Trophy className={`w-8 h-8 ${completed ? "text-white" : "text-slate-600 dark:text-slate-400"}`} />
            )}
          </motion.div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-2">
              <h3
                className={`text-xl font-bold ${completed ? "text-white" : "text-slate-900 dark:text-white"} truncate`}
              >
                {completed ? "🎉 Challenge Complete!" : title}
              </h3>
              {reward && (
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                  className="flex items-center space-x-1 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400 px-2 py-1 rounded-full text-xs font-medium"
                >
                  <Award className="w-3 h-3" />
                  <span>{reward}</span>
                </motion.div>
              )}
            </div>

            <p className={`text-sm mb-4 ${completed ? "text-white/90" : "text-slate-600 dark:text-slate-400"}`}>
              {completed ? "Great job! You've completed this challenge." : description}
            </p>

            {!completed && (
              <div className="space-y-3">
                <ProgressBar
                  percent={progressPercent}
                  gradient={true}
                  animated={true}
                  labelLeft=""
                  labelRight={`${Math.round(progressPercent)}% complete`}
                />

                {encouragement && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-sm font-medium text-slate-700 dark:text-slate-300"
                  >
                    💪 {encouragement}
                  </motion.p>
                )}

                {progressPercent >= 80 && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex items-center space-x-2"
                  >
                    <Target className="w-4 h-4 text-orange-500" />
                    <span className="text-sm font-medium text-orange-600 dark:text-orange-400">
                      Almost there! You're so close!
                    </span>
                  </motion.div>
                )}
              </div>
            )}

            {completed && onCelebrate && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <Button
                  onClick={onCelebrate}
                  variant="secondary"
                  size="sm"
                  className="bg-white/20 hover:bg-white/30 text-white border-white/30"
                >
                  🎉 Celebrate
                </Button>
              </motion.div>
            )}
          </div>
        </div>
      </div>

      {/* Completion Animation */}
      {completed && (
        <>
          <motion.div
            animate={{
              scale: [1, 1.2, 1],
              rotate: [0, 10, -10, 0],
            }}
            transition={{
              duration: 0.6,
              repeat: Number.POSITIVE_INFINITY,
              repeatDelay: 3,
            }}
            className="absolute top-4 left-4 text-3xl"
          >
            🎉
          </motion.div>
          <motion.div
            animate={{
              opacity: [0.5, 1, 0.5],
              scale: [1, 1.05, 1],
            }}
            transition={{
              duration: 2,
              repeat: Number.POSITIVE_INFINITY,
            }}
            className="absolute inset-0 bg-gradient-to-r from-emerald-400/20 to-teal-400/20 rounded-2xl pointer-events-none"
          />
        </>
      )}
    </motion.div>
  )
}
