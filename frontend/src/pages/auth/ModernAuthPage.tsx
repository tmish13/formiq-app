import React, { useState, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Eye, EyeOff, Mail, Lock, User, ArrowLeft, CheckCircle } from "lucide-react"
import { Input } from "../../components/ui/input"
import { Label } from "../../components/ui/label"
import { Navigate, useNavigate } from "react-router-dom"
import { useAuth } from "../../hooks/useAuth"
import { useAppSelector } from "../../store/hooks"
import { useGoogleLogin } from "@react-oauth/google"
import apiService from "../../services/apiService"
import SocialSignInButtons from '../../components/auth/SocialSignInButtons'

type AuthMode = "login" | "signup" | "forgot-password" | "reset-success"

// ---------------------------------------------------------------------------
// GoogleLoginButton — only rendered inside GoogleOAuthProvider (clientId set)
// ---------------------------------------------------------------------------
interface GoogleLoginButtonProps {
  onSuccess: (accessToken: string) => void
  onError: () => void
  disabled?: boolean
}

const GoogleLoginButton: React.FC<GoogleLoginButtonProps> = ({ onSuccess, onError, disabled }) => {
  const googleLogin = useGoogleLogin({
    flow: 'implicit',
    onSuccess: (tokenResponse) => onSuccess(tokenResponse.access_token),
    onError,
  })

  return (
    <motion.button
      type="button"
      whileHover={{ scale: 1.02, y: -1 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => googleLogin()}
      disabled={disabled}
      className="flex-1 h-12 flex items-center justify-center gap-3 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all duration-200 disabled:opacity-50"
    >
      <svg className="h-5 w-5" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
      </svg>
      <span className="font-medium text-slate-700 dark:text-slate-300">Google</span>
    </motion.button>
  )
}

// ---------------------------------------------------------------------------
// AppleLoginButton — loads Apple JS SDK lazily, uses popup flow.
// Only rendered when REACT_APP_APPLE_CLIENT_ID is present.
// Note: Apple Sign-In web requires HTTPS and a registered redirect URI.
// ---------------------------------------------------------------------------
interface AppleLoginButtonProps {
  onSuccess: (idToken: string) => void
  onError: () => void
  disabled?: boolean
}

const APPLE_SDK_URL =
  "https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js"

const AppleLoginButton: React.FC<AppleLoginButtonProps> = ({ onSuccess, onError, disabled }) => {
  const handleClick = async () => {
    try {
      // Load the Apple JS SDK script if it hasn't been loaded yet
      if (!document.getElementById("apple-jssdk")) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement("script")
          script.id = "apple-jssdk"
          script.src = APPLE_SDK_URL
          script.onload = () => resolve()
          script.onerror = () => reject(new Error("Failed to load Apple Sign-In script"))
          document.head.appendChild(script)
        })
      }

      const AppleID = (window as any).AppleID
      if (!AppleID) {
        throw new Error("Apple Sign-In SDK not available")
      }

      AppleID.auth.init({
        clientId: process.env.REACT_APP_APPLE_CLIENT_ID!,
        scope: "name email",
        // redirectURI must be registered in your Apple developer portal.
        // For popup mode Apple uses this as a validation hint, not a real redirect.
        redirectURI: window.location.origin,
        usePopup: true,
      })

      const response = await AppleID.auth.signIn()
      const idToken = response?.authorization?.id_token
      if (!idToken) {
        throw new Error("No identity token in Apple response")
      }
      onSuccess(idToken)
    } catch (error: any) {
      // popup_closed_by_user is not an error — user simply cancelled
      if (error?.error !== "popup_closed_by_user") {
        console.error("Apple Sign-In error:", error)
        onError()
      }
    }
  }

  return (
    <motion.button
      type="button"
      whileHover={{ scale: 1.02, y: -1 }}
      whileTap={{ scale: 0.98 }}
      onClick={handleClick}
      disabled={disabled}
      className="flex-1 h-12 flex items-center justify-center gap-3 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all duration-200 disabled:opacity-50"
    >
      <svg className="h-5 w-5 text-slate-700 dark:text-slate-300" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
      </svg>
      <span className="font-medium text-slate-700 dark:text-slate-300">Apple</span>
    </motion.button>
  )
}

