"use client"

import type React from "react"

import { motion } from "framer-motion"
import { useEffect, useState } from "react"

interface StatCardProps {
  title: string
  value: string
  delta?: string
  color: "blue" | "green" | "purple" | "orange"
  icon?: React.ReactNode
}

export function StatCard({ title, value, delta, color, icon }: StatCardProps) {
  const [animatedValue, setAnimatedValue] = useState("0")

  const colorClasses = {
    blue: "from-blue-500 to-blue-600",
    green: "from-green-500 to-green-600",
    purple: "from-purple-500 to-purple-600",
    orange: "from-orange-500 to-orange-600",
  }

  const bgClasses = {
    blue: "bg-blue-50 dark:bg-blue-900/20",
    green: "bg-green-50 dark:bg-green-900/20",
    purple: "bg-purple-50 dark:bg-purple-900/20",
    orange: "bg-orange-50 dark:bg-orange-900/20",
  }

  useEffect(() => {
    // Animate number counting
    const numericValue = Number.parseInt(value.replace(/\D/g, ""))
    if (!isNaN(numericValue)) {
      let current = 0
      const increment = numericValue / 30
      const timer = setInterval(() => {
        current += increment
        if (current >= numericValue) {
          setAnimatedValue(value)
          clearInterval(timer)
        } else {
          setAnimatedValue(Math.floor(current) + value.replace(/\d/g, ""))
        }
      }, 50)
      return () => clearInterval(timer)
    } else {
      setAnimatedValue(value)
    }
  }, [value])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -2 }}
      transition={{ duration: 0.2 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-200"
    >
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl ${bgClasses[color]} flex items-center justify-center`}>
          {icon || <div className={`w-6 h-6 rounded-full bg-gradient-to-r ${colorClasses[color]}`} />}
        </div>
        {delta && <span className="text-sm font-medium text-green-600 dark:text-green-400">{delta}</span>}
      </div>

      <div className="space-y-1">
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{animatedValue}</p>
      </div>
    </motion.div>
  )
}
