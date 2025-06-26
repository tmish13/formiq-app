import React, { lazy, Suspense } from 'react';
import { RouteObject } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { PageLoader } from '../components/common/PageLoader';

// Route constants
export const ROUTES = {
  // Public routes
  LOGIN: '/login',
  REGISTER: '/register',
  NOT_FOUND: '/404',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  REQUEST_EMAIL_VERIFICATION: '/request-verification',
  VERIFY_EMAIL: '/verify-email',
  
  // Protected routes
  HOME: '/',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  FORM_ANALYSIS: '/form-analysis',
  PROGRESS: '/progress',
  WORKOUT: '/workout',
  FORM_CHECK_UPLOAD: '/workout/form-check/upload',
  PROCESSING: '/processing/:videoId',
  ANALYSIS: '/analysis',
  ANALYTICS: '/analytics',
  VIDEOS: '/videos',
  EXERCISE_LIBRARY: '/exercise-library',
  
  // Admin routes
  ADMIN_USERS: '/admin/users',
  ADMIN_SETTINGS: '/admin/settings',
} as const;

// Lazy-loaded pages for better performance
const Login = lazy(() => import('../pages/auth/Login'));
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage').then(module => ({ default: module.RegisterPage })));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage').then(module => ({ default: module.DashboardPage })));
const FormAnalysis = lazy(() => import('../pages/FormAnalysis').then(module => ({ default: module.FormAnalysis })));
const Progress = lazy(() => import('../pages/Progress').then(module => ({ default: module.Progress })));
const FormCheckUploadPage = lazy(() => import('../pages/workout/FormCheckUploadPage').then(module => ({ default: module.FormCheckUploadPage })));
const AnalysisPage = lazy(() => import('../pages/analysis/AnalysisPage').then(module => ({ default: module.AnalysisPage })));
const ProfilePage = lazy(() => import('../pages/profile/ProfilePage').then(module => ({ default: module.ProfilePage })));
const WorkoutPage = lazy(() => import('../pages/workout/WorkoutPage').then(module => ({ default: module.WorkoutPage })));
const ExerciseLibraryPage = lazy(() => import('../pages/workout/ExerciseLibraryPage'));
const ProcessingProgressPage = lazy(() => import('../pages/processing/ProcessingProgressPage').then(module => ({ default: module.ProcessingProgressPage })));
const Analytics = lazy(() => import('../pages/Analytics').then(module => ({ default: module.Analytics })));
const VideosPage = lazy(() => import('../pages/Videos'));
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then(module => ({ default: module.NotFoundPage })));

// Import authentication components directly
import { ResetPasswordForm } from '../components/auth/ResetPasswordForm';
import { ConfirmPasswordResetForm } from '../components/auth/ConfirmPasswordResetForm';
import { RequestEmailVerificationForm } from '../components/auth/RequestEmailVerificationForm';
import { ConfirmEmailVerification } from '../components/auth/ConfirmEmailVerification';

// Admin pages
const UserManagement = lazy(() => import('../pages/admin/UserManagement').then(module => ({ default: module.UserManagement })));
const AdminSettings = lazy(() => import('../pages/admin/AdminSettings').then(module => ({ default: module.AdminSettings })));

// Route configuration with Suspense
const withSuspense = (Component: React.LazyExoticComponent<any>) => (
  <Suspense fallback={<PageLoader />}>
    <Component />
  </Suspense>
);

/**
 * Main public routes accessible without authentication
 */
export const publicRoutes: RouteObject[] = [
  {
    path: ROUTES.LOGIN,
    element: withSuspense(Login)
  },
  {
    path: ROUTES.REGISTER,
    element: withSuspense(RegisterPage)
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
    element: withSuspense(NotFoundPage)
  }
];

/**
 * Routes that require user authentication
 */
export const protectedRoutes: RouteObject[] = [
  {
    path: ROUTES.HOME,
    element: <ProtectedRoute><DashboardPage /></ProtectedRoute>
  },
  {
    path: ROUTES.DASHBOARD,
    element: <ProtectedRoute><DashboardPage /></ProtectedRoute>
  },
  {
    path: ROUTES.PROFILE,
    element: <ProtectedRoute><ProfilePage /></ProtectedRoute>
  },
  {
    path: ROUTES.FORM_ANALYSIS,
    element: <ProtectedRoute><FormAnalysis /></ProtectedRoute>
  },
  {
    path: ROUTES.PROGRESS,
    element: <ProtectedRoute><Progress /></ProtectedRoute>
  },
  {
    path: ROUTES.WORKOUT,
    element: <ProtectedRoute><WorkoutPage /></ProtectedRoute>
  },
  {
    path: ROUTES.FORM_CHECK_UPLOAD,
    element: <ProtectedRoute><FormCheckUploadPage /></ProtectedRoute>
  },
  {
    path: ROUTES.PROCESSING,
    element: <ProtectedRoute>{withSuspense(ProcessingProgressPage)}</ProtectedRoute>
  },
  {
    path: ROUTES.ANALYSIS,
    element: <ProtectedRoute><AnalysisPage /></ProtectedRoute>
  },
  {
    path: ROUTES.ANALYTICS,
    element: <ProtectedRoute>{withSuspense(Analytics)}</ProtectedRoute>
  },
  {
    path: ROUTES.VIDEOS,
    element: <ProtectedRoute><VideosPage /></ProtectedRoute>
  },
  {
    path: ROUTES.EXERCISE_LIBRARY,
    element: <ProtectedRoute>{withSuspense(ExerciseLibraryPage)}</ProtectedRoute>
  }
];

/**
 * Routes accessible only to users with admin role
 */
export const adminRoutes: RouteObject[] = [
  {
    path: ROUTES.ADMIN_USERS,
    element: <ProtectedRoute roles={['admin']}><UserManagement /></ProtectedRoute>
  },
  {
    path: ROUTES.ADMIN_SETTINGS,
    element: <ProtectedRoute roles={['admin']}><AdminSettings /></ProtectedRoute>
  }
];

/**
 * All application routes combined
 */
export const appRoutes: RouteObject[] = [
  ...publicRoutes,
  ...protectedRoutes,
  ...adminRoutes,
  {
    path: '*',
    element: withSuspense(NotFoundPage)
  }
]; 