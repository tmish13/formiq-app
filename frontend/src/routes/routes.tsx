import React, { lazy, Suspense } from 'react';
import { RouteObject, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { PageLoader } from '../components/common/PageLoader';
import { ResetPasswordForm } from '../components/auth/ResetPasswordForm';
import { ConfirmPasswordResetForm } from '../components/auth/ConfirmPasswordResetForm';
import { RequestEmailVerificationForm } from '../components/auth/RequestEmailVerificationForm';
import { ConfirmEmailVerification } from '../components/auth/ConfirmEmailVerification';
import AuthenticatedRoot from '../components/auth/AuthenticatedRoot';

// Chunk load recovery: if a lazy chunk 404s (stale SW or CDN eviction), reload once.
// sessionStorage flag prevents an infinite reload loop if the chunk is genuinely missing.
function lazyWithRetry(factory: () => Promise<{ default: any }>) {
  return lazy(() =>
    factory().catch(() => {
      if (!sessionStorage.getItem('chunk_load_retry')) {
        sessionStorage.setItem('chunk_load_retry', '1');
        window.location.reload();
      }
      return new Promise<never>(() => {});
    })
  );
}

// Route constants
export const ROUTES = {
  // Public routes
  AUTH: '/auth',
  LOGIN: '/login',
  REGISTER: '/register',
  NOT_FOUND: '/404',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  REQUEST_EMAIL_VERIFICATION: '/request-verification',
  VERIFY_EMAIL: '/verify-email',
  ONBOARDING: '/onboarding',
  
  // Protected routes
  HOME: '/',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  FORM_ANALYSIS: '/form-analysis',
  PROGRESS: '/progress',
  EXERCISE_LIBRARY: '/exercise-library',
  LIBRARY: '/library',
  WORKOUTS: '/workouts',
  PROCESSING: '/processing/:videoId',
  FORM_CHECK_RESULTS: '/form-check/results/:videoId',
} as const;

// Modern UI pages ONLY - using shadcn/ui and Tailwind
const LandingPage = lazyWithRetry(() => import('../pages/LandingPage'));
const ModernAuthPage = lazyWithRetry(() => import('../pages/auth/ModernAuthPage'));
const GoogleCallback = lazyWithRetry(() => import('../pages/auth/GoogleCallback'));
const AppleCallback = lazyWithRetry(() => import('../pages/auth/AppleCallback'));
const DashboardPage = lazyWithRetry(() => import('../pages/DashboardPage'));
const RecordPage = lazyWithRetry(() => import('../pages/RecordPage'));
const AnalysisPage = lazyWithRetry(() => import('../pages/AnalysisPage'));
const AnalysisListPage = lazyWithRetry(() => import('../pages/AnalysisListPage'));
const ProgressPage = lazyWithRetry(() => import('../pages/ProgressPage'));
const ModernExerciseLibrary = lazyWithRetry(() => import('../pages/ModernExerciseLibrary'));
const ProfilePage = lazyWithRetry(() => import('../pages/ProfilePage'));
const OnboardingPage = lazyWithRetry(() => import('../pages/OnboardingPage'));
const ExerciseLibraryPage = lazyWithRetry(() => import('../pages/ExerciseLibraryPage'));
const WorkoutsPage = lazyWithRetry(() => import('../pages/WorkoutsPage'));
const BetaChecklistPage = lazyWithRetry(() => import('../pages/BetaChecklistPage'));

// Create modern versions of missing pages using shadcn/ui
const ModernProcessingPage = lazyWithRetry(() => import('../pages/ModernProcessingPage'));
const ModernResultsPage = lazyWithRetry(() => import('../pages/ModernResultsPage'));
const ModernNotFoundPage = lazyWithRetry(() => import('../pages/ModernNotFoundPage'));
const TermsPage = lazyWithRetry(() => import('../pages/TermsPage'));
const PrivacyPage = lazyWithRetry(() => import('../pages/PrivacyPage'));

// Route configuration with Suspense
const withSuspense = (Component: React.LazyExoticComponent<any>) => (
  <Suspense fallback={<PageLoader />}>
    <Component />
  </Suspense>
);

/**
 * Public routes accessible without authentication
 */
export const publicRoutes: RouteObject[] = [
  {
    path: ROUTES.AUTH,
    element: withSuspense(ModernAuthPage)
  },
  {
    path: ROUTES.LOGIN,
    element: <Navigate to="/auth" replace />
  },
  {
    path: ROUTES.REGISTER,
    element: <Navigate to="/auth" replace />
  },
  {
    path: ROUTES.FORGOT_PASSWORD,
    element: <ResetPasswordForm />
  },
  {
    path: ROUTES.RESET_PASSWORD,
    element: <ConfirmPasswordResetForm />
  },
  {
    path: ROUTES.REQUEST_EMAIL_VERIFICATION,
    element: <RequestEmailVerificationForm />
  },
  {
    path: ROUTES.VERIFY_EMAIL,
    element: <ConfirmEmailVerification />
  },
  {
    path: ROUTES.NOT_FOUND,
    element: withSuspense(ModernNotFoundPage)
  },
  {
    path: '/auth/google/callback',
    element: withSuspense(GoogleCallback)
  },
  {
    path: '/auth/apple/callback',
    element: withSuspense(AppleCallback)
  },
  {
    path: '/terms',
    element: withSuspense(TermsPage)
  },
  {
    path: '/privacy',
    element: withSuspense(PrivacyPage)
  }
];

/**
 * Protected routes requiring authentication - ALL using modern UI
 */
export const protectedRoutes: RouteObject[] = [
  {
    path: ROUTES.HOME,
    element: <ProtectedRoute>{withSuspense(DashboardPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.DASHBOARD,
    element: <ProtectedRoute>{withSuspense(DashboardPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.PROFILE,
    element: <ProtectedRoute>{withSuspense(ProfilePage)}</ProtectedRoute>
  },
  {
    path: ROUTES.FORM_ANALYSIS,
    element: <ProtectedRoute>{withSuspense(RecordPage)}</ProtectedRoute>
  },
  {
    path: '/record',
    element: <ProtectedRoute>{withSuspense(RecordPage)}</ProtectedRoute>
  },
  {
    path: '/analysis',
    element: <ProtectedRoute>{withSuspense(AnalysisListPage)}</ProtectedRoute>
  },
  {
    path: '/analysis/:id',
    element: <ProtectedRoute>{withSuspense(AnalysisPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.PROGRESS,
    element: <ProtectedRoute>{withSuspense(ProgressPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.EXERCISE_LIBRARY,
    element: <ProtectedRoute>{withSuspense(ModernExerciseLibrary)}</ProtectedRoute>
  },
  {
    path: ROUTES.LIBRARY,
    element: <ProtectedRoute>{withSuspense(ExerciseLibraryPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.WORKOUTS,
    element: <ProtectedRoute>{withSuspense(WorkoutsPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.PROCESSING,
    element: <ProtectedRoute>{withSuspense(ModernProcessingPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.FORM_CHECK_RESULTS,
    element: <ProtectedRoute>{withSuspense(ModernResultsPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.ONBOARDING,
    element: <ProtectedRoute>{withSuspense(OnboardingPage)}</ProtectedRoute>
  },
  {
    // Hidden beta testing guide — not shown in nav
    path: '/beta-checklist',
    element: <ProtectedRoute>{withSuspense(BetaChecklistPage)}</ProtectedRoute>
  }
];

/**
 * All application routes combined - MODERN UI ONLY
 */
export const appRoutes: RouteObject[] = [
  // Root: public landing page — handles authenticated redirect internally
  {
    path: '/',
    element: withSuspense(LandingPage)
  },
  ...publicRoutes,
  ...protectedRoutes,
  {
    path: '*',
    element: withSuspense(ModernNotFoundPage)
  }
];