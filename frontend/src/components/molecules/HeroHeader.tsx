"use client"

import { motion } from "framer-motion"
import { ProgressBar } from "@/components/atoms/ProgressBar"
import { Badge } from "@/components/atoms/Badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface HeroHeaderProps {
  username: string
  currentLevel: string
  streak: string
  progressPercent: number
  avatar?: string
}

export function HeroHeader({ username, currentLevel, streak, progressPercent, avatar }: HeroHeaderProps) {
  const getNextLevel = (current: string) => {
    const levels = ["Beginner", "Intermediate", "Advanced", "Expert"]
    const currentIndex = levels.indexOf(current)
    return currentIndex < levels.length - 1 ? levels[currentIndex + 1] : "Master"
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center space-y-4 sm:space-y-0 sm:space-x-4">
        {/* Avatar */}
        <motion.div whileHover={{ scale: 1.05 }} className="relative">
          <Avatar className="w-16 h-16 ring-4 ring-blue-100 dark:ring-blue-900/30">
            <AvatarImage src={avatar || "/placeholder.svg"} alt={username} />
            <AvatarFallback className="bg-blue-100 text-blue-600 text-xl font-bold">
              {username.charAt(0)}
            </AvatarFallback>
          </Avatar>
          {streak.includes("🔥") && (
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1, repeat: Number.POSITIVE_INFINITY }}
              className="absolute -top-1 -right-1 w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center"
            >
              🔥
            </motion.div>
          )}
        </motion.div>

        {/* Content */}
        <div className="flex-1 w-full">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
            <div>
              <motion.h1
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="text-2xl font-bold text-gray-900 dark:text-white"
              >
                Hey {username}! 👋
              </motion.h1>
              <p className="text-gray-600 dark:text-gray-400">Ready to perfect your form?</p>
            </div>

            <Badge label={streak} variant="warning" animated={true} size="lg" />
          </div>

          {/* Progress */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Current Level: {currentLevel}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {progressPercent}% to {getNextLevel(currentLevel)}
              </span>
            </div>
            <ProgressBar percent={progressPercent} gradient={true} animated={true} />
          </div>
        </div>
      </div>
    </motion.div>
  )
}
