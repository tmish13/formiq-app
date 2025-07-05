/**
 * Integration Test Configuration for FormIQ
 * 
 * This configuration enables real backend testing, mobile integration,
 * and comprehensive user flow validation.
 */

export interface IntegrationTestConfig {
  backend: {
    baseUrl: string;
    timeout: number;
    enableRealApi: boolean;
    mockFallback: boolean;
  };
  mobile: {
    testNativeFeatures: boolean;
    simulateMobileEnvironment: boolean;
    testCapacitorPlugins: boolean;
  };
  auth: {
    testTokenRefresh: boolean;
    enableAuthFlow: boolean;
    mockCredentials: {
      username: string;
      password: string;
    };
  };
  video: {
    testRealUploads: boolean;
    sampleVideoPath: string;
    uploadTimeout: number;
  };
  performance: {
    enableMetrics: boolean;
    thresholds: {
      uploadTime: number;
      analysisTime: number;
      renderTime: number;
    };
  };
}

const defaultConfig: IntegrationTestConfig = {
  backend: {
    baseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
    timeout: 30000,
    enableRealApi: process.env.INTEGRATION_REAL_API === 'true',
    mockFallback: true,
  },
  mobile: {
    testNativeFeatures: process.env.INTEGRATION_MOBILE === 'true',
    simulateMobileEnvironment: true,
    testCapacitorPlugins: process.env.CAPACITOR_TESTS === 'true',
  },
  auth: {
    testTokenRefresh: true,
    enableAuthFlow: true,
    mockCredentials: {
      username: process.env.TEST_USERNAME || 'test@formiq.com',
      password: process.env.TEST_PASSWORD || 'TestPassword123!',
    },
  },
  video: {
    testRealUploads: process.env.TEST_REAL_UPLOADS === 'true',
    sampleVideoPath: '/tests/fixtures/sample-squat-video.mp4',
    uploadTimeout: 120000, // 2 minutes
  },
  performance: {
    enableMetrics: true,
    thresholds: {
      uploadTime: 60000, // 1 minute
      analysisTime: 30000, // 30 seconds
      renderTime: 2000, // 2 seconds
    },
  },
};

export const integrationConfig = defaultConfig;

/**
 * Environment-specific configurations
 */
export const environments = {
  development: {
    ...defaultConfig,
    backend: {
      ...defaultConfig.backend,
      baseUrl: 'http://localhost:8000',
    },
  },
  staging: {
    ...defaultConfig,
    backend: {
      ...defaultConfig.backend,
      baseUrl: 'https://staging-api.formiq.com',
      enableRealApi: true,
    },
  },
  production: {
    ...defaultConfig,
    backend: {
      ...defaultConfig.backend,
      baseUrl: 'https://api.formiq.com',
      enableRealApi: true,
    },
    video: {
      ...defaultConfig.video,
      testRealUploads: false, // Don't upload to production
    },
  },
};

/**
 * Get configuration for current environment
 */
export const getIntegrationConfig = (): IntegrationTestConfig => {
  const env = process.env.NODE_ENV || 'development';
  return environments[env as keyof typeof environments] || defaultConfig;
};