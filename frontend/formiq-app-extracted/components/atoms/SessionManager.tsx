"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { AlertTriangle, RefreshCw, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SessionManagerProps {
  enabled?: boolean
  sessionDuration?: number // in minutes
  warningTime?: number // minutes before expiry to show warning
  onSessionExpired?: () => void
}

export function SessionManager({
  enabled = false, // Disabled by default for MVP
  sessionDuration = 30,
  warningTime = 5,
  onSessionExpired,
}: SessionManagerProps) {
  const [timeLeft, setTimeLeft] = useState(sessionDuration * 60)
  const [showWarning, setShowWarning] = useState(false)
  const [isExpired, setIsExpired] = useState(false)

  useEffect(() => {
    if (!enabled) return

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        const newTime = prev - 1

        // Show warning when approaching expiry
        if (newTime <= warningTime * 60 && newTime > 0) {
          setShowWarning(true)
        }

        // Handle expiry
        if (newTime <= 0) {
          setIsExpired(true)
          onSessionExpired?.()
          return 0
        }

        return newTime
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [enabled, warningTime, onSessionExpired])

  const handleRefreshSession = () => {
    setTimeLeft(sessionDuration * 60)
    setShowWarning(false)
    setIsExpired(false)
  }

  const handleRedirectToAuth = () => {
    // Redirect to onboarding instead of non-existent login page
    window.location.href = "/onboarding"
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  if (!enabled) return null

  return (
    <>
      {/* Session Warning */}
      <AnimatePresence>
        {showWarning && !isExpired && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className="fixed top-4 left-4 right-4 z-50 mx-auto max-w-md"
          >
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 shadow-lg">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">Session expiring soon</h3>
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    Your session will expire in {formatTime(timeLeft)}
                  </p>
                </div>
                <Button size="sm" onClick={handleRefreshSession} className="flex-shrink-0">
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Extend
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Session Expired Modal */}
      <AnimatePresence>
        {isExpired && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white dark:bg-slate-800 rounded-xl p-6 mx-4 max-w-md w-full shadow-2xl"
            >
              <div className="text-center">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">
                  Time for a fresh start! 💪
                </h3>
                <p className="text-slate-600 dark:text-slate-400 mb-6">
                  Your session has expired to keep your data secure. Ready to jump back into your fitness journey?
                </p>
                <div className="space-y-3">
                  <Button onClick={handleRedirectToAuth} className="w-full">
                    Continue Training
                  </Button>
                  <Button variant="outline" onClick={handleRefreshSession} className="w-full bg-transparent">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Session
                  </Button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
