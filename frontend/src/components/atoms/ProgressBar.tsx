"use client"

import { motion } from "framer-motion"
import { useEffect, useState } from "react"

interface ProgressBarProps {
  percent: number
  gradient?: boolean
  labelLeft?: string
  labelRight?: string
  animated?: boolean
}

export function ProgressBar({ percent, gradient = false, labelLeft, labelRight, animated = true }: ProgressBarProps) {
  const [animatedPercent, setAnimatedPercent] = useState(0)

  useEffect(() => {
    if (animated) {
      const timer = setTimeout(() => setAnimatedPercent(percent), 100)
      return () => clearTimeout(timer)
    } else {
      setAnimatedPercent(percent)
    }
  }, [percent, animated])

  return (
    <div className="w-full space-y-2">
      {(labelLeft || labelRight) && (
        <div className="flex justify-between text-sm font-medium">
          {labelLeft && <span className="text-gray-700 dark:text-gray-300">{labelLeft}</span>}
          {labelRight && <span className="text-gray-500 dark:text-gray-400">{labelRight}</span>}
        </div>
      )}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${gradient ? "bg-gradient-to-r from-blue-500 to-purple-600" : "bg-blue-500"}`}
          initial={{ width: 0 }}
          animate={{ width: `${animatedPercent}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </div>
      <div className="text-right text-xs text-gray-500 dark:text-gray-400">{Math.round(animatedPercent)}%</div>
    </div>
  )
}
