"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Eye, EyeOff, Mail, Lock, User, ArrowLeft, CheckCircle } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useRouter } from "next/navigation"
import Link from "next/link"

type AuthMode = "login" | "signup" | "forgot-password" | "reset-success"

export default function AuthPage() {
  const [authMode, setAuthMode] = useState<AuthMode>("login")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [logoAnimated, setLogoAnimated] = useState(false)
  const [showToast, setShowToast] = useState(false)
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    firstName: "",
    lastName: "",
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const router = useRouter()

  useEffect(() => {
    // Trigger logo animation after component mounts
    const timer = setTimeout(() => setLogoAnimated(true), 300)
    return () => clearTimeout(timer)
  }, [])

  const handleInputChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: "" }))
    }
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}

    // Email validation
    if (!formData.email) {
      newErrors.email = "Email is required"
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Please enter a valid email"
    }

    // Password validation for login and signup
    if (authMode !== "forgot-password") {
      if (!formData.password) {
        newErrors.password = "Password is required"
      } else if (authMode === "signup" && formData.password.length < 8) {
        newErrors.password = "Password must be at least 8 characters"
      }
    }

    // Signup specific validations
    if (authMode === "signup") {
      if (!formData.firstName) {
        newErrors.firstName = "First name is required"
      }
      if (!formData.lastName) {
        newErrors.lastName = "Last name is required"
      }
      if (!formData.confirmPassword) {
        newErrors.confirmPassword = "Please confirm your password"
      } else if (formData.password !== formData.confirmPassword) {
        newErrors.confirmPassword = "Passwords don't match"
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const showSuccessToast = () => {
    setShowToast(true)
    setTimeout(() => setShowToast(false), 3000)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setIsLoading(true)

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500))

    if (authMode === "forgot-password") {
      setAuthMode("reset-success")
      showSuccessToast()
    } else {
      // Set authentication token
      localStorage.setItem("formiq-auth-token", "demo-token-" + Date.now())

      if (authMode === "signup") {
        // New user - save user data and go to onboarding
        localStorage.setItem(
          "formiq-user-data",
          JSON.stringify({
            firstName: formData.firstName,
            lastName: formData.lastName,
            email: formData.email,
            joinDate: new Date().toISOString(),
          }),
        )
        router.push("/onboarding")
      } else {
        // Existing user - check if they've completed onboarding
        const onboardingComplete = localStorage.getItem("formiq-onboarding-complete")
        if (onboardingComplete) {
          router.push("/")
        } else {
          router.push("/onboarding")
        }
      }
    }

    setIsLoading(false)
  }

  const handleSocialLogin = async (provider: string) => {
    setIsLoading(true)
    // Simulate social login
    await new Promise((resolve) => setTimeout(resolve, 1000))
    console.log(`Social login with ${provider}`)
    setIsLoading(false)
  }

  const renderSocialButtons = () => (
    <div className="space-y-4">
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-slate-300 dark:border-slate-600" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white dark:bg-slate-800 px-2 text-slate-500 dark:text-slate-400">Or continue with</span>
        </div>
      </div>

      <div className="flex gap-4">
        <motion.button
          type="button"
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => handleSocialLogin("google")}
          disabled={isLoading}
          className="flex-1 h-12 flex items-center justify-center gap-3 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 hover:bg-gray-800 dark:hover:bg-gray-800 transition-all duration-200 disabled:opacity-50"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          <span className="font-medium text-slate-700 dark:text-slate-300">Google</span>
        </motion.button>

        <motion.button
          type="button"
          whileHover={{ scale: 1.02, y: -1 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => handleSocialLogin("apple")}
          disabled={isLoading}
          className="flex-1 h-12 flex items-center justify-center gap-3 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 hover:bg-gray-800 dark:hover:bg-gray-800 transition-all duration-200 disabled:opacity-50"
        >
          <svg className="h-5 w-5 text-slate-700 dark:text-slate-300" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
          </svg>
          <span className="font-medium text-slate-700 dark:text-slate-300">Apple</span>
        </motion.button>
      </div>
    </div>
  )

  const renderLoginForm = () => (
    <motion.div
      key="login"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="text-center space-y-3">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100" style={{ lineHeight: "1.2" }}>
          Welcome back
        </h1>
        <p className="text-slate-600 dark:text-slate-400 -mt-1">Sign in to continue</p>
      </div>

      {renderSocialButtons()}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Email
          </Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              id="email"
              type="email"
              placeholder="your@email.com"
              value={formData.email}
              onChange={(e) => handleInputChange("email", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 h-12 ${
                errors.email ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
          </div>
          {errors.email && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-400 text-left"
            >
              {errors.email}
            </motion.p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Password
          </Label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              value={formData.password}
              onChange={(e) => handleInputChange("password", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 pr-10 h-12 ${
                errors.password ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
            <motion.button
              type="button"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setShowPassword(!showPassword)}
              disabled={isLoading}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </motion.button>
          </div>
          {errors.password && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-400 text-left"
            >
              {errors.password}
            </motion.p>
          )}
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              disabled={isLoading}
              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 disabled:opacity-50"
            />
            <span className="text-slate-600 dark:text-slate-400">Remember me</span>
          </label>
          <motion.button
            type="button"
            whileHover={{ scale: 1.02 }}
            onClick={() => setAuthMode("forgot-password")}
            disabled={isLoading}
            className="text-sm text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 font-medium disabled:opacity-50 hover:underline transition-all duration-200"
          >
            Forgot password?
          </motion.button>
        </div>

        <motion.button
          type="submit"
          disabled={isLoading}
          className="w-full h-14 py-5 bg-gradient-to-r from-purple-500 to-indigo-600 hover:scale-105 hover:shadow-xl text-white font-semibold text-lg rounded-lg shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Signing in...</span>
            </div>
          ) : (
            <span>Sign In</span>
          )}
        </motion.button>
      </form>

      <div className="text-center">
        <p className="text-slate-600/80 dark:text-slate-400/80">
          No account yet?{" "}
          <motion.button
            whileHover={{ scale: 1.02 }}
            onClick={() => setAuthMode("signup")}
            disabled={isLoading}
            className="text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 font-bold disabled:opacity-50 hover:underline transition-all duration-200"
          >
            Create one
          </motion.button>
        </p>
      </div>
    </motion.div>
  )

  const renderSignupForm = () => (
    <motion.div
      key="signup"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="text-center space-y-3">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100" style={{ lineHeight: "1.2" }}>
          Create your account
        </h1>
        <p className="text-slate-600 dark:text-slate-400 -mt-1">Join thousands improving their form with AI</p>
      </div>

      {renderSocialButtons()}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="firstName" className="text-sm font-medium text-slate-700 dark:text-slate-300">
              First Name
            </Label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                id="firstName"
                type="text"
                placeholder="John"
                value={formData.firstName}
                onChange={(e) => handleInputChange("firstName", e.target.value)}
                disabled={isLoading}
                className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 h-12 ${
                  errors.firstName ? "border-red-400 focus:border-red-400" : ""
                }`}
                style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
              />
            </div>
            {errors.firstName && (
              <motion.p
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm text-red-400 text-left"
              >
                {errors.firstName}
              </motion.p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="lastName" className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Last Name
            </Label>
            <Input
              id="lastName"
              type="text"
              placeholder="Doe"
              value={formData.lastName}
              onChange={(e) => handleInputChange("lastName", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 h-12 ${
                errors.lastName ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
            {errors.lastName && (
              <motion.p
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm text-red-400 text-left"
              >
                {errors.lastName}
              </motion.p>
            )}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Email
          </Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              id="email"
              type="email"
              placeholder="your@email.com"
              value={formData.email}
              onChange={(e) => handleInputChange("email", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 h-12 ${
                errors.email ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
          </div>
          {errors.email && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-400 text-left"
            >
              {errors.email}
            </motion.p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Password
          </Label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Create a strong password"
              value={formData.password}
              onChange={(e) => handleInputChange("password", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 pr-10 h-12 ${
                errors.password ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
            <motion.button
              type="button"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setShowPassword(!showPassword)}
              disabled={isLoading}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </motion.button>
          </div>
          {errors.password && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-400 text-left"
            >
              {errors.password}
            </motion.p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirmPassword" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Confirm Password
          </Label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              id="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Confirm your password"
              value={formData.confirmPassword}
              onChange={(e) => handleInputChange("confirmPassword", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 pr-10 h-12 ${
                errors.confirmPassword ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
            <motion.button
              type="button"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              disabled={isLoading}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
            >
              {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </motion.button>
          </div>
          {errors.confirmPassword && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-400 text-left"
            >
              {errors.confirmPassword}
            </motion.p>
          )}
        </div>

        <motion.button
          type="submit"
          disabled={isLoading}
          className="w-full h-14 py-5 bg-gradient-to-r from-purple-500 to-indigo-600 hover:scale-105 hover:shadow-xl text-white font-semibold text-lg rounded-lg shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Creating Account...</span>
            </div>
          ) : (
            <span>Create Account</span>
          )}
        </motion.button>
      </form>

      <div className="text-center space-y-3">
        <p className="text-xs text-slate-500/80 dark:text-slate-400/80">
          By continuing, you agree to our{" "}
          <Link href="/terms" className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline">
            Privacy Policy
          </Link>
        </p>

        <p className="text-slate-600/80 dark:text-slate-400/80">
          Already have an account?{" "}
          <motion.button
            whileHover={{ scale: 1.02 }}
            onClick={() => setAuthMode("login")}
            disabled={isLoading}
            className="text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 font-bold disabled:opacity-50 hover:underline transition-all duration-200"
          >
            Sign in
          </motion.button>
        </p>
      </div>
    </motion.div>
  )

  const renderForgotPasswordForm = () => (
    <motion.div
      key="forgot-password"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="text-center space-y-3">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100" style={{ lineHeight: "1.2" }}>
          Reset Password
        </h1>
        <p className="text-slate-600 dark:text-slate-400 -mt-1">Enter your email and we'll send you a reset link</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Email
          </Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
            <Input
              id="email"
              type="email"
              placeholder="your@email.com"
              value={formData.email}
              onChange={(e) => handleInputChange("email", e.target.value)}
              disabled={isLoading}
              className={`border border-gray-700 focus:border-purple-500 rounded-md p-3 pl-10 h-12 ${
                errors.email ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
          </div>
          {errors.email && (
            <motion.p
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-sm text-red-400 text-left"
            >
              {errors.email}
            </motion.p>
          )}
        </div>

        <motion.button
          type="submit"
          disabled={isLoading}
          className="w-full h-14 py-5 bg-gradient-to-r from-purple-500 to-indigo-600 hover:scale-105 hover:shadow-xl text-white font-semibold text-lg rounded-lg shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Sending...</span>
            </div>
          ) : (
            <span>Send Reset Link</span>
          )}
        </motion.button>
      </form>

      <div className="text-center">
        <motion.button
          whileHover={{ scale: 1.02 }}
          onClick={() => setAuthMode("login")}
          disabled={isLoading}
          className="inline-flex items-center text-slate-500/80 hover:text-slate-800 dark:text-slate-400/80 dark:hover:text-slate-200 transition-colors disabled:opacity-50 hover:underline"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to sign in
        </motion.button>
      </div>
    </motion.div>
  )

  const renderResetSuccess = () => (
    <motion.div
      key="reset-success"
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ duration: 0.3 }}
      className="text-center space-y-6"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
        className="w-16 h-16 bg-green-100 dark:bg-green-900/20 rounded-full flex items-center justify-center mx-auto"
      >
        <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
      </motion.div>

      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100" style={{ lineHeight: "1.2" }}>
          Check your email
        </h1>
        <p className="text-slate-600 dark:text-slate-400 -mt-1">
          We've emailed you a reset link at
          <br />
          <span className="font-medium">{formData.email}</span>
        </p>
      </div>

      <div className="space-y-4">
        <p className="text-sm text-slate-500/80 dark:text-slate-400/80">
          Didn't receive the email? Check your spam folder or try again.
        </p>

        <div className="space-y-3">
          <motion.button
            onClick={() => setAuthMode("forgot-password")}
            className="w-full h-12 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-semibold rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Resend Email
          </motion.button>

          <motion.button
            onClick={() => setAuthMode("login")}
            className="w-full h-14 py-5 bg-gradient-to-r from-purple-500 to-indigo-600 hover:scale-105 hover:shadow-xl text-white font-semibold text-lg rounded-lg shadow-md transition-all duration-200 flex items-center justify-center"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
          >
            <span>Back to Sign In</span>
          </motion.button>
        </div>
      </div>
    </motion.div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo with Animation */}
        <motion.div
          className="text-center mt-6 mb-2"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center space-x-4">
            <motion.div
              className="relative w-12 h-12 flex items-center justify-center"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            >
              {/* FormIQ Logo SVG */}
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#8B5CF6" />
                    <stop offset="100%" stopColor="#6366F1" />
                  </linearGradient>
                </defs>
                <circle cx="24" cy="24" r="20" fill="url(#logoGradient)" />
                <path
                  d="M16 22L20 26L32 14"
                  stroke="white"
                  strokeWidth="3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </motion.div>
            <div className="flex flex-col gap-0">
              <motion.span
                className="text-3xl font-bold text-slate-900 dark:text-slate-100"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                FormIQ
              </motion.span>
              <motion.div
                className="text-xs text-slate-500 dark:text-slate-400 font-normal -mt-1"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Powered by FormIQ AI
              </motion.div>
            </div>
          </div>
        </motion.div>

        {/* Auth Form Container with Glassmorphism */}
        <motion.div
          className="bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl rounded-2xl shadow-2xl p-6 border border-slate-200/50 dark:border-slate-700/50"
          style={{ padding: "24px" }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <AnimatePresence mode="wait">
            {authMode === "login" && renderLoginForm()}
            {authMode === "signup" && renderSignupForm()}
            {authMode === "forgot-password" && renderForgotPasswordForm()}
            {authMode === "reset-success" && renderResetSuccess()}
          </AnimatePresence>
        </motion.div>

        {/* Minimal Footer */}
        <motion.div
          className="text-center mt-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <p className="text-sm text-slate-500 dark:text-slate-400">© 2024 FormIQ. Perfect your form with AI.</p>
        </motion.div>
      </div>

      {/* Toast Notification */}
      <AnimatePresence>
        {showToast && (
          <motion.div
            initial={{ opacity: 0, y: -50, x: "-50%" }}
            animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: -50, x: "-50%" }}
            className="fixed top-4 left-1/2 transform bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50"
          >
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5" />
              <span>Reset link sent successfully!</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading Overlay */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
          >
            <div className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-xl">
              <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-slate-600 dark:text-slate-400">Processing...</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
