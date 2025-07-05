"use client"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Settings, Type, Contrast, Volume2, Keyboard, Eye } from "lucide-react"

interface AccessibilityControlsProps {
  onSettingsChange?: (settings: AccessibilitySettings) => void
}

interface AccessibilitySettings {
  highContrast: boolean
  largeText: boolean
  reduceMotion: boolean
  voiceCommands: boolean
  keyboardNav: boolean
  screenReader: boolean
}

export function AccessibilityControls({ onSettingsChange }: AccessibilityControlsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [settings, setSettings] = useState<AccessibilitySettings>({
    highContrast: false,
    largeText: false,
    reduceMotion: false,
    voiceCommands: false,
    keyboardNav: false,
    screenReader: false,
  })

  useEffect(() => {
    // Apply settings to document
    const root = document.documentElement

    if (settings.highContrast) {
      root.classList.add("high-contrast")
    } else {
      root.classList.remove("high-contrast")
    }

    if (settings.largeText) {
      root.classList.add("large-text")
    } else {
      root.classList.remove("large-text")
    }

    if (settings.reduceMotion) {
      root.classList.add("reduce-motion")
    } else {
      root.classList.remove("reduce-motion")
    }

    onSettingsChange?.(settings)
  }, [settings, onSettingsChange])

  const toggleSetting = (key: keyof AccessibilitySettings) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const accessibilityOptions = [
    {
      key: "highContrast" as const,
      label: "High Contrast",
      description: "Increase color contrast for better visibility",
      icon: <Contrast className="w-5 h-5" />,
    },
    {
      key: "largeText" as const,
      label: "Large Text",
      description: "Increase text size throughout the app",
      icon: <Type className="w-5 h-5" />,
    },
    {
      key: "reduceMotion" as const,
      label: "Reduce Motion",
      description: "Minimize animations and transitions",
      icon: <Eye className="w-5 h-5" />,
    },
    {
      key: "voiceCommands" as const,
      label: "Voice Commands",
      description: "Enable voice control for navigation",
      icon: <Volume2 className="w-5 h-5" />,
    },
    {
      key: "keyboardNav" as const,
      label: "Keyboard Navigation",
      description: "Enhanced keyboard navigation support",
      icon: <Keyboard className="w-5 h-5" />,
    },
  ]

  return (
    <>
      {/* Accessibility Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-24 right-4 z-40 w-12 h-12 bg-purple-600 text-white rounded-full shadow-lg flex items-center justify-center"
        aria-label="Accessibility Settings"
      >
        <Settings className="w-6 h-6" />
      </motion.button>

      {/* Accessibility Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed bottom-40 right-4 w-80 bg-white dark:bg-gray-800 rounded-xl shadow-2xl z-50 border border-gray-200 dark:border-gray-700"
          >
            <div className="p-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Accessibility Settings</h3>

              <div className="space-y-4">
                {accessibilityOptions.map((option) => (
                  <div key={option.key} className="flex items-start space-x-3">
                    <button
                      onClick={() => toggleSetting(option.key)}
                      className={`
                        w-12 h-6 rounded-full transition-colors relative
                        ${settings[option.key] ? "bg-purple-600" : "bg-gray-300 dark:bg-gray-600"}
                      `}
                      aria-pressed={settings[option.key]}
                    >
                      <div
                        className={`
                          w-5 h-5 bg-white rounded-full transition-transform absolute top-0.5
                          ${settings[option.key] ? "translate-x-6" : "translate-x-0.5"}
                        `}
                      />
                    </button>

                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        {option.icon}
                        <h4 className="font-medium text-gray-900 dark:text-white">{option.label}</h4>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">{option.description}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Voice Command Status */}
              {settings.voiceCommands && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mt-4 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse" />
                    <span className="text-sm font-medium text-purple-700 dark:text-purple-300">
                      Voice commands active
                    </span>
                  </div>
                  <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">
                    Say "Hey FormIQ" to start a command
                  </p>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Keyboard Navigation Hints */}
      {settings.keyboardNav && (
        <div className="fixed top-4 left-4 bg-black/80 text-white px-3 py-2 rounded-lg text-sm z-50">
          <div className="flex items-center space-x-2">
            <Keyboard className="w-4 h-4" />
            <span>Tab to navigate • Enter to select • Esc to close</span>
          </div>
        </div>
      )}
    </>
  )
}
