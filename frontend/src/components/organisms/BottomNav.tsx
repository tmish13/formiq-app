"use client"

import type React from "react"

import { motion } from "framer-motion"
import { useNavigate, useLocation } from "react-router-dom"

interface NavItem {
  icon: React.ReactNode
  label: string
  path: string
  active?: boolean
}

interface BottomNavProps {
  items: NavItem[]
}

export function BottomNav({ items }: BottomNavProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const pathname = location.pathname

  return (
    <motion.div
      initial={{ y: 100 }}
      animate={{ y: 0 }}
      className="fixed bottom-0 left-0 right-0 bg-white/95 dark:bg-gray-800/95 backdrop-blur-lg border-t border-gray-200 dark:border-gray-700 z-50"
      style={{ 
        paddingBottom: "max(env(safe-area-inset-bottom), 12px)",
        paddingTop: "12px",
        paddingLeft: "max(env(safe-area-inset-left), 8px)",
        paddingRight: "max(env(safe-area-inset-right), 8px)"
      }}
    >
      <div className="grid grid-cols-5 h-16 px-2 max-w-lg mx-auto">
        {items.map((item, index) => {
          const isActive = pathname === item.path

          return (
            <motion.button
              key={index}
              onClick={() => navigate(item.path)}
              className={`
                flex flex-col items-center justify-center space-y-1 relative rounded-lg p-2
                ${isActive ? "text-blue-600 dark:text-blue-400" : "text-gray-600 dark:text-gray-400"}
                transition-all duration-200
              `}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {isActive && (
                <motion.div
                  layoutId="activeNavItem"
                  className="absolute inset-0 bg-blue-50 dark:bg-blue-900/20 rounded-lg"
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}

              <motion.div
                animate={isActive ? { scale: [1, 1.2, 1] } : {}}
                transition={{ duration: 0.3 }}
                className="relative z-10 mb-1"
              >
                {item.icon}
              </motion.div>

              <span className="text-xs font-medium relative z-10 leading-tight">{item.label}</span>
            </motion.button>
          )
        })}
      </div>
    </motion.div>
  )
}
