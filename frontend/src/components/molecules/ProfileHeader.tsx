"use client"

import { motion } from "framer-motion"
import { Edit, Crown } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/atoms/Badge"
import { CTAButton } from "@/components/atoms/CTAButton"

interface ProfileHeaderProps {
  avatar: string
  name: string
  email: string
  membership: "Basic" | "Pro" | "Premium"
  joinDate: string
}

export function ProfileHeader({ avatar, name, email, membership, joinDate }: ProfileHeaderProps) {
  const membershipColors = {
    Basic: "default",
    Pro: "purple",
    Premium: "warning",
  } as const

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg"
    >
      <div className="flex flex-col sm:flex-row items-center space-y-4 sm:space-y-0 sm:space-x-4">
        {/* Avatar */}
        <motion.div whileHover={{ scale: 1.05 }} className="relative">
          <Avatar className="w-20 h-20 ring-4 ring-blue-100 dark:ring-blue-900/30">
            <AvatarImage src={avatar || "/placeholder.svg"} alt={name} />
            <AvatarFallback className="bg-blue-100 text-blue-600 text-2xl font-bold">
              {name
                .split(" ")
                .map((n) => n[0])
                .join("")}
            </AvatarFallback>
          </Avatar>

          {membership !== "Basic" && (
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 2, repeat: Number.POSITIVE_INFINITY }}
              className="absolute -top-1 -right-1 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center"
            >
              <Crown className="w-3 h-3 text-white" />
            </motion.div>
          )}
        </motion.div>

        {/* Info */}
        <div className="flex-1 text-center sm:text-left">
          <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2 mb-1">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{name}</h2>
            <Badge
              label={membership}
              icon={membership !== "Basic" ? <Crown className="w-3 h-3" /> : undefined}
              variant={membershipColors[membership]}
            />
          </div>
          <p className="text-gray-600 dark:text-gray-400">{email}</p>
          <p className="text-sm text-gray-500 dark:text-gray-500">Member since {joinDate}</p>
        </div>

        {/* Edit Button */}
        <CTAButton label="Edit" icon={<Edit className="w-4 h-4" />} onClick={() => {}} variant="outline" size="sm" />
      </div>
    </motion.div>
  )
}
