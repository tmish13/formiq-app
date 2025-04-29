import { ApiError } from '../types/api';

// Mock classes for testing
export class MockStorageService {
  private storage: Record<string, string> = {};

  async get(key: string): Promise<string | null> {
    return this.storage[key] || null;
  }

  async set(key: string, value: string): Promise<void> {
    this.storage[key] = value;
  }

  async remove(key: string): Promise<void> {
    delete this.storage[key];
  }

  async clear(): Promise<void> {
    this.storage = {};
  }
}

export class MockNetworkRecoveryService {
  async retryRequest<T>(request: () => Promise<T>): Promise<T> {
    return request();
  }
}

// Helper functions for creating test data
export const createApiError = (
  status: number,
  message: string,
  name: string = 'ApiError',
  data?: unknown
): ApiError => ({
  name,
  status,
  message,
  data
});

export const createMockFormData = (data: Record<string, string | Blob>) => {
  const formData = new FormData();
  Object.entries(data).forEach(([key, value]) => {
    formData.append(key, value);
  });
  return formData;
};

export const createMockFile = (name: string, type: string, size: number = 1024) => {
  return new File(['test'], name, { type });
};

export const createMockVideoElement = () => {
  const video = document.createElement('video');
  Object.defineProperty(video, 'duration', { value: 10 });
  Object.defineProperty(video, 'videoWidth', { value: 1280 });
  Object.defineProperty(video, 'videoHeight', { value: 720 });
  return video;
};

// Mock Capacitor plugins
export const mockCapacitorPlugins = {
  Camera: {
    getPhoto: jest.fn().mockResolvedValue({ path: 'test/path', webPath: 'test/webPath' }),
  },
  Filesystem: {
    readFile: jest.fn().mockResolvedValue({ data: 'test-data' }),
    writeFile: jest.fn().mockResolvedValue(undefined),
    deleteFile: jest.fn().mockResolvedValue(undefined),
  },
  Storage: {
    get: jest.fn().mockResolvedValue({ value: 'test-value' }),
    set: jest.fn().mockResolvedValue(undefined),
    remove: jest.fn().mockResolvedValue(undefined),
    clear: jest.fn().mockResolvedValue(undefined),
  },
};

// Test data generators
export const generateTestPose = (overrides = {}) => ({
  keypoints: [
    { x: 0, y: 0, score: 1, name: 'nose' },
    { x: 10, y: 10, score: 1, name: 'left_shoulder' },
    { x: -10, y: 10, score: 1, name: 'right_shoulder' }
  ],
  score: 0.9,
  ...overrides
});

export const generateTestFormAnalysis = (overrides = {}) => ({
  id: 'test-analysis-id',
  exercise_type: 'squat',
  score: 85,
  feedback: [
    { type: 'success', message: 'Good form' },
    { type: 'warning', message: 'Keep your back straight' }
  ],
  timestamp: Date.now(),
  ...overrides
});

export const mockTheme = {
  colors: {
    primary: {
      light: '#4dabf5',
      main: '#228be6',
      dark: '#1c7ed6',
      contrastText: '#ffffff'
    },
    secondary: {
      light: '#868e96',
      main: '#495057',
      dark: '#343a40',
      contrastText: '#ffffff'
    },
    error: {
      light: '#ff6b6b',
      main: '#fa5252',
      dark: '#e03131',
      contrastText: '#ffffff'
    },
    warning: {
      light: '#ffd43b',
      main: '#fcc419',
      dark: '#fab005',
      contrastText: '#000000'
    },
    success: {
      light: '#69db7c',
      main: '#40c057',
      dark: '#2f9e44',
      contrastText: '#ffffff'
    },
    info: {
      light: '#4dabf7',
      main: '#339af0',
      dark: '#228be6',
      contrastText: '#ffffff'
    },
    gray: {
      light: '#f8f9fa',
      main: '#e9ecef',
      dark: '#dee2e6',
      contrastText: '#000000'
    },
    background: {
      main: '#ffffff',
      secondary: '#f8f9fa',
      paper: '#ffffff'
    },
    text: {
      primary: '#212529',
      secondary: '#495057',
      disabled: '#adb5bd',
      inverse: '#ffffff'
    },
    border: {
      main: '#dee2e6',
      light: '#e9ecef'
    },
    disabled: '#adb5bd'
  },
  typography: {
    fontFamily: {
      primary: "'Inter', sans-serif",
      secondary: "'Poppins', sans-serif",
      mono: "'SF Mono', monospace"
    },
    fontSize: {
      xxs: '0.625rem',
      xs: '0.75rem',
      sm: '0.875rem',
      md: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      xxl: '1.5rem'
    },
    fontWeight: {
      light: 300,
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    },
    lineHeight: {
      tight: '1.25',
      normal: '1.5',
      relaxed: '1.75'
    }
  },
  spacing: {
    xxs: '0.25rem',
    xs: '0.5rem',
    sm: '0.75rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    xxl: '3rem'
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.5rem',
    lg: '1rem',
    full: '9999px'
  },
  shadows: {
    none: 'none',
    small: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    medium: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    large: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
  },
  transitions: {
    duration: {
      shortest: 150,
      shorter: 200,
      short: 250,
      standard: 300,
      complex: 375,
      enteringScreen: 225,
      leavingScreen: 195
    },
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)'
    }
  }
};

/**
 * Creates a mock StorageService instance for testing
 */
export function createMockStorageService() {
  const mockStorage = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn(),
    get: jest.fn(),
    set: jest.fn(),
    remove: jest.fn(),
    getAllKeys: jest.fn().mockResolvedValue([]),
    multiGet: jest.fn().mockResolvedValue([]),
    multiSet: jest.fn().mockResolvedValue(undefined),
    multiRemove: jest.fn().mockResolvedValue(undefined),
    mergeItem: jest.fn().mockResolvedValue(undefined),
    // Form analysis cache methods
    cacheFormAnalysis: jest.fn().mockResolvedValue(undefined),
    getFormAnalysisCache: jest.fn().mockResolvedValue({}),
    // User preferences methods
    getUserPreferences: jest.fn().mockResolvedValue({}),
    setUserPreferences: jest.fn().mockResolvedValue(undefined),
    // Workout data methods
    getWorkoutData: jest.fn().mockResolvedValue({}),
    setWorkoutData: jest.fn().mockResolvedValue(undefined),
    // Social data methods
    getSocialData: jest.fn().mockResolvedValue({}),
    setSocialData: jest.fn().mockResolvedValue(undefined),
  };

  return mockStorage;
} 