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