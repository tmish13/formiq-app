"use client"

import { motion } from "framer-motion"
import { Trophy, CheckCircle } from "lucide-react"
import { ProgressBar } from "@/components/atoms/ProgressBar"

interface ChallengeBannerProps {
  title: string
  progressPercent: number
  completed: boolean
}

export function ChallengeBanner({ title, progressPercent, completed }: ChallengeBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`
        rounded-xl p-6 relative overflow-hidden
        ${
          completed
            ? "bg-gradient-to-r from-green-500 to-emerald-600 text-white"
            : "bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20"
        }
      `}
    >
      <div className="flex items-center space-x-4">
        <div
          className={`
          w-12 h-12 rounded-xl flex items-center justify-center
          ${completed ? "bg-white/20" : "bg-yellow-100 dark:bg-yellow-900/30"}
        `}
        >
          {completed ? (
            <CheckCircle className="w-6 h-6 text-white" />
          ) : (
            <Trophy className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
          )}
        </div>

        <div className="flex-1">
          <h3 className={`font-semibold text-lg mb-2 ${completed ? "text-white" : "text-gray-900 dark:text-white"}`}>
            {completed ? "🎉 Challenge Complete!" : title}
          </h3>

          {!completed && (
            <div className="space-y-2">
              <ProgressBar percent={progressPercent} animated={true} />
              <p className="text-sm text-gray-600 dark:text-gray-400">{Math.round(progressPercent)}% complete</p>
            </div>
          )}

          {completed && (
            <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-white/90">
              Great job! You've completed this week's challenge.
            </motion.p>
          )}
        </div>
      </div>

      {completed && (
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
          className="absolute top-4 right-4 text-2xl"
        >
          🎉
        </motion.div>
      )}
    </motion.div>
  )
}