export default function ModernAuthPage() {
  const { isAuthenticated, user } = useAppSelector((state) => state.auth)
  const [authMode, setAuthMode] = useState<AuthMode>("login")
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [logoAnimated, setLogoAnimated] = useState(false)
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
  const navigate = useNavigate()
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

  useEffect(() => {
    // Trigger logo animation after component mounts
    const timer = setTimeout(() => setLogoAnimated(true), 300)
    return () => clearTimeout(timer)
  }, [])

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
        const rawUsername = `${formData.firstName}${formData.lastName}`.toLowerCase().trim();
        const usernameFromEmail = formData.email.split('@')[0].replace(/[^a-z0-9_]/g, '_');
        const registrationData = {
          confirm_password: formData.confirmPassword,
          full_name: `${formData.firstName} ${formData.lastName}`.trim() || formData.email.split('@')[0],
          username: rawUsername.length >= 3 ? rawUsername : usernameFromEmail,
          first_name: formData.firstName,
          last_name: formData.lastName
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

  const handleSocialLogin = async (provider: 'google' | 'apple') => {
    setIsLoading(true)
    try {
      console.log(`🔐 Starting ${provider} authentication...`);
      
      // Check if we're in a mobile environment
      const { Capacitor } = await import('@capacitor/core');
      const isNativeMobile = Capacitor.isNativePlatform();
      
      if (provider === 'google') {
        if (isNativeMobile) {
          // Mobile Google OAuth using web redirect flow
          const { Browser } = await import('@capacitor/browser');
          const { App } = await import('@capacitor/app');
          
          // Use existing backend redirect endpoint
          const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
          const oauthUrl = `${apiBaseUrl}/auth/social/google/redirect?redirect_uri=${encodeURIComponent('formiq://auth/callback')}`;
          
          console.log('🌐 Opening Google OAuth URL:', oauthUrl);
          
          // Open OAuth in in-app browser
          await Browser.open({
            url: oauthUrl,
            windowName: 'oauth',
          });
          
          // Listen for the app to be reopened (OAuth callback)
          const listener = await App.addListener('appUrlOpen', async (data) => {
            console.log('📱 App URL opened:', data.url);
            
            if (data.url.includes('formiq://auth/callback')) {
              try {
                // Extract OAuth token or code from the URL
                const url = new URL(data.url);
                const token = url.searchParams.get('token');
                const code = url.searchParams.get('code');
                const error = url.searchParams.get('error');
                
                if (error) {
                  throw new Error(`OAuth error: ${error}`);
                }
                
                if (token) {
                  // Direct token - use socialLogin
                  await socialLogin('google', token);
                  showToastMessage("Successfully signed in with Google!", "success");
                } else if (code) {
                  // OAuth code - exchange for token using existing endpoint
                  const response = await fetch(`${apiBaseUrl}/api/v1/auth/social/google`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code })
                  });
                  
                  if (response.ok) {
                    const data = await response.json();
                    await socialLogin('google', data.access_token);
                    showToastMessage("Successfully signed in with Google!", "success");
                  } else {
                    throw new Error('Failed to exchange OAuth code');
                  }
                }
                
                // Close the browser and remove listener
                await Browser.close();
                listener.remove();
                setIsLoading(false);
              } catch (err) {
                console.error('OAuth callback error:', err);
                setErrors({ general: 'Google authentication failed. Please try again.' });
                setIsLoading(false);
              }
            }
          });
        } else {
          // Web Google OAuth - redirect to backend endpoint
          const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
          window.location.href = `${apiBaseUrl}/auth/social/google/redirect?redirect_uri=${encodeURIComponent(window.location.origin + '/auth/google/callback')}`;
        }
        
      } else if (provider === 'apple') {
        if (isNativeMobile) {
          // Try native Apple Sign In first
          try {
            const { SignInWithApple } = await import('@capacitor-community/apple-sign-in');
            
            const result = await SignInWithApple.authorize({
              clientId: 'com.formiq.app',
              redirectURI: 'formiq://auth/callback',
              scopes: 'email name',
              state: 'state',
              nonce: 'nonce'
            });
            
            if (result.response && result.response.identityToken) {
              await socialLogin('apple', result.response.identityToken);
              showToastMessage("Successfully signed in with Apple!", "success");
              setIsLoading(false);
            }
          } catch (appleError) {
            console.error('Native Apple Sign In failed, falling back to web flow');
            
            // Fallback to web-based Apple OAuth
            const { Browser } = await import('@capacitor/browser');
            const { App } = await import('@capacitor/app');
            
            const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
            const oauthUrl = `${apiBaseUrl}/auth/social/apple/redirect?redirect_uri=${encodeURIComponent('formiq://auth/callback')}`;
            
            await Browser.open({
              url: oauthUrl,
              windowName: 'oauth',
            });
            
            const listener = await App.addListener('appUrlOpen', async (data) => {
              if (data.url.includes('formiq://auth/callback')) {
                try {
                  const url = new URL(data.url);
                  const token = url.searchParams.get('token');
                  const code = url.searchParams.get('code');
                  
                  if (token) {
                    await socialLogin('apple', token);
                  } else if (code) {
                    const response = await fetch(`${apiBaseUrl}/api/v1/auth/social/apple`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ code })
                    });
                    
                    if (response.ok) {
                      const data = await response.json();
                      await socialLogin('apple', data.access_token);
                    }
                  }
                  
                  showToastMessage("Successfully signed in with Apple!", "success");
                  await Browser.close();
                  listener.remove();
                  setIsLoading(false);
                } catch (err) {
                  console.error('Apple OAuth callback error:', err);
                  setErrors({ general: 'Apple authentication failed. Please try again.' });
                  setIsLoading(false);
                }
              }
            });
          }
        } else {
          // Web Apple OAuth - redirect to backend endpoint
          const apiBaseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
          window.location.href = `${apiBaseUrl}/auth/social/apple/redirect?redirect_uri=${encodeURIComponent(window.location.origin + '/auth/apple/callback')}`;
        }
      }
    } catch (error) {
      console.error(`${provider} login failed:`, error)
      setErrors({ general: `${provider} authentication failed. Please try again.` })
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

  // Already logged-in users are redirected immediately after all hooks have been called
  if (isAuthenticated && user) {
    return <Navigate to={user.has_completed_onboarding ? "/dashboard" : "/onboarding"} replace />
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