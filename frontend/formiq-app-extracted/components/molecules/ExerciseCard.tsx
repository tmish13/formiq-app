"use client"

import { motion } from "framer-motion"
import { Play, Target, Star, Clock } from "lucide-react"
import { Badge } from "@/components/atoms/Badge"
import { CTAButton } from "@/components/atoms/CTAButton"

interface ExerciseCardProps {
  thumbnail: string
  title: string
  tags: string[]
  rating: number
  duration?: string
  difficulty?: "Beginner" | "Intermediate" | "Advanced"
  demoHandler: () => void
  analyzeHandler: () => void
}

export function ExerciseCard({
  thumbnail,
  title,
  tags,
  rating,
  duration,
  difficulty,
  demoHandler,
  analyzeHandler,
}: ExerciseCardProps) {
  const difficultyColors = {
    Beginner: "success",
    Intermediate: "warning",
    Advanced: "purple",
  } as const

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, scale: 1.02 }}
      className="bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-all duration-200"
    >
      {/* Thumbnail */}
      <div className="relative h-48 overflow-hidden">
        <img
          src={thumbnail || "/placeholder.svg?height=200&width=300"}
          alt={title}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />

        {/* Rating */}
        <div className="absolute top-3 right-3 flex items-center space-x-1 bg-black/50 rounded-full px-2 py-1">
          <Star className="w-3 h-3 text-yellow-400 fill-current" />
          <span className="text-white text-sm font-medium">{rating}</span>
        </div>

        {/* Play overlay */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={demoHandler}
          className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity duration-200"
        >
          <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-full flex items-center justify-center">
            <Play className="w-8 h-8 text-white ml-1" />
          </div>
        </motion.button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{title}</h3>

          <div className="flex items-center space-x-2 mb-3">
            {difficulty && <Badge label={difficulty} variant={difficultyColors[difficulty]} size="sm" />}
            {duration && <Badge label={duration} icon={<Clock className="w-3 h-3" />} size="sm" />}
          </div>

          <div className="flex flex-wrap gap-1">
            {tags.slice(0, 3).map((tag, index) => (
              <Badge key={index} label={tag} size="sm" />
            ))}
            {tags.length > 3 && <Badge label={`+${tags.length - 3}`} size="sm" />}
          </div>
        </div>

        {/* Actions */}
        <div className="flex space-x-2">
          <CTAButton
            label="Demo"
            icon={<Play className="w-4 h-4" />}
            onClick={demoHandler}
            variant="outline"
            size="sm"
          />
          <CTAButton
            label="Analyze"
            icon={<Target className="w-4 h-4" />}
            onClick={analyzeHandler}
            variant="primary"
            size="sm"
            fullWidth
          />
        </div>
      </div>
    </motion.div>
  )
}
