"use client"

import type React from "react"

import { motion } from "framer-motion"
import { ChevronRight } from "lucide-react"
import { Switch } from "@/components/ui/switch"

interface SettingOption {
  label: string
  type: "toggle" | "link"
  value?: boolean
  icon?: React.ReactNode
  description?: string
  onToggle?: (value: boolean) => void
  onClick?: () => void
  danger?: boolean
}

interface SettingGroupProps {
  title: string
  options: SettingOption[]
}

export function SettingGroup({ title, options }: SettingGroupProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>

      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {options.map((option, index) => (
          <motion.div
            key={index}
            whileHover={{ backgroundColor: "rgba(0,0,0,0.02)" }}
            className={`
              px-6 py-4 flex items-center justify-between cursor-pointer
              ${option.danger ? "hover:bg-red-50 dark:hover:bg-red-900/10" : ""}
            `}
            onClick={option.type === "link" ? option.onClick : undefined}
          >
            <div className="flex items-center space-x-3">
              {option.icon && (
                <div
                  className={`
                  w-8 h-8 rounded-lg flex items-center justify-center
                  ${option.danger ? "bg-red-100 dark:bg-red-900/20" : "bg-gray-100 dark:bg-gray-700"}
                `}
                >
                  <div className={option.danger ? "text-red-600" : "text-gray-600 dark:text-gray-400"}>
                    {option.icon}
                  </div>
                </div>
              )}

              <div>
                <p
                  className={`
                  font-medium
                  ${option.danger ? "text-red-600 dark:text-red-400" : "text-gray-900 dark:text-white"}
                `}
                >
                  {option.label}
                </p>
                {option.description && <p className="text-sm text-gray-500 dark:text-gray-400">{option.description}</p>}
              </div>
            </div>

            <div className="flex items-center">
              {option.type === "toggle" ? (
                <Switch checked={option.value || false} onCheckedChange={option.onToggle} />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-400" />
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
