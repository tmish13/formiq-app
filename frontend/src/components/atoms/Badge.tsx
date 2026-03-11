"use client"

import React from "react"
import { motion } from "framer-motion"

interface BadgeProps {
  label: string
  icon?: React.ReactNode
  animated?: boolean
  variant?: "default" | "success" | "warning" | "purple"
  size?: "sm" | "md" | "lg"
}

export function Badge({ label, icon, animated = false, variant = "default", size = "md" }: BadgeProps) {
  const variants = {
    default: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
    success: "bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400",
    warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400",
    purple: "bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400",
  }

  const sizes = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-2 text-base",
  }

  const BadgeComponent = (
    <span
      className={`
      inline-flex items-center space-x-1 rounded-full font-medium
      ${variants[variant]} ${sizes[size]}
      ${animated ? "animate-pulse" : ""}
    `}
    >
      {icon && <span>{icon}</span>}
      <span>{label}</span>
    </span>
  )

  if (animated) {
    return (
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      >
        {BadgeComponent}
      </motion.div>
    )
  }

  return BadgeComponent
}
