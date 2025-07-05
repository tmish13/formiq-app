"use client"

import { motion } from "framer-motion"

interface SkeletonLoaderProps {
  className?: string
  variant?: "text" | "card" | "avatar" | "button"
  lines?: number
}

export function SkeletonLoader({ className = "", variant = "text", lines = 1 }: SkeletonLoaderProps) {
  const variants = {
    text: "h-4 bg-gray-200 dark:bg-gray-700 rounded",
    card: "h-32 bg-gray-200 dark:bg-gray-700 rounded-xl",
    avatar: "w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-full",
    button: "h-10 bg-gray-200 dark:bg-gray-700 rounded-lg",
  }

  if (variant === "text" && lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
          <motion.div
            key={i}
            className={`${variants.text} ${i === lines - 1 ? "w-3/4" : "w-full"}`}
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY, delay: i * 0.1 }}
          />
        ))}
      </div>
    )
  }

  return (
    <motion.div
      className={`${variants[variant]} ${className}`}
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.5, repeat: Number.POSITIVE_INFINITY }}
    />
  )
}
