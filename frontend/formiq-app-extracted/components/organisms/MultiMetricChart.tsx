"use client"

import { motion } from "framer-motion"
import { TrendingUp, TrendingDown } from "lucide-react"

interface Metric {
  name: string
  data: number[]
  color: string
}

interface MultiMetricChartProps {
  metrics: Metric[]
  labels: string[]
  title?: string
}

export function MultiMetricChart({ metrics, labels, title }: MultiMetricChartProps) {
  const maxValue = Math.max(...metrics.flatMap((m) => m.data))

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg"
    >
      {title && <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">{title}</h3>}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 mb-6">
        {metrics.map((metric, index) => (
          <div key={index} className="flex items-center space-x-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: metric.color }} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{metric.name}</span>
            <div className="flex items-center space-x-1">
              {metric.data[metric.data.length - 1] > metric.data[0] ? (
                <TrendingUp className="w-3 h-3 text-green-500" />
              ) : (
                <TrendingDown className="w-3 h-3 text-red-500" />
              )}
              <span className="text-xs text-gray-500">{metric.data[metric.data.length - 1]}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="relative h-64 overflow-hidden">
        <svg className="w-full h-full" viewBox="0 0 400 200">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((value) => (
            <g key={value}>
              <line
                x1="0"
                y1={200 - (value / 100) * 200}
                x2="400"
                y2={200 - (value / 100) * 200}
                stroke="currentColor"
                strokeOpacity="0.1"
                className="text-gray-400"
              />
              <text x="5" y={200 - (value / 100) * 200 - 5} className="text-xs fill-gray-500">
                {value}%
              </text>
            </g>
          ))}

          {/* Data lines */}
          {metrics.map((metric, metricIndex) => {
            const points = metric.data.map((value, index) => ({
              x: (index / (metric.data.length - 1)) * 380 + 20,
              y: 200 - (value / 100) * 180,
            }))

            const pathData = points.reduce((path, point, index) => {
              return path + (index === 0 ? `M ${point.x} ${point.y}` : ` L ${point.x} ${point.y}`)
            }, "")

            return (
              <g key={metricIndex}>
                <motion.path
                  d={pathData}
                  fill="none"
                  stroke={metric.color}
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 1, delay: metricIndex * 0.2 }}
                />

                {/* Data points */}
                {points.map((point, pointIndex) => (
                  <motion.circle
                    key={pointIndex}
                    cx={point.x}
                    cy={point.y}
                    r="4"
                    fill={metric.color}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 1 + pointIndex * 0.1 }}
                  />
                ))}
              </g>
            )
          })}
        </svg>

        {/* X-axis labels */}
        <div className="absolute bottom-0 left-0 right-0 flex justify-between px-5 text-xs text-gray-500">
          {labels.map((label, index) => (
            <span key={index}>{label}</span>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
