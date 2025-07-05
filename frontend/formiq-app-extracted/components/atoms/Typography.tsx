"use client"

import { cn } from "@/lib/utils"
import { designSystem } from "@/lib/design-system"
import type React from "react"

interface TypographyProps {
  variant: keyof typeof designSystem.typography
  children: React.ReactNode
  className?: string
  as?: keyof JSX.IntrinsicElements
}

export function Typography({ variant, children, className, as = "p" }: TypographyProps) {
  const Component = as as any

  return <Component className={cn(designSystem.typography[variant], className)}>{children}</Component>
}

// Specific typography components for consistency
export function Heading1({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Typography variant="h1" as="h1" className={className}>
      {children}
    </Typography>
  )
}

export function Heading2({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Typography variant="h2" as="h2" className={className}>
      {children}
    </Typography>
  )
}

export function Heading3({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <Typography variant="h3" as="h3" className={className}>
      {children}
    </Typography>
  )
}

export function StatNumber({
  children,
  size = "medium",
  className,
}: {
  children: React.ReactNode
  size?: "small" | "medium" | "large"
  className?: string
}) {
  const sizeMap = {
    small: "statSmall",
    medium: "statMedium",
    large: "statLarge",
  } as const

  return (
    <Typography variant={sizeMap[size]} className={className}>
      {children}
    </Typography>
  )
}
