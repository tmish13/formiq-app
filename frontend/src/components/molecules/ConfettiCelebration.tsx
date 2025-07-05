"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle, Target } from "lucide-react"

interface ConfettiCelebrationProps {
  trigger: boolean
  onComplete: () => void
  duration?: number
}

export function ConfettiCelebration({ trigger, onComplete, duration = 3000 }: ConfettiCelebrationProps) {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    if (trigger) {
      setIsVisible(true)
      const timer = setTimeout(() => {
        setIsVisible(false)
        onComplete()
      }, duration)

      return () => clearTimeout(timer)
    }
  }, [trigger, duration, onComplete])

  const particles = Array.from({ length: 30 }, (_, i) => ({
    id: i,
    color: ["#3b82f6", "#10b981", "#8b5cf6"][i % 3],
    delay: Math.random() * 1,
    x: Math.random() * 100,
    rotation: Math.random() * 360,
    size: Math.random() * 4 + 2,
  }))

  return (
    <AnimatePresence>
      {isVisible && (
        <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
          {/* Subtle particle animation */}
          {particles.map((particle) => (
            <motion.div
              key={particle.id}
              className="absolute rounded-full opacity-80"
              style={{
                backgroundColor: particle.color,
                width: particle.size,
                height: particle.size,
                left: `${particle.x}%`,
                top: "-10px",
              }}
              initial={{
                y: -10,
                rotate: 0,
                opacity: 0.8,
              }}
              animate={{
                y: window.innerHeight + 10,
                rotate: particle.rotation,
                opacity: 0,
              }}
              transition={{
                duration: 2.5,
                delay: particle.delay,
                ease: "easeOut",
              }}
            />
          ))}

          {/* Professional success message */}
          <motion.div
            className="absolute inset-0 flex items-center justify-center"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <div className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-2xl p-8 text-center shadow-2xl border border-gray-200/50 dark:border-gray-700/50 max-w-md mx-4">
              <motion.div
                className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mx-auto mb-4"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              >
                <CheckCircle className="w-8 h-8 text-white" />
              </motion.div>

              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">Setup Complete!</h2>
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  You're all set to start improving your form with AI-powered analysis.
                </p>

                <div className="flex items-center justify-center space-x-2 text-sm text-blue-600 dark:text-blue-400">
                  <Target className="w-4 h-4" />
                  <span>Ready to begin your fitness journey</span>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
