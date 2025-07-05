"use client"

import type React from "react"

import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { Tooltip } from "@/components/atoms/Tooltip"
import { StatNumber } from "@/components/atoms/Typography"
import { designSystem } from "@/lib/design-system"

interface EnhancedStatCardProps {
  title: string
  value: string
  delta?: string
  color?: "blue" | "green" | "orange" | "purple" | "teal"
  icon?: React.ReactNode
  tooltip?: string
  celebration?: boolean
  size?: "small" | "medium" | "large"
  trend?: "up" | "down" | "neutral"
}

export function EnhancedStatCard({
  title,
  value,
  delta,
  color = "blue",
  icon,
  tooltip,
  celebration = false,
  size = "medium",
  trend,
}: EnhancedStatCardProps) {
  const colorVariants = {
    blue: {
      bg: "bg-gradient-to-br from-blue-50 to-slate-50 dark:from-slate-800 dark:to-slate-900",
      border: "border-blue-200/50 dark:border-blue-800/50",
      accent: "text-blue-600 dark:text-blue-400",
      glow: celebration ? "shadow-lg shadow-blue-500/20" : "",
    },
    green: {
      bg: "bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-slate-800 dark:to-slate-900",
      border: "border-emerald-200/50 dark:border-emerald-800/50",
      accent: "text-emerald-600 dark:text-emerald-400",
      glow: celebration ? "shadow-lg shadow-emerald-500/20" : "",
    },
    orange: {
      bg: "bg-gradient-to-br from-orange-50 to-amber-50 dark:from-slate-800 dark:to-slate-900",
      border: "border-orange-200/50 dark:border-orange-800/50",
      accent: "text-orange-600 dark:text-orange-400",
      glow: celebration ? "shadow-lg shadow-orange-500/20" : "",
    },
    purple: {
      bg: "bg-gradient-to-br from-purple-50 to-violet-50 dark:from-slate-800 dark:to-slate-900",
      border: "border-purple-200/50 dark:border-purple-800/50",
      accent: "text-purple-600 dark:text-purple-400",
      glow: celebration ? "shadow-lg shadow-purple-500/20" : "",
    },
    teal: {
      bg: "bg-gradient-to-br from-teal-50 to-cyan-50 dark:from-slate-800 dark:to-slate-900",
      border: "border-teal-200/50 dark:border-teal-800/50",
      accent: "text-teal-600 dark:text-teal-400",
      glow: celebration ? "shadow-lg shadow-teal-500/20" : "",
    },
  }

  const getTrendIcon = () => {
    if (!trend) return null
    switch (trend) {
      case "up":
        return <TrendingUp className="w-3 h-3 text-emerald-500" />
      case "down":
        return <TrendingDown className="w-3 h-3 text-red-500" />
      case "neutral":
        return <Minus className="w-3 h-3 text-slate-400" />
    }
  }

  const variant = colorVariants[color]

  const cardContent = (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02, y: -4 }}
      className={`
        ${variant.bg} ${variant.border} ${variant.glow}
        rounded-xl border backdrop-blur-sm
        ${designSystem.spacing.cardInternal}
        ${designSystem.shadows.card}
        ${designSystem.animations.cardHover}
        relative overflow-hidden
        ${celebration ? "animate-pulse" : ""}
      `}
    >
      {/* Background pattern for AI theme */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0 bg-gradient-to-br from-current/10 to-transparent" />
      </div>

      <div className="relative z-10">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">{title}</p>
            <div className="flex items-baseline space-x-2">
              <StatNumber size={size} className={variant.accent}>
                {value}
              </StatNumber>
              {celebration && (
                <motion.span
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 0.5, repeat: 3 }}
                  className="text-lg"
                >
                  ✨
                </motion.span>
              )}
            </div>
          </div>

          {icon && (
            <motion.div
              whileHover={{ rotate: 12, scale: 1.1 }}
              className={`p-2 rounded-lg ${variant.bg} ${variant.border} border`}
            >
              {icon}
            </motion.div>
          )}
        </div>

        {delta && (
          <div className="flex items-center space-x-1">
            {getTrendIcon()}
            <span className="text-sm font-medium text-slate-600 dark:text-slate-400">{delta}</span>
          </div>
        )}
      </div>

      {/* Celebration glow effect */}
      {celebration && (
        <motion.div
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
          className={`absolute inset-0 rounded-xl ${variant.glow} pointer-events-none`}
        />
      )}
    </motion.div>
  )

  if (tooltip) {
    return <Tooltip content={tooltip}>{cardContent}</Tooltip>
  }

  return cardContent
}
