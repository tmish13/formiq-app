export const env = {
  // API Configuration
  apiUrl: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  apiVersion: process.env.REACT_APP_API_VERSION || 'v1',
  
  // Feature Flags
  enableAnalytics: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  enableErrorTracking: process.env.REACT_APP_ENABLE_ERROR_TRACKING === 'true',
  
  // Authentication
  authDomain: process.env.REACT_APP_AUTH_DOMAIN || '',
  authClientId: process.env.REACT_APP_AUTH_CLIENT_ID || '',
  
  // Video Processing
  maxVideoSize: parseInt(process.env.REACT_APP_MAX_VIDEO_SIZE || '100000000', 10),
  allowedVideoTypes: (process.env.REACT_APP_ALLOWED_VIDEO_TYPES || 'mp4,webm,mov').split(','),
  
  // Cache Configuration
  cacheTTL: parseInt(process.env.REACT_APP_CACHE_TTL || '3600', 10),
  
  // Stripe Configuration
  stripePublicKey: process.env.REACT_APP_STRIPE_PUBLIC_KEY || '',
  
  // Debug Mode
  isDebugMode: process.env.REACT_APP_DEBUG_MODE === 'true',
  
  // Environment
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
  isTest: process.env.NODE_ENV === 'test',
} as const;

// Validate required environment variables
const requiredEnvVars = [
  'REACT_APP_AUTH_DOMAIN',
  'REACT_APP_AUTH_CLIENT_ID',
  'REACT_APP_STRIPE_PUBLIC_KEY',
] as const;

requiredEnvVars.forEach((envVar) => {
  if (!process.env[envVar]) {
    throw new Error(`Missing required environment variable: ${envVar}`);
  }
}); 