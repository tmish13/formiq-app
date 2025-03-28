declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production' | 'test';
    
    // API Configuration
    REACT_APP_API_URL: string;
    REACT_APP_API_VERSION: string;
    
    // Feature Flags
    REACT_APP_ENABLE_ANALYTICS: string;
    REACT_APP_ENABLE_ERROR_TRACKING: string;
    
    // Authentication
    REACT_APP_AUTH_DOMAIN: string;
    REACT_APP_AUTH_CLIENT_ID: string;
    
    // Video Processing
    REACT_APP_MAX_VIDEO_SIZE: string;
    REACT_APP_ALLOWED_VIDEO_TYPES: string;
    
    // Cache Configuration
    REACT_APP_CACHE_TTL: string;
    
    // Stripe Configuration
    REACT_APP_STRIPE_PUBLIC_KEY: string;
    
    // Debug Mode
    REACT_APP_DEBUG_MODE: string;
  }
} 