"use client"

import { useState } from "react"
import { Play, Pause, SkipBack, SkipForward, Eye } from "lucide-react"

interface TimelineFrame {
  timestamp: number
  score: number
  feedback: string
  issues: string[]
  poseData: {
    joints: Array<{ name: string; angle: number; optimal: string; status: "good" | "warning" | "poor" }>
  }
}

interface AnalysisTimelineProps {
  frames: TimelineFrame[]
  videoUrl?: string
  duration: number
}

export function AnalysisTimeline({ frames, videoUrl, duration }: AnalysisTimelineProps) {
  const [currentFrame, setCurrentFrame] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [showPoseOverlay, setShowPoseOverlay] = useState(true)

  const currentFrameData = frames[currentFrame]

  const getStatusColor = (status: string) => {
    switch (status) {
      case "good":
        return "text-green-600 bg-green-100 dark:bg-green-900/20"
      case "warning":
        return "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20"
      case "poor":
        return "text-red-600 bg-red-100 dark:bg-red-900/20"
      default:
        return "text-gray-600 bg-gray-100 dark:bg-gray-700"
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
      {/* Video Player */}
      <div className="relative aspect-video bg-gray-900">
        {videoUrl ? (
          <video className="w-full h-full object-cover" src={videoUrl} poster="/placeholder.svg?height=400&width=600" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center text-white">
              <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Play className="w-8 h-8" />
              </div>
              <p>Video analysis visualization</p>
            </div>
          </div>
        )}

        {/* Pose Overlay Toggle */}
        <button
          onClick={() => setShowPoseOverlay(!showPoseOverlay)}
          className={`absolute top-4 right-4 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
            showPoseOverlay ? "bg-blue-600 text-white" : "bg-black/50 text-white hover:bg-black/70"
          }`}
        >
          <Eye className="w-4 h-4 mr-1 inline" />
          Pose Overlay
        </button>

        {/* Pose Skeleton Overlay */}
        {showPoseOverlay && (
          <div className="absolute inset-0 pointer-events-none">
            <svg className="w-full h-full">
              {/* Sample pose points - would be dynamic based on actual pose data */}
              <circle cx="50%" cy="20%" r="4" fill="#3B82F6" opacity="0.8" />
              <circle cx="45%" cy="35%" r="3" fill="#3B82F6" opacity="0.8" />
              <circle cx="55%" cy="35%" r="3" fill="#3B82F6" opacity="0.8" />
              <circle cx="50%" cy="50%" r="3" fill="#10B981" opacity="0.8" />
              <circle cx="40%" cy="70%" r="3" fill="#F59E0B" opacity="0.8" />
              <circle cx="60%" cy="70%" r="3" fill="#F59E0B" opacity="0.8" />

              {/* Connecting lines */}
              <line x1="50%" y1="20%" x2="50%" y2="50%" stroke="#3B82F6" strokeWidth="2" opacity="0.6" />
              <line x1="45%" y1="35%" x2="55%" y2="35%" stroke="#3B82F6" strokeWidth="2" opacity="0.6" />
              <line x1="50%" y1="50%" x2="40%" y2="70%" stroke="#10B981" strokeWidth="2" opacity="0.6" />
              <line x1="50%" y1="50%" x2="60%" y2="70%" stroke="#10B981" strokeWidth="2" opacity="0.6" />
            </svg>
          </div>
        )}

        {/* Current Frame Info Overlay */}
        <div className="absolute bottom-4 left-4 bg-black/70 text-white px-3 py-2 rounded-lg">
          <div className="text-sm">
            Frame {currentFrame + 1} • {formatTime(currentFrameData?.timestamp || 0)}
          </div>
          <div className="text-lg font-bold">Score: {currentFrameData?.score || 0}%</div>
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCurrentFrame(Math.max(0, currentFrame - 1))}
              disabled={currentFrame === 0}
              className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center disabled:opacity-50"
            >
              <SkipBack className="w-4 h-4" />
            </button>

            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center"
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
            </button>

            <button
              onClick={() => setCurrentFrame(Math.min(frames.length - 1, currentFrame + 1))}
              disabled={currentFrame === frames.length - 1}
              className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center disabled:opacity-50"
            >
              <SkipForward className="w-4 h-4" />
            </button>
          </div>

          <div className="text-sm text-gray-600 dark:text-gray-400">
            {formatTime(currentFrameData?.timestamp || 0)} / {formatTime(duration)}
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="relative">
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-600 transition-all duration-200"
              style={{ width: `${((currentFrame + 1) / frames.length) * 100}%` }}
            />
          </div>

          {/* Frame markers */}
          <div className="absolute inset-0 flex justify-between">
            {frames.map((frame, index) => (
              <button
                key={index}
                onClick={() => setCurrentFrame(index)}
                className={`w-3 h-3 rounded-full border-2 border-white transform -translate-y-0.5 transition-colors ${
                  frame.score >= 80 ? "bg-green-500" : frame.score >= 60 ? "bg-yellow-500" : "bg-red-500"
                }`}
                style={{ left: `${(index / (frames.length - 1)) * 100}%` }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Frame Analysis */}
      <div className="p-4 space-y-4">
        {/* Current Frame Feedback */}
        <div>
          <h4 className="font-medium text-gray-900 dark:text-white mb-2">Frame Analysis</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {currentFrameData?.feedback || "Select a frame to see detailed analysis"}
          </p>
        </div>

        {/* Issues */}
        {currentFrameData?.issues && currentFrameData.issues.length > 0 && (
          <div>
            <h5 className="font-medium text-gray-900 dark:text-white mb-2">Issues Detected</h5>
            <div className="flex flex-wrap gap-2">
              {currentFrameData.issues.map((issue, index) => (
                <span
                  key={index}
                  className="px-2 py-1 bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400 text-xs rounded-full"
                >
                  {issue}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Joint Analysis */}
        {currentFrameData?.poseData?.joints && (
          <div>
            <h5 className="font-medium text-gray-900 dark:text-white mb-2">Joint Analysis</h5>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {currentFrameData.poseData.joints.map((joint, index) => (
                <div key={index} className={`p-2 rounded-lg text-xs ${getStatusColor(joint.status)}`}>
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{joint.name}</span>
                    <span>{joint.angle}°</span>
                  </div>
                  <div className="text-xs opacity-75 mt-1">Optimal: {joint.optimal}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
