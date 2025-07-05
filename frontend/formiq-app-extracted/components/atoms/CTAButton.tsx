"use client"

import type React from "react"

import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"

interface CTAButtonProps {
  label: string
  icon?: React.ReactNode
  onClick: () => void
  variant?: "primary" | "secondary" | "outline" | "accent"
  size?: "sm" | "md" | "lg"
  fullWidth?: boolean
  loading?: boolean
  disabled?: boolean
  className?: string
}

export function CTAButton({
  label,
  icon,
  onClick,
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  disabled = false,
  className = "",
}: CTAButtonProps) {
  const variants = {
    primary: "cta-primary",
    secondary: "cta-secondary",
    outline: "cta-outline",
    accent: "cta-accent",
  }

  const sizes = {
    sm: "h-10 px-4 text-sm",
    md: "h-12 px-6 text-base",
    lg: "h-14 px-8 text-lg",
  }

  return (
    <motion.div
      whileHover={!disabled && !loading ? { scale: 1.02 } : {}}
      whileTap={!disabled && !loading ? { scale: 0.98 } : {}}
      className={fullWidth ? "w-full" : "inline-block"}
    >
      <Button
        onClick={onClick}
        disabled={loading || disabled}
        className={`
          ${variants[variant]} ${sizes[size]}
          ${fullWidth ? "w-full" : ""}
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}
          ${className}
        `}
      >
        {loading ? (
          <div className="flex items-center space-x-2">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Loading...</span>
          </div>
        ) : (
          <div className="flex items-center justify-center space-x-2">
            {icon && <span>{icon}</span>}
            <span>{label}</span>
          </div>
        )}
      </Button>
    </motion.div>
  )
}
