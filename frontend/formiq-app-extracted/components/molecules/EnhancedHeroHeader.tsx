"use client"

import { motion } from "framer-motion"
import { ProgressBar } from "@/components/atoms/ProgressBar"
import { PremiumBadge } from "@/components/molecules/PremiumBadge"
import { Tooltip } from "@/components/atoms/Tooltip"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Heading1 } from "@/components/atoms/Typography"
import { designSystem } from "@/lib/design-system"
import { Zap, Target, Brain } from "lucide-react"

interface EnhancedHeroHeaderProps {
  username: string
  currentLevel: string
  streak: string
  progressPercent: number
  avatar?: string
  membershipTier?: "Basic" | "Pro" | "Premium"
  aiConfidence?: number
}

export function EnhancedHeroHeader({
  username,
  currentLevel,
  streak,
  progressPercent,
  avatar,
  membershipTier = "Pro",
  aiConfidence = 94,
}: EnhancedHeroHeaderProps) {
  const getNextLevel = (current: string) => {
    const levels = ["Beginner", "Intermediate", "Advanced", "Expert"]
    const currentIndex = levels.indexOf(current)
    return currentIndex < levels.length - 1 ? levels[currentIndex + 1] : "Master"
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        ${designSystem.gradients.card} dark:${designSystem.gradients.cardDark}
        rounded-2xl border border-slate-200/50 dark:border-slate-700/50
        ${designSystem.spacing.cardInternal}
        ${designSystem.shadows.cardElevated}
        backdrop-blur-sm
        relative overflow-hidden
      `}
    >
      {/* Background AI Pattern */}
      <div className="absolute inset-0 opacity-5">
        <svg className="w-full h-full" viewBox="0 0 200 100">
          <defs>
            <pattern id="ai-grid" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
              <circle cx="10" cy="10" r="1" fill="currentColor" className="text-blue-500" />
              <line x1="10" y1="10" x2="15" y2="5" stroke="currentColor" strokeWidth="0.5" className="text-blue-500" />
              <line x1="10" y1="10" x2="5" y2="15" stroke="currentColor" strokeWidth="0.5" className="text-blue-500" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#ai-grid)" />
        </svg>
      </div>

      <div className="relative z-10">
        <div className="flex flex-col lg:flex-row items-start lg:items-center space-y-6 lg:space-y-0 lg:space-x-6">
          {/* Enhanced Avatar Section */}
          <motion.div whileHover={{ scale: 1.05 }} className="relative flex-shrink-0">
            <div className="relative">
              {/* AI Glow Ring */}
              <motion.div
                animate={{
                  rotate: [0, 360],
                  scale: [1, 1.1, 1],
                }}
                transition={{
                  rotate: { duration: 20, repeat: Number.POSITIVE_INFINITY, ease: "linear" },
                  scale: { duration: 3, repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" },
                }}
                className="absolute -inset-2 bg-gradient-to-r from-teal-400 via-blue-500 to-purple-500 rounded-full opacity-75 blur-sm"
              />

              <Avatar className="w-20 h-20 relative z-10 ring-4 ring-white dark:ring-slate-800">
                <AvatarImage src={avatar || "/placeholder.svg"} alt={username} />
                <AvatarFallback className="bg-gradient-to-br from-blue-500 to-teal-600 text-white text-2xl font-bold">
                  {username.charAt(0)}
                </AvatarFallback>
              </Avatar>

              {/* Streak Fire Indicator */}
              {streak.includes("🔥") && (
                <Tooltip content="You're on fire! Amazing streak!">
                  <motion.div
                    animate={{ scale: [1, 1.3, 1], rotate: [0, 10, -10, 0] }}
                    transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                    className="absolute -top-2 -right-2 w-8 h-8 bg-gradient-to-r from-orange-400 to-red-500 rounded-full flex items-center justify-center shadow-lg"
                  >
                    🔥
                  </motion.div>
                </Tooltip>
              )}

              {/* AI Status Indicator */}
              <Tooltip content={`AI Confidence: ${aiConfidence}% - Your form analysis is highly accurate!`}>
                <motion.div
                  animate={{
                    opacity: [0.7, 1, 0.7],
                    scale: [1, 1.1, 1],
                  }}
                  transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
                  className="absolute -bottom-2 -right-2 w-8 h-8 bg-gradient-to-r from-teal-500 to-blue-600 rounded-full flex items-center justify-center shadow-lg"
                >
                  <Brain className="w-4 h-4 text-white" />
                </motion.div>
              </Tooltip>
            </div>
          </motion.div>

          {/* Enhanced Content */}
          <div className="flex-1 w-full space-y-6">
            {/* Greeting Section */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 }}
                className="space-y-2"
              >
                <div className="flex items-center space-x-3">
                  <Heading1 className="text-slate-900 dark:text-white">Hey {username}! 👋</Heading1>
                  <PremiumBadge tier={membershipTier} size="sm" animated={true} />
                </div>
                <p className="text-lg text-slate-600 dark:text-slate-400">Ready to perfect your form?</p>
              </motion.div>

              {/* Enhanced Streak Display */}
              <Tooltip content={`${streak} - Amazing consistency! Keep it up!`}>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.3, type: "spring", stiffness: 500, damping: 30 }}
                  className="bg-gradient-to-r from-orange-100 to-red-100 dark:from-orange-900/20 dark:to-red-900/20 text-orange-800 dark:text-orange-400 px-4 py-3 rounded-2xl text-lg font-semibold border border-orange-200 dark:border-orange-800/50 shadow-lg"
                >
                  {streak}
                </motion.div>
              </Tooltip>
            </div>

            {/* Enhanced Progress Section */}
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <Tooltip content="Your current skill level based on AI form analysis">
                  <div className="flex items-center space-x-2">
                    <Target className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    <span className="text-lg font-semibold text-slate-700 dark:text-slate-300">
                      Current Level: {currentLevel}
                    </span>
                  </div>
                </Tooltip>
                <span className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                  {progressPercent}% to {getNextLevel(currentLevel)}
                </span>
              </div>

              {/* Enhanced Progress Bar */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4 }}
              >
                <ProgressBar percent={progressPercent} gradient={true} animated={true} labelLeft="" labelRight="" />
              </motion.div>

              {/* Level Progression Indicator */}
              <div className="flex justify-between items-center text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full" />
                  <span className="text-slate-600 dark:text-slate-400 font-medium">{currentLevel}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <Zap className="w-4 h-4 text-teal-500" />
                  <span className="text-slate-600 dark:text-slate-400 font-medium">{getNextLevel(currentLevel)}</span>
                  <div className="w-3 h-3 bg-teal-500 rounded-full opacity-50" />
                </div>
              </div>

              {/* Motivational Message */}
              {progressPercent >= 80 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gradient-to-r from-teal-50 to-blue-50 dark:from-teal-900/20 dark:to-blue-900/20 rounded-lg p-3 border border-teal-200 dark:border-teal-800/50"
                >
                  <div className="flex items-center space-x-2">
                    <motion.div
                      animate={{ rotate: [0, 360] }}
                      transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
                    >
                      <Zap className="w-4 h-4 text-teal-600 dark:text-teal-400" />
                    </motion.div>
                    <span className="text-sm font-medium text-teal-700 dark:text-teal-300">
                      You're almost ready to level up! Keep pushing! 💪
                    </span>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
