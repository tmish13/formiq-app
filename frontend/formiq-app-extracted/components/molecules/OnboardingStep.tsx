"use client"

import type React from "react"

import { motion } from "framer-motion"
import { CTAButton } from "@/components/atoms/CTAButton"
import { ChevronLeft, ChevronRight } from "lucide-react"

interface OnboardingStepProps {
  title: string
  description: string
  illustration: string
  currentStep: number
  totalSteps: number
  onNext: () => void
  onPrev?: () => void
  onSkip?: () => void
  nextLabel?: string
  children?: React.ReactNode
}

export function OnboardingStep({
  title,
  description,
  illustration,
  currentStep,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  nextLabel = "Continue",
  children,
}: OnboardingStepProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 50 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -50 }}
      className="flex flex-col h-full"
    >
      {/* Progress indicator */}
      <div className="flex items-center justify-between p-4">
        <div className="flex space-x-2">
          {Array.from({ length: totalSteps }).map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-colors ${
                index < currentStep ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
              }`}
            />
          ))}
        </div>
        {onSkip && (
          <button
            onClick={onSkip}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
          >
            Skip
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="w-48 h-48 mb-8"
        >
          <img
            src={illustration || "/placeholder.svg?height=200&width=200"}
            alt={title}
            className="w-full h-full object-contain"
          />
        </motion.div>

        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-2xl font-bold text-gray-900 dark:text-white mb-4"
        >
          {title}
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="text-gray-600 dark:text-gray-400 text-lg leading-relaxed mb-8 max-w-md"
        >
          {description}
        </motion.p>

        {children && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="w-full max-w-sm mb-8"
          >
            {children}
          </motion.div>
        )}
      </div>

      {/* Navigation */}
      <div className="p-6 space-y-4">
        <CTAButton
          label={nextLabel}
          icon={<ChevronRight className="w-4 h-4" />}
          onClick={onNext}
          variant="primary"
          size="lg"
          fullWidth
        />

        {onPrev && currentStep > 1 && (
          <CTAButton
            label="Back"
            icon={<ChevronLeft className="w-4 h-4" />}
            onClick={onPrev}
            variant="outline"
            size="lg"
            fullWidth
          />
        )}
      </div>
    </motion.div>
  )
}
