"use client"

import { motion } from "framer-motion"
import { Crown, Sparkles, Zap } from "lucide-react"
import { Tooltip } from "@/components/atoms/Tooltip"

interface PremiumBadgeProps {
  tier: "Basic" | "Pro" | "Premium"
  size?: "sm" | "md" | "lg"
  animated?: boolean
  showTooltip?: boolean
}

export function PremiumBadge({ tier, size = "md", animated = false, showTooltip = true }: PremiumBadgeProps) {
  const tierConfig = {
    Basic: {
      icon: null,
      color: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400",
      border: "border-slate-200 dark:border-slate-600",
      tooltip: "Basic plan - Essential features",
    },
    Pro: {
      icon: <Crown className="w-3 h-3" />,
      color: "bg-gradient-to-r from-blue-500 to-purple-600 text-white",
      border: "border-blue-300 dark:border-purple-500",
      tooltip: "Pro plan - Advanced AI coaching & analytics",
      glow: "shadow-lg shadow-blue-500/25",
    },
    Premium: {
      icon: <Sparkles className="w-3 h-3" />,
      color: "bg-gradient-to-r from-purple-600 to-pink-600 text-white",
      border: "border-purple-300 dark:border-pink-500",
      tooltip: "Premium plan - All features + priority support",
      glow: "shadow-lg shadow-purple-500/25",
    },
  }

  const sizeConfig = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  }

  const config = tierConfig[tier]
  const sizeClass = sizeConfig[size]

  if (tier === "Basic") {
    return (
      <span className={`inline-flex items-center rounded-full font-medium ${config.color} ${sizeClass}`}>{tier}</span>
    )
  }

  const badge = (
    <motion.div
      initial={animated ? { scale: 0, rotate: -180 } : {}}
      animate={animated ? { scale: 1, rotate: 0 } : {}}
      transition={animated ? { type: "spring", stiffness: 500, damping: 30 } : {}}
      whileHover={{ scale: 1.05 }}
      className={`
        inline-flex items-center space-x-1 rounded-full font-medium border
        ${config.color} ${config.border} ${sizeClass}
        ${config.glow || ""}
        ${animated ? "animate-pulse" : ""}
        relative overflow-hidden
      `}
    >
      {/* Animated background for premium tiers */}
      {tier !== "Basic" && (
        <motion.div
          animate={{
            x: ["-100%", "100%"],
          }}
          transition={{
            duration: 2,
            repeat: Number.POSITIVE_INFINITY,
            ease: "linear",
          }}
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
        />
      )}

      <div className="relative z-10 flex items-center space-x-1">
        {config.icon && (
          <motion.div
            animate={animated ? { rotate: [0, 360] } : {}}
            transition={animated ? { duration: 2, repeat: Number.POSITIVE_INFINITY, ease: "linear" } : {}}
          >
            {config.icon}
          </motion.div>
        )}
        <span>{tier}</span>
        {tier === "Premium" && (
          <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY }}>
            <Zap className="w-3 h-3" />
          </motion.div>
        )}
      </div>
    </motion.div>
  )

  if (showTooltip) {
    return <Tooltip content={config.tooltip}>{badge}</Tooltip>
  }

  return badge
}
