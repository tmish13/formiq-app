"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Bell, Settings, Brain, Sparkles } from "lucide-react"

interface HeaderProps {
  variant?: "default" | "dark"
}

export function Header({ variant = "default" }: HeaderProps) {
  const isDark = variant === "dark"

  return (
    <header
      className={`sticky top-0 z-50 border-b ${
        isDark ? "bg-gray-900 border-gray-700" : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
      }`}
    >
      <div className="px-4 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isDark ? "bg-blue-600" : "bg-gradient-to-r from-blue-600 to-purple-600"
            }`}
          >
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className={`text-lg font-bold ${isDark ? "text-white" : "text-gray-900 dark:text-white"}`}>FormIQ</h1>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className={`text-xs ${isDark ? "text-gray-300" : "text-gray-500 dark:text-gray-400"}`}>
                AI Active
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Badge
            variant="secondary"
            className={`hidden sm:flex text-xs ${
              isDark
                ? "bg-purple-900/30 text-purple-300"
                : "bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400"
            }`}
          >
            <Sparkles className="w-3 h-3 mr-1" />
            94% AI Confidence
          </Badge>
          <Button
            variant="ghost"
            size="sm"
            className={`${
              isDark ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-600 dark:text-gray-400"
            }`}
          >
            <Bell className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={`${
              isDark ? "text-gray-300 hover:text-white hover:bg-gray-800" : "text-gray-600 dark:text-gray-400"
            }`}
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </header>
  )
}
