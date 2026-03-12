import type React from "react"
import { motion } from "framer-motion"
import { useNavigate, useLocation } from "react-router-dom"

interface NavItem {
  icon: React.ElementType
  label: string
  path: string
}

interface BottomNavProps {
  items: NavItem[]
}

export function BottomNav({ items }: BottomNavProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const pathname = location.pathname

  return (
    <div
      className="fixed bottom-0 left-0 right-0 bg-black/70 backdrop-blur-md border-t border-white/[0.06] z-50"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex justify-center">
        <div className="flex items-center justify-between max-w-[430px] w-full px-2">
          {items.map((item, index) => {
            const Icon = item.icon
            const isActive = pathname === item.path

            return (
              <motion.button
                key={index}
                onClick={() => navigate(item.path)}
                className={`relative flex flex-col items-center py-2.5 px-1 flex-1 transition-all duration-150 ${
                  isActive ? "-translate-y-0.5" : "opacity-80"
                }`}
                whileTap={{ scale: 0.92 }}
              >
                <Icon
                  className={`w-5 h-5 mb-0.5 transition-colors duration-150 ${
                    isActive
                      ? "text-blue-500 drop-shadow-[0_0_8px_rgba(59,130,246,0.4)]"
                      : "text-slate-300"
                  }`}
                  strokeWidth={isActive ? 2.25 : 1.75}
                />
                <span
                  className={`text-[10px] transition-colors duration-150 ${
                    isActive
                      ? "text-blue-500 font-medium"
                      : "text-slate-300 font-normal"
                  }`}
                >
                  {item.label}
                </span>
              </motion.button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
