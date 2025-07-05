"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Search, Filter, Clock, Dumbbell, Activity, Target, Play } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { BottomNavigation } from "@/components/bottom-navigation"

const categories = ["All", "Strength", "Mobility", "Corrective"]

const exercises = [
  {
    id: 1,
    title: "Perfect Squat Form",
    category: "Strength",
    duration: "5 min",
    difficulty: "Beginner",
    thumbnail: "/placeholder.svg?height=80&width=80&text=Squat",
    focusPoints: ["Knee alignment", "Hip depth", "Back posture", "Foot placement"],
    description: "Master the fundamental squat movement with proper form cues",
  },
  {
    id: 2,
    title: "Deadlift Technique",
    category: "Strength",
    duration: "7 min",
    difficulty: "Intermediate",
    thumbnail: "/placeholder.svg?height=80&width=80&text=Deadlift",
    focusPoints: ["Hip hinge", "Spine neutral", "Bar path", "Grip strength"],
    description: "Learn proper deadlift mechanics for maximum safety and effectiveness",
  },
  {
    id: 3,
    title: "Shoulder Mobility Flow",
    category: "Mobility",
    duration: "10 min",
    difficulty: "Beginner",
    thumbnail: "/placeholder.svg?height=80&width=80&text=Shoulder",
    focusPoints: ["Range of motion", "Joint stability", "Muscle activation"],
    description: "Improve shoulder flexibility and reduce stiffness",
  },
  {
    id: 4,
    title: "Hip Flexor Stretch",
    category: "Mobility",
    duration: "8 min",
    difficulty: "Beginner",
    thumbnail: "/placeholder.svg?height=80&width=80&text=Hip",
    focusPoints: ["Hip extension", "Pelvic tilt", "Core engagement"],
    description: "Release tight hip flexors from prolonged sitting",
  },
  {
    id: 5,
    title: "Knee Tracking Fix",
    category: "Corrective",
    duration: "6 min",
    difficulty: "Intermediate",
    thumbnail: "/placeholder.svg?height=80&width=80&text=Knee",
    focusPoints: ["Valgus correction", "Glute activation", "Ankle mobility"],
    description: "Correct common knee tracking issues during squats",
  },
  {
    id: 6,
    title: "Posture Reset",
    category: "Corrective",
    duration: "12 min",
    difficulty: "Beginner",
    thumbnail: "/placeholder.svg?height=80&width=80&text=Posture",
    focusPoints: ["Thoracic extension", "Cervical alignment", "Scapular stability"],
    description: "Counteract forward head posture and rounded shoulders",
  },
]

const getCategoryIcon = (category: string) => {
  switch (category) {
    case "Strength":
      return <Dumbbell className="w-4 h-4 text-blue-600" />
    case "Mobility":
      return <Activity className="w-4 h-4 text-green-600" />
    case "Corrective":
      return <Target className="w-4 h-4 text-orange-600" />
    default:
      return <Activity className="w-4 h-4 text-gray-600" />
  }
}

export default function LibraryPage() {
  const [selectedCategories, setSelectedCategories] = useState<string[]>(["All"])
  const [searchQuery, setSearchQuery] = useState("")

  const handleCategoryToggle = (category: string) => {
    if (category === "All") {
      setSelectedCategories(["All"])
    } else {
      const newCategories = selectedCategories.includes("All")
        ? [category]
        : selectedCategories.includes(category)
          ? selectedCategories.filter((c) => c !== category)
          : [...selectedCategories.filter((c) => c !== "All"), category]

      setSelectedCategories(newCategories.length === 0 ? ["All"] : newCategories)
    }
  }

  const filteredExercises = exercises.filter((exercise) => {
    const matchesCategory = selectedCategories.includes("All") || selectedCategories.includes(exercise.category)
    const matchesSearch =
      exercise.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      exercise.focusPoints.some((point) => point.toLowerCase().includes(searchQuery.toLowerCase()))
    return matchesCategory && matchesSearch
  })

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-20">
      <div className="px-4 py-6 space-y-6 max-w-4xl mx-auto">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">Exercise Library</h1>
          <p className="text-gray-600 dark:text-gray-400">Perfect your form with guided exercises</p>
        </motion.div>

        {/* Search */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <Input
              placeholder="Search exercises..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-gray-200/50 dark:border-gray-700/50"
            />
          </div>
        </motion.div>

        {/* Enhanced Category Filters */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <div className="flex items-center space-x-2 mb-4">
            <Filter className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Categories:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => {
              const isActive = selectedCategories.includes(category)
              return (
                <motion.button
                  key={category}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleCategoryToggle(category)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-purple-600 text-white shadow-lg ring-2 ring-purple-200 dark:ring-purple-800"
                      : "bg-white/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    {isActive && category !== "All" && getCategoryIcon(category)}
                    <span>{category}</span>
                    {isActive && <div className="w-2 h-2 bg-white rounded-full" />}
                  </div>
                </motion.button>
              )
            })}
          </div>
        </motion.div>

        {/* Enhanced Exercise List */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="space-y-3">
            {filteredExercises.map((exercise, index) => (
              <motion.div
                key={exercise.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
              >
                <Card className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-md hover:shadow-lg transition-all duration-200 cursor-pointer border border-gray-200/50 dark:border-gray-700/50">
                  <CardContent className="p-3">
                    <div className="flex items-center space-x-4">
                      {/* Enhanced Thumbnail */}
                      <div className="relative w-20 h-20 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 rounded-xl flex items-center justify-center overflow-hidden">
                        <img
                          src={exercise.thumbnail || "/placeholder.svg"}
                          alt={exercise.title}
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                          <Play className="w-6 h-6 text-white" />
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            {getCategoryIcon(exercise.category)}
                            <h3 className="font-semibold text-gray-900 dark:text-white text-lg truncate">
                              {exercise.title}
                            </h3>
                          </div>
                        </div>

                        {/* Compact Tagline */}
                        <div className="flex items-center space-x-2 mb-2">
                          <div className="flex items-center space-x-1 text-sm text-gray-600 dark:text-gray-400">
                            <Clock className="w-4 h-4" />
                            <span>{exercise.duration}</span>
                          </div>
                          <span className="text-gray-400">•</span>
                          <Badge variant="outline" className="text-xs px-2 py-0.5">
                            {exercise.category}
                          </Badge>
                          <span className="text-gray-400">•</span>
                          <Badge variant="secondary" className="text-xs px-2 py-0.5">
                            {exercise.difficulty}
                          </Badge>
                        </div>

                        {/* Enhanced Focus Points */}
                        <div className="mb-2">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Focus Points:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {exercise.focusPoints.slice(0, 2).map((point, idx) => (
                              <Badge
                                key={idx}
                                variant="outline"
                                className="text-xs px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800"
                              >
                                {point}
                              </Badge>
                            ))}
                            {exercise.focusPoints.length > 2 && (
                              <Badge variant="outline" className="text-xs px-2 py-0.5 text-gray-600 dark:text-gray-400">
                                +{exercise.focusPoints.length - 2} more
                              </Badge>
                            )}
                          </div>
                        </div>

                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{exercise.description}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {filteredExercises.length === 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-12">
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <Search className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No exercises found</h3>
              <p className="text-gray-600 dark:text-gray-400">Try adjusting your search or category filters</p>
            </motion.div>
          )}
        </motion.div>
      </div>

      <BottomNavigation activeTab="library" />
    </div>
  )
}
