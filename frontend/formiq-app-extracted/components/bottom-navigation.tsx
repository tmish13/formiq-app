"use client"

import { motion } from "framer-motion"
import { Home, Camera, TrendingUp, BookOpen, User } from "lucide-react"
import Link from "next/link"

interface BottomNavigationProps {
  activeTab: "home" | "record" | "progress" | "library" | "profile"
}

const navItems = [
  { id: "home", icon: Home, label: "Home", href: "/" },
  { id: "record", icon: Camera, label: "Record", href: "/record" },
  { id: "progress", icon: TrendingUp, label: "Progress", href: "/progress" },
  { id: "library", icon: BookOpen, label: "Library", href: "/library" },
  { id: "profile", icon: User, label: "Profile", href: "/profile" },
]

export function BottomNavigation({ activeTab }: BottomNavigationProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-t border-gray-200/50 dark:border-gray-800/50 safe-area-pb z-50">
      <div className="flex justify-center">
        <div className="flex items-center justify-between max-w-md w-full px-4">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id

            return (
              <Link key={item.id} href={item.href} className="flex-1">
                <motion.div className="relative flex flex-col items-center py-3 px-2" whileTap={{ scale: 0.95 }}>
                  {/* Active Indicator */}
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute -top-1 w-12 h-1 bg-purple-600 rounded-full"
                      style={{
                        left: "50%",
                        transform: "translateX(-50%)",
                      }}
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}

                  {/* Icon */}
                  <Icon
                    className={`w-6 h-6 mb-1 transition-colors ${
                      isActive ? "text-purple-600 dark:text-purple-400" : "text-gray-500 dark:text-gray-400"
                    }`}
                  />

                  {/* Label */}
                  <span
                    className={`text-xs font-medium transition-colors ${
                      isActive ? "text-purple-600 dark:text-purple-400" : "text-gray-500 dark:text-gray-400"
                    }`}
                  >
                    {item.label}
                  </span>
                </motion.div>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}
