import React from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { useToast } from '../../hooks/use-toast'

// ─── SVG icon primitives ──────────────────────────────────────────────────────

const GoogleSvg: React.FC = () => (
  <svg className="h-4 w-4 flex-shrink-0" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
)

const AppleSvg: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg
    className={`h-4 w-4 flex-shrink-0 ${className}`}
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
  </svg>
)

// ─── Real Google button ───────────────────────────────────────────────────────
// Only rendered when REACT_APP_GOOGLE_CLIENT_ID is set.
// Requires a GoogleOAuthProvider ancestor with the same clientId.

interface GoogleRealButtonProps {
  onSuccess: (accessToken: string) => void
  onError: () => void
  disabled?: boolean
}

const GoogleRealButton: React.FC<GoogleRealButtonProps> = ({ onSuccess, onError, disabled }) => {
  const googleLogin = useGoogleLogin({
    flow: 'implicit',
    onSuccess: (tokenResponse) => onSuccess(tokenResponse.access_token),
    onError,
  })

  return (
    <button
      type="button"
      onClick={() => googleLogin()}
      disabled={disabled}
      className="flex-1 h-12 flex items-center justify-center gap-2 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <GoogleSvg />
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Continue with Google</span>
    </button>
  )
}

// ─── Real Apple button ────────────────────────────────────────────────────────
// Only rendered when REACT_APP_APPLE_CLIENT_ID is set.
// Lazy-loads the Apple JS SDK and uses the popup flow.

const APPLE_SDK_URL =
  'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js'

interface AppleRealButtonProps {
  onSuccess: (idToken: string) => void
  onError: () => void
  disabled?: boolean
}

const AppleRealButton: React.FC<AppleRealButtonProps> = ({ onSuccess, onError, disabled }) => {
  const handleClick = async () => {
    try {
      if (!document.getElementById('apple-jssdk')) {
        await new Promise<void>((resolve, reject) => {
          const script = document.createElement('script')
          script.id = 'apple-jssdk'
          script.src = APPLE_SDK_URL
          script.onload = () => resolve()
          script.onerror = () => reject(new Error('Failed to load Apple Sign-In script'))
          document.head.appendChild(script)
        })
      }
      const AppleID = (window as any).AppleID
      if (!AppleID) throw new Error('Apple Sign-In SDK not available')
      AppleID.auth.init({
        clientId: process.env.REACT_APP_APPLE_CLIENT_ID!,
        scope: 'name email',
        redirectURI: window.location.origin,
        usePopup: true,
      })
      const response = await AppleID.auth.signIn()
      const idToken = response?.authorization?.id_token
      if (!idToken) throw new Error('No identity token in Apple response')
      onSuccess(idToken)
    } catch (error: any) {
      if (error?.error !== 'popup_closed_by_user') {
        console.error('Apple Sign-In error:', error)
        onError()
      }
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled}
      className="flex-1 h-12 flex items-center justify-center gap-2 rounded-xl bg-black hover:bg-neutral-900 transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <AppleSvg className="text-white" />
      <span className="text-sm font-medium text-white">Continue with Apple</span>
    </button>
  )
}

// ─── SocialSignInButtons — exported component ─────────────────────────────────
// Always renders both buttons. Shows "Soon" stub pills when client IDs are
// not yet configured so beta users know the option is coming.

export interface SocialSignInButtonsProps {
  onGoogleSuccess: (accessToken: string) => void
  onGoogleError: () => void
  onAppleSuccess: (idToken: string) => void
  onAppleError: () => void
  isLoading?: boolean
}

const SocialSignInButtons: React.FC<SocialSignInButtonsProps> = ({
  onGoogleSuccess,
  onGoogleError,
  onAppleSuccess,
  onAppleError,
  isLoading,
}) => {
  const { toast } = useToast()
  const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || ''
  const appleClientId = process.env.REACT_APP_APPLE_CLIENT_ID || ''

  return (
    <div className="space-y-4">
      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t border-slate-200 dark:border-slate-700" />
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="bg-card px-2 text-slate-400 dark:text-slate-500">Or continue with</span>
        </div>
      </div>

      {/* Social buttons */}
      <div className="flex gap-3">
        {/* Google */}
        {googleClientId ? (
          <GoogleRealButton
            onSuccess={onGoogleSuccess}
            onError={onGoogleError}
            disabled={isLoading}
          />
        ) : (
          <button
            type="button"
            onClick={() =>
              toast({ title: 'Google sign-in is coming soon.', duration: 3000 })
            }
            disabled={isLoading}
            className="relative flex-1 h-12 flex items-center justify-center gap-2 border border-slate-200 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <GoogleSvg />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Google</span>
            <span className="absolute top-1 right-1.5 text-[9px] font-semibold text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-700 rounded px-1 py-0.5 leading-none">
              Soon
            </span>
          </button>
        )}

        {/* Apple */}
        {appleClientId ? (
          <AppleRealButton
            onSuccess={onAppleSuccess}
            onError={onAppleError}
            disabled={isLoading}
          />
        ) : (
          <button
            type="button"
            onClick={() =>
              toast({ title: 'Apple sign-in is coming soon.', duration: 3000 })
            }
            disabled={isLoading}
            className="relative flex-1 h-12 flex items-center justify-center gap-2 rounded-xl bg-black hover:bg-neutral-900 transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <AppleSvg className="text-white" />
            <span className="text-sm font-medium text-white">Apple</span>
            <span className="absolute top-1 right-1.5 text-[9px] font-semibold text-white/50 bg-white/10 rounded px-1 py-0.5 leading-none">
              Soon
            </span>
          </button>
        )}
      </div>
    </div>
  )
}

export default SocialSignInButtons
