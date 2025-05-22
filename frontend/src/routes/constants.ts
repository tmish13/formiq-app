export const ROUTES = {
  // Auth routes
  LOGIN: '/login',
  REGISTER: '/register',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',

  // Main app routes
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  WORKOUT: '/workout',
  FORM_ANALYSIS: '/form-analysis',
  PROGRESS: '/progress',
  VIDEOS: '/videos',
  SETTINGS: '/settings',

  // Form analysis routes
  FORM_ANALYSIS_HISTORY: '/form-analysis/history',
  FORM_ANALYSIS_DETAILS: '/form-analysis/:id',

  // Workout routes
  WORKOUT_HISTORY: '/workout/history',
  WORKOUT_DETAILS: '/workout/:id',
  WORKOUT_CREATE: '/workout/create',

  // Progress routes
  PROGRESS_METRICS: '/progress/metrics',
  PROGRESS_GOALS: '/progress/goals',
  PROGRESS_REPORTS: '/progress/reports',

  // Settings routes
  SETTINGS_PROFILE: '/settings/profile',
  SETTINGS_PREFERENCES: '/settings/preferences',
  SETTINGS_NOTIFICATIONS: '/settings/notifications',
  SETTINGS_SECURITY: '/settings/security',
} as const;

// Type for route paths
export type RoutePath = typeof ROUTES[keyof typeof ROUTES];

// Helper function to generate route with parameters
export const generatePath = (route: RoutePath, params: Record<string, string> = {}): string => {
  let path = route;
  Object.entries(params).forEach(([key, value]) => {
    path = path.replace(`:${key}`, value);
  });
  return path;
}; 