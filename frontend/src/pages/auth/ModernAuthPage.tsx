import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Eye, EyeOff, Mail, Lock, User, ArrowLeft, CheckCircle } from "lucide-react"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "../../hooks/useAuth"
import { useAppSelector } from "../../store/hooks"
import apiService from "../../services/apiService"
import SocialSignInButtons from '../../components/auth/SocialSignInButtons'

type AuthMode = "login" | "signup" | "forgot-password" | "reset-success"

export default function ModernAuthPage() {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth)
  const location = useLocation()
  // Support ?return=/workouts so auth expiry during a workout brings user back
  const returnTo = new URLSearchParams(location.search).get("return") ?? undefined
  const [authMode, setAuthMode] = useState<AuthMode>("login")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showToast, setShowToast] = useState(false)
  const [toastMessage, setToastMessage] = useState("")
  const [toastType, setToastType] = useState<"success" | "error">("success")
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    firstName: "",
    lastName: "",
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [verificationResent, setVerificationResent] = useState(false)
  const [isResendingVerification, setIsResendingVerification] = useState(false)
  // "check your inbox" screen shown after signup when verification is required
  const [verificationPending, setVerificationPending] = useState(false)
  const [pendingEmail, setPendingEmail] = useState("")
  // 30-second cooldown after each resend
  const [resendCooldown, setResendCooldown] = useState(0)
  const { login, register, requestPasswordReset, socialLogin } = useAuth()

  const handleGoogleSuccess = async (accessToken: string) => {
    try {
      setIsLoading(true)
      await socialLogin('google', accessToken)
    } catch {
      setErrors({ general: 'Google sign-in failed. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGoogleError = () => {
    setErrors({ general: 'Google sign-in failed. Please try again.' })
  }

  const handleResendVerification = async (emailOverride?: string) => {
    const target = emailOverride || formData.email
    if (!target || resendCooldown > 0) return
    setIsResendingVerification(true)
    try {
      await apiService.requestEmailVerification(target)
    } catch (err) {
      // fail silently — don't reveal whether email exists
      console.debug("[FormIQ] resend verification failed:", err)
    } finally {
      setVerificationResent(true)
      setIsResendingVerification(false)
      setResendCooldown(30) // 30-second cooldown
    }
  }

  const handleAppleSuccess = async (idToken: string) => {
    try {
      setIsLoading(true)
      await socialLogin('apple', idToken)
    } catch {
      setErrors({ general: 'Apple sign-in failed. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleAppleError = () => {
    setErrors({ general: 'Apple sign-in failed. Please try again.' })
  }

  // Count down resend cooldown
  useEffect(() => {
    if (resendCooldown <= 0) return
    const t = setTimeout(() => setResendCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [resendCooldown])

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
      } else if (authMode === "signup") {
        if (formData.password.length < 8) {
          newErrors.password = "Password must be at least 8 characters"
        } else if (!/\d/.test(formData.password)) {
          newErrors.password = "Password must contain at least one number"
        } else if (!/[!@#$%^&*()\-_=+[\]{}|;:'",.<>/?`~]/.test(formData.password)) {
          newErrors.password = "Password must contain at least one special character (e.g. !@#$%)"
        }
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

  const showToastMessage = (message: string, type: "success" | "error" = "success") => {
    setToastMessage(message)
    setToastType(type)
    setShowToast(true)
    setTimeout(() => setShowToast(false), 4000)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) return

    setIsLoading(true)
    setErrors({}) // Clear previous errors

    try {
      if (authMode === "forgot-password") {
        await requestPasswordReset(formData.email)
        setAuthMode("reset-success")
        showToastMessage("Reset link sent successfully!", "success")
      } else if (authMode === "signup") {
        console.log("🔄 Creating account for:", formData.email);
        // Derive username from name fields; fall back to email prefix if blank
        const rawUsername = `${formData.firstName}${formData.lastName}`.toLowerCase().replace(/[^a-z0-9_-]/g, '').trim();
        const usernameFromEmail = formData.email.split('@')[0].replace(/[^a-z0-9_]/g, '_');
        const registrationData = {
          confirm_password: formData.confirmPassword,
          full_name: `${formData.firstName} ${formData.lastName}`.trim() || formData.email.split('@')[0],
          username: rawUsername.length >= 3 ? rawUsername : usernameFromEmail,
        };
        console.log("📝 Registration data:", registrationData);

        // --- Step 1: Register (separate catch so login errors don't get misread) ---
        try {
          await register(formData.email, formData.password, registrationData);
          console.log("✅ Account creation successful!");
        } catch (regError: any) {
          const regMsg: string = regError.message || "Registration failed. Please try again."
          if (regMsg.toLowerCase().includes("exists") || regMsg.toLowerCase().includes("already")) {
            setErrors({ general: "An account with this email already exists. Please sign in instead." })
          } else {
            setErrors({ general: regMsg })
          }
          return // outer finally still runs setIsLoading(false)
        }

        // --- Step 2: Try auto-login; if blocked by email verification, show inbox screen ---
        try {
          await login(formData.email, formData.password)
          // Navigation handled by useAuth
        } catch (autoLoginErr: any) {
          const autoLoginMsg: string = autoLoginErr?.message || ''
          const needsVerify =
            autoLoginMsg.toLowerCase().includes("verify your email") ||
            autoLoginErr?.response?.status === 403
          if (needsVerify) {
            // Backend sent the verification email automatically on registration.
            // Show a dedicated "check your inbox" screen.
            setPendingEmail(formData.email)
            setVerificationPending(true)
            setVerificationResent(false)
            setResendCooldown(30)
          } else {
            showToastMessage("Account created! Please sign in to continue.", "success")
            setAuthMode("login")
          }
        }
        return

      } else {
        console.log("🔄 Logging in user:", formData.email);
        await login(formData.email, formData.password);
        console.log("✅ Login successful!");
        // Navigation is handled by useAuth hook
      }
    } catch (error: any) {
      console.error("Authentication error:", error)
      
      // Extract specific error message
      let errorMessage = "Authentication failed. Please try again."
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message
      } else if (error.message) {
        errorMessage = error.message
      }
      
      // Map known login error patterns to user-friendly messages
      if (authMode === "login") {
        if (
          errorMessage.includes("EMAIL_NOT_VERIFIED") ||
          errorMessage.toLowerCase().includes("verify your email")
        ) {
          setPendingEmail(formData.email)
          setVerificationPending(true)
          setVerificationResent(false)
          setResendCooldown(30)
          return // finally still runs setIsLoading(false); no error shown
        } else if (errorMessage.toLowerCase().includes("invalid") ||
            errorMessage.toLowerCase().includes("incorrect") ||
            errorMessage.toLowerCase().includes("wrong") ||
            errorMessage.toLowerCase().includes("validation failed")) {
          errorMessage = "Invalid email or password. Please check your credentials and try again."
        }
      }
      // Signup errors are handled in the inner try-catch above; this outer catch
      // only fires for the forgot-password branch or unexpected throws.

      setErrors({ general: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  const renderSocialButtons = () => (
    <SocialSignInButtons
      onGoogleSuccess={handleGoogleSuccess}
      onGoogleError={handleGoogleError}
      onAppleSuccess={handleAppleSuccess}
      onAppleError={handleAppleError}
      isLoading={isLoading}
    />
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
              className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 h-12 ${
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
              className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 pr-10 h-12 ${
                errors.password ? "border-red-400 focus:border-red-400" : ""
              }`}
              style={{ maxWidth: "100%", textOverflow: "ellipsis" }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              disabled={isLoading}
              className="absolute inset-y-0 right-3 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
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

        {/* General Error Display */}
        {errors.general && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3"
          >
            <p className="text-sm text-red-600 dark:text-red-400">{errors.general}</p>
          </motion.div>
        )}

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
          className="w-full h-[52px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-base rounded-xl shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Signing in...</span>
            </div>
          ) : (
            <span>Sign In</span>
          )}
        </motion.button>
      </form>

      {renderSocialButtons()}

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
                placeholder="First name"
                value={formData.firstName}
                onChange={(e) => handleInputChange("firstName", e.target.value)}
                disabled={isLoading}
                className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 h-12 ${
                  errors.firstName ? "border-red-400 focus:border-red-400" : ""
                }`}
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
            <div className="relative">
              <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                id="lastName"
                type="text"
                placeholder="Last name"
                value={formData.lastName}
                onChange={(e) => handleInputChange("lastName", e.target.value)}
                disabled={isLoading}
                className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 h-12 ${
                  errors.lastName ? "border-red-400 focus:border-red-400" : ""
                }`}
              />
            </div>
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
              className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 h-12 ${
                errors.email ? "border-red-400 focus:border-red-400" : ""
              }`}
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
              maxLength={100}
              className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 pr-10 h-12 ${
                errors.password ? "border-red-400 focus:border-red-400" : ""
              }`}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              disabled={isLoading}
              className="absolute inset-y-0 right-3 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
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
              maxLength={100}
              className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 pr-10 h-12 ${
                errors.confirmPassword ? "border-red-400 focus:border-red-400" : ""
              }`}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              disabled={isLoading}
              className="absolute inset-y-0 right-3 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors disabled:opacity-50"
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
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

        {/* General Error Display for Signup */}
        {errors.general && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3"
          >
            <p className="text-sm text-red-600 dark:text-red-400">{errors.general}</p>
          </motion.div>
        )}

        <motion.button
          type="submit"
          disabled={isLoading}
          className="w-full h-[52px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-base rounded-xl shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Creating account...</span>
            </div>
          ) : (
            <span>Create Account</span>
          )}
        </motion.button>
      </form>

      {renderSocialButtons()}

      <div className="text-center space-y-3">
        <p className="text-xs text-slate-500/80 dark:text-slate-400/80">
          By continuing, you agree to our{" "}
          <a href="/terms" className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline">
            Terms of Service
          </a>{" "}
          and{" "}
          <a href="/privacy" className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 underline">
            Privacy Policy
          </a>
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
          Reset your password
        </h1>
        <p className="text-slate-600 dark:text-slate-400 -mt-1">
          Enter your email and we'll send you a reset link
        </p>
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
              className={`border border-slate-300 dark:border-slate-600 focus:border-indigo-500 dark:focus:border-indigo-400 rounded-md p-3 pl-10 h-12 ${
                errors.email ? "border-red-400 focus:border-red-400" : ""
              }`}
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
          className="w-full h-[52px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-base rounded-xl shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Sending reset link...</span>
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
          className="inline-flex items-center space-x-2 text-slate-500 hover:text-indigo-600 dark:text-slate-400 dark:hover:text-indigo-400 font-medium disabled:opacity-50 hover:underline transition-all duration-200"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to sign in</span>
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
            className="w-full h-[52px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-base rounded-xl shadow-md transition-all duration-200 flex items-center justify-center"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
          >
            Back to Sign In
          </motion.button>
        </div>
      </div>
    </motion.div>
  )

  const renderVerificationPending = () => (
    <motion.div
      key="verification-pending"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: 0.3 }}
      className="text-center space-y-6"
    >
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
        className="w-16 h-16 bg-indigo-100 dark:bg-indigo-900/30 rounded-full flex items-center justify-center mx-auto"
      >
        <Mail className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
      </motion.div>

      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Check your inbox
        </h1>
        <p className="text-slate-600 dark:text-slate-400">
          We've sent a verification link to
          <br />
          <span className="font-semibold text-slate-800 dark:text-slate-200">{pendingEmail}</span>
        </p>
        <p className="text-sm text-slate-500 dark:text-slate-400 pt-1">
          It might take a minute to arrive. Check your spam folder if you don't see it.
        </p>
      </div>

      <div className="space-y-3">
        {verificationResent ? (
          <p className="text-sm text-green-600 dark:text-green-400 font-medium">
            Verification email sent again.
            {resendCooldown > 0 && (
              <span className="text-slate-400 font-normal"> (Resend in {resendCooldown}s)</span>
            )}
          </p>
        ) : null}

        <motion.button
          type="button"
          onClick={() => handleResendVerification(pendingEmail)}
          disabled={isResendingVerification || resendCooldown > 0}
          className="w-full h-12 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-medium rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.98 }}
        >
          {isResendingVerification
            ? 'Sending…'
            : resendCooldown > 0
            ? `Resend in ${resendCooldown}s`
            : 'Resend verification email'}
        </motion.button>

        <motion.button
          type="button"
          onClick={() => { setVerificationPending(false); setAuthMode("login") }}
          className="w-full h-12 text-slate-500 dark:text-slate-400 text-sm hover:underline"
        >
          Back to Sign In
        </motion.button>
      </div>
    </motion.div>
  )

  // Already logged-in users are redirected immediately after all hooks have been called.
  // If there's a ?return= param (e.g. set by apiService on auth expiry), use it.
  if (isAuthenticated && user) {
    const dest = returnTo
      ? decodeURIComponent(returnTo)
      : (user.has_completed_onboarding ? "/dashboard" : "/onboarding")
    return <Navigate to={dest} replace />
  }

  // Verification pending — show dedicated inbox screen (bypasses the card's AnimatePresence)
  if (verificationPending) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <motion.div
            className="bg-card rounded-2xl shadow-lg p-6 border border-border"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            {renderVerificationPending()}
          </motion.div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
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
            </div>
          </div>
        </motion.div>

        {/* Auth Form Container */}
        <motion.div
          className="bg-card rounded-2xl shadow-lg p-6 border border-border"
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
          <p className="text-sm text-slate-500 dark:text-slate-400">© {new Date().getFullYear()} FormIQ. Perfect your form with AI.</p>
        </motion.div>
      </div>

      {/* Toast Notification */}
      <AnimatePresence>
        {showToast && (
          <motion.div
            initial={{ opacity: 0, y: -50, x: "-50%" }}
            animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: -50, x: "-50%" }}
            className={`fixed top-4 left-1/2 transform text-white px-6 py-3 rounded-lg shadow-lg z-50 max-w-md text-center ${
              toastType === "success" ? "bg-green-500" : "bg-red-500"
            }`}
          >
            <div className="flex items-center space-x-2">
              {toastType === "success" ? (
                <CheckCircle className="w-5 h-5 flex-shrink-0" />
              ) : (
                <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              )}
              <span className="text-sm font-medium">{toastMessage}</span>
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