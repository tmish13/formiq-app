"use client"

import { motion } from "framer-motion"
import { Play, Target, Star, Clock, Users, TrendingUp } from "lucide-react"
import { Badge } from "@/components/atoms/Badge"
import { CTAButton } from "@/components/atoms/CTAButton"
import { Tooltip } from "@/components/atoms/Tooltip"
import { designSystem } from "@/lib/design-system"

interface EnhancedExerciseCardProps {
  thumbnail: string
  title: string
  tags: string[]
  rating: number
  duration?: string
  difficulty?: "Beginner" | "Intermediate" | "Advanced"
  completions?: number
  personalBest?: string
  demoHandler: () => void
  analyzeHandler: () => void
}

export function EnhancedExerciseCard({
  thumbnail,
  title,
  tags,
  rating,
  duration,
  difficulty,
  completions,
  personalBest,
  demoHandler,
  analyzeHandler,
}: EnhancedExerciseCardProps) {
  const difficultyColors = {
    Beginner: "success",
    Intermediate: "warning",
    Advanced: "purple",
  } as const

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -6, scale: 1.02, rotateY: 2 }}
      className={`
        bg-gradient-to-br from-white to-slate-50 dark:from-slate-800 dark:to-slate-900
        rounded-2xl overflow-hidden
        ${designSystem.shadows.card}
        hover:${designSystem.shadows.cardHover}
        transition-all duration-300 ease-out
        border border-slate-200/50 dark:border-slate-700/50
        group
      `}
    >
      {/* Enhanced Thumbnail */}
      <div className="relative h-48 overflow-hidden">
        <motion.img
          whileHover={{ scale: 1.1 }}
          transition={{ duration: 0.3 }}
          src={thumbnail || "/placeholder.svg?height=200&width=300"}
          alt={title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent" />

        {/* Enhanced Rating */}
        <Tooltip content={`Average user rating: ${rating}/5`}>
          <div className="absolute top-3 right-3 flex items-center space-x-1 bg-black/50 backdrop-blur-sm rounded-full px-3 py-1.5">
            <Star className="w-4 h-4 text-yellow-400 fill-current" />
            <span className="text-white text-sm font-semibold">{rating}</span>
          </div>
        </Tooltip>

        {/* Personal Best Badge */}
        {personalBest && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute top-3 left-3 bg-gradient-to-r from-emerald-500 to-teal-600 text-white px-2 py-1 rounded-full text-xs font-semibold flex items-center space-x-1"
          >
            <TrendingUp className="w-3 h-3" />
            <span>PB: {personalBest}</span>
          </motion.div>
        )}

        {/* Enhanced Play Overlay */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={demoHandler}
          className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        >
          <motion.div
            whileHover={{ scale: 1.1 }}
            className="w-20 h-20 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center border border-white/30"
          >
            <Play className="w-10 h-10 text-white ml-1" />
          </motion.div>
        </motion.button>
      </div>

      {/* Enhanced Content */}
      <div className={`${designSystem.spacing.cardInternal} space-y-4`}>
        <div>
          <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-3 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
            {title}
          </h3>

          {/* Enhanced Metadata */}
          <div className={`flex items-center flex-wrap ${designSystem.spacing.tagSpacing} mb-4`}>
            {difficulty && (
              <Badge label={difficulty} variant={difficultyColors[difficulty]} size="sm" animated={false} />
            )}
            {duration && (
              <Badge
                label={duration}
                icon={<Clock className="w-3 h-3" />}
                size="sm"
                variant="default"
                animated={false}
              />
            )}
            {completions && (
              <Tooltip content={`${completions.toLocaleString()} users have completed this exercise`}>
                <div className="flex items-center space-x-1 text-xs text-slate-500 dark:text-slate-400">
                  <Users className="w-3 h-3" />
                  <span>{completions.toLocaleString()}</span>
                </div>
              </Tooltip>
            )}
          </div>

          {/* Enhanced Tags */}
          <div className={`flex flex-wrap ${designSystem.spacing.tagSpacing}`}>
            {tags.slice(0, 3).map((tag, index) => (
              <motion.div
                key={index}
                whileHover={{ scale: 1.05 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              >
                <Badge label={tag} size="sm" variant="default" />
              </motion.div>
            ))}
            {tags.length > 3 && (
              <Tooltip content={tags.slice(3).join(", ")}>
                <div>
                  <Badge label={`+${tags.length - 3}`} size="sm" variant="default" />
                </div>
              </Tooltip>
            )}
          </div>
        </div>

        {/* Enhanced Actions */}
        <div className={`flex ${designSystem.spacing.tagSpacing}`}>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
            <CTAButton
              label="Demo"
              icon={<Play className="w-4 h-4" />}
              onClick={demoHandler}
              variant="outline"
              size="sm"
            />
          </motion.div>
          <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="flex-1">
            <CTAButton
              label="Analyze Form"
              icon={<Target className="w-4 h-4" />}
              onClick={analyzeHandler}
              variant="primary"
              size="sm"
              fullWidth
            />
          </motion.div>
        </div>
      </div>

      {/* Hover Glow Effect */}
      <motion.div
        className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{
          background: "linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%)",
        }}
      />
    </motion.div>
  )
}
