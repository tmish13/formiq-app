"use client"

import { motion } from "framer-motion"
import { Clock, Target, Play } from "lucide-react"
import { CTAButton } from "@/components/atoms/CTAButton"
import { Badge } from "@/components/atoms/Badge"

interface WorkoutBannerProps {
  title: string
  time: string
  exercises: number
  buttonLabel: string
  difficulty?: string
  description?: string
  onStart: () => void
}

export function WorkoutBanner({
  title,
  time,
  exercises,
  buttonLabel,
  difficulty,
  description,
  onStart,
}: WorkoutBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      whileHover={{ scale: 1.01 }}
      className="bg-gradient-to-r from-green-500 to-emerald-600 rounded-xl p-6 text-white relative overflow-hidden"
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-24 h-24 opacity-10">
        <Target className="w-full h-full" />
      </div>

      <div className="relative z-10">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <h3 className="text-xl font-bold">{title}</h3>
              {difficulty && <Badge label={difficulty} variant="default" size="sm" />}
            </div>

            {description && <p className="text-green-100 mb-3">{description}</p>}

            <div className="flex items-center space-x-4 text-green-100">
              <div className="flex items-center space-x-1">
                <Clock className="w-4 h-4" />
                <span className="text-sm">{time}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Target className="w-4 h-4" />
                <span className="text-sm">{exercises} exercises</span>
              </div>
            </div>
          </div>

          <div className="sm:ml-4">
            <CTAButton
              label={buttonLabel}
              icon={<Play className="w-5 h-5" />}
              onClick={onStart}
              variant="secondary"
              size="lg"
            />
          </div>
        </div>
      </div>
    </motion.div>
  )
}
