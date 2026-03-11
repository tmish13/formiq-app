import React, { useState, useEffect } from 'react'
import { Mail, X } from 'lucide-react'
import { useAppSelector } from '../../store/hooks'
import apiService from '../../services/apiService'

interface AuthConfig {
  beta_allow_unverified: boolean
  smtp_configured: boolean
  deadlock: boolean
}

/**
 * Amber dev-mode banner — shown ONLY when:
 *   1. Backend reports beta_allow_unverified === true  (dev/testing mode)
 *   2. The logged-in user has is_verified === false
 *   3. User hasn't dismissed this session
 *
 * External beta testers (BETA_ALLOW_UNVERIFIED=false):
 *   They must verify before logging in, so is_verified is always true when logged in.
 *   The backend flag check is an explicit additional gate — they will never see this banner.
 */
const UnverifiedBanner: React.FC = () => {
  const user = useAppSelector((state) => state.auth.user)
  const [dismissed, setDismissed] = useState(false)
  const [resendState, setResendState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [cooldown, setCooldown] = useState(0)
  // null = loading; false = production mode (hide); true = dev mode (may show)
  const [betaAllowUnverified, setBetaAllowUnverified] = useState<boolean | null>(null)

  // Fetch auth-config once to know if we're in dev beta mode
  useEffect(() => {
    let cancelled = false
    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000'
    fetch(`${apiBase}/api/v1/health/health/auth-config`)
      .then((r) => r.json())
      .then((data: AuthConfig) => {
        if (!cancelled) setBetaAllowUnverified(data.beta_allow_unverified)
      })
      .catch(() => {
        // Can't reach health endpoint — default hidden (safe for production)
        if (!cancelled) setBetaAllowUnverified(false)
      })
    return () => { cancelled = true }
  }, [])

  // Count down resend cooldown
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [cooldown])

  // Hide while loading config, in production mode, if verified, or dismissed
  if (!user || dismissed || betaAllowUnverified !== true || user.is_verified) return null

  const handleResend = async () => {
    if (cooldown > 0 || resendState === 'sending') return
    setResendState('sending')
    try {
      await apiService.requestEmailVerification(user.email)
      setResendState('sent')
      setCooldown(30)
    } catch (err) {
      console.debug('[FormIQ] banner resend failed:', err)
      setResendState('error')
      setCooldown(10)
    }
  }

  return (
    <div
      role="alert"
      className="flex items-center gap-2 px-4 py-2 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-700"
    >
      <Mail className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 flex-shrink-0" />

      <p className="flex-1 text-amber-800 dark:text-amber-300 text-xs leading-snug">
        <span className="font-semibold">Dev mode</span> — email verification not enforced.
      </p>

      <button
        type="button"
        onClick={handleResend}
        disabled={cooldown > 0 || resendState === 'sending'}
        className="text-xs font-medium text-amber-700 dark:text-amber-300 underline underline-offset-2 hover:no-underline disabled:opacity-50 flex-shrink-0 min-h-[32px] px-1"
      >
        {resendState === 'sending'
          ? 'Sending…'
          : resendState === 'sent' && cooldown > 0
          ? `Sent (${cooldown}s)`
          : resendState === 'error'
          ? 'Try again'
          : 'Resend'}
      </button>

      <button
        type="button"
        onClick={() => setDismissed(true)}
        aria-label="Dismiss"
        className="text-amber-500 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-200 flex-shrink-0 p-1 min-h-[32px] min-w-[32px] flex items-center justify-center"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export default UnverifiedBanner
