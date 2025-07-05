"use client"

import type React from "react"

import { motion } from "framer-motion"

interface IllustrationBlockProps {
  image: string
  message: string
  title?: string
  action?: React.ReactNode
}

export function IllustrationBlock({ image, message, title, action }: IllustrationBlockProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="text-center py-12 px-6"
    >
      <motion.div initial={{ y: 20 }} animate={{ y: 0 }} transition={{ delay: 0.2 }} className="w-32 h-32 mx-auto mb-6">
        <img
          src={image || "/placeholder.svg?height=128&width=128"}
          alt="Illustration"
          className="w-full h-full object-contain"
        />
      </motion.div>

      {title && (
        <motion.h2
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-2xl font-bold text-gray-900 dark:text-white mb-4"
        >
          {title}
        </motion.h2>
      )}

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-gray-600 dark:text-gray-400 text-lg leading-relaxed mb-8 max-w-md mx-auto"
      >
        {message}
      </motion.p>

      {action && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          {action}
        </motion.div>
      )}
    </motion.div>
  )
}
