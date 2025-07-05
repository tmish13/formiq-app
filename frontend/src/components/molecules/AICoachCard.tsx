"use client"

import { motion } from "framer-motion"
import { Brain, Sparkles } from "lucide-react"

interface AICoachCardProps {
  icon?: string
  tip: string
  backgroundGradient?: string
}

export function AICoachCard({
  icon = "🤖",
  tip,
  backgroundGradient = "from-purple-500 to-blue-600",
}: AICoachCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={`bg-gradient-to-r ${backgroundGradient} rounded-xl p-6 text-white relative overflow-hidden`}
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 opacity-10">
        <Brain className="w-full h-full" />
      </div>

      <div className="relative z-10">
        <div className="flex items-center space-x-3 mb-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center text-2xl">{icon}</div>
          <div>
            <h3 className="font-semibold text-lg">AI Coach Tip</h3>
            <div className="flex items-center space-x-1">
              <Sparkles className="w-4 h-4" />
              <span className="text-sm opacity-90">Personalized for you</span>
            </div>
          </div>
        </div>

        <p className="text-white/95 leading-relaxed text-base">{tip}</p>

        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
          className="absolute bottom-4 right-4 w-3 h-3 bg-white/30 rounded-full"
        />
      </div>
    </motion.div>
  )
}
