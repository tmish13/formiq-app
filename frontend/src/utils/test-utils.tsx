import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from '../ThemeProvider';
import { Provider } from 'react-redux';
import { store } from '../store';
import { BrowserRouter } from 'react-router-dom';
import ErrorBoundary from '../components/ErrorBoundary';
import { ApiError } from '../services/apiService';
import { StorageService } from '../services/storageService';
import { NetworkRecoveryService } from '../services/networkRecovery';

// Mock storage service
export class MockStorageService {
  private store: { [key: string]: string } = {};

  async get(key: string): Promise<string | null> {
    return this.store[key] || null;
  }

  async set(key: string, value: string): Promise<void> {
    this.store[key] = value;
  }

  async remove(key: string): Promise<void> {
    delete this.store[key];
  }

  async clear(): Promise<void> {
    this.store = {};
  }

  async keys(): Promise<string[]> {
    return Object.keys(this.store);
  }
}

// Mock network recovery service
export class MockNetworkRecoveryService {
  private isOnline = true;
  private pendingRequests: any[] = [];

  setOnline(online: boolean): void {
    this.isOnline = online;
  }

  async executeRequest(request: any): Promise<any> {
    if (!this.isOnline) {
      this.pendingRequests.push(request);
      throw new Error('Network offline');
    }
    return Promise.resolve({ status: 200, data: {} });
  }

  getPendingRequests(): any[] {
    return this.pendingRequests;
  }

  clearPendingRequests(): void {
    this.pendingRequests = [];
  }
}

// Custom render function that includes providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
  mockStorage?: MockStorageService;
  mockNetwork?: MockNetworkRecoveryService;
}

const customRender = (
  ui: ReactElement,
  {
    initialRoute = '/',
    mockStorage = new MockStorageService(),
    mockNetwork = new MockNetworkRecoveryService(),
    ...renderOptions
  }: CustomRenderOptions = {}
) => {
  // Override implementations
  (StorageService as any).instance = mockStorage;
  (NetworkRecoveryService as any).instance = mockNetwork;

  window.history.pushState({}, 'Test page', initialRoute);

  const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
    return (
      <Provider store={store}>
        <ThemeProvider>
          <BrowserRouter>
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </BrowserRouter>
        </ThemeProvider>
      </Provider>
    );
  };

  return {
    ...render(ui, { wrapper: AllTheProviders, ...renderOptions }),
    mockStorage,
    mockNetwork
  };
};

// Create a mock API error
const createApiError = (
  status: number,
  message: string,
  code?: string,
  data?: unknown
): ApiError => ({
  name: 'ApiError',
  status,
  message,
  code,
  data,
  timestamp: new Date().toISOString()
});

// Mock response creator
const createMockApiResponse = <T extends unknown>(data: T) => ({
  data,
  status: 200,
  metadata: {
    timestamp: new Date().toISOString(),
    requestId: Math.random().toString(36).substring(7)
  }
});

// Mock form data helper
const createFormData = (obj: Record<string, any>): FormData => {
  const formData = new FormData();
  Object.entries(obj).forEach(([key, value]) => {
    if (value instanceof Blob) {
      formData.append(key, value);
    } else if (typeof value === 'object') {
      formData.append(key, JSON.stringify(value));
    } else {
      formData.append(key, String(value));
    }
  });
  return formData;
};

// Mock file creator
const createMockFile = (
  name: string,
  type: string,
  size: number
): File => {
  const file = new File([''], name, { type });
  Object.defineProperty(file, 'size', {
    get() {
      return size;
    }
  });
  return file;
};

// Mock video element
const createMockVideoElement = () => {
  const mockVideo = document.createElement('video');
  Object.defineProperty(mockVideo, 'readyState', {
    get() {
      return 4; // HAVE_ENOUGH_DATA
    }
  });
  Object.defineProperty(mockVideo, 'videoWidth', {
    get() {
      return 1280;
    }
  });
  Object.defineProperty(mockVideo, 'videoHeight', {
    get() {
      return 720;
    }
  });
  return mockVideo;
};

// Wait for element to be removed with timeout
const waitForElementToBeRemoved = async (
  callback: () => Element | null,
  timeout = 5000
) => {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (!callback()) {
      return;
    }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('Element not removed within timeout');
};

// Mock pose detection result
const createMockPoseDetection = (confidence = 0.9) => ({
  score: confidence,
  keypoints: [
    { x: 0, y: 0, score: confidence, name: 'nose' },
    { x: 10, y: 0, score: confidence, name: 'left_eye' },
    { x: -10, y: 0, score: confidence, name: 'right_eye' },
    { x: 10, y: 10, score: confidence, name: 'left_shoulder' },
    { x: -10, y: 10, score: confidence, name: 'right_shoulder' }
  ]
});

// Mock Capacitor plugins
export const mockCapacitor = {
  Camera: {
    getPhoto: jest.fn().mockResolvedValue({
      dataUrl: 'data:image/jpeg;base64,mockImageData'
    })
  },
  Device: {
    getInfo: jest.fn().mockResolvedValue({
      platform: 'web',
      isVirtual: false,
      manufacturer: 'test',
      model: 'test',
      operatingSystem: 'test',
      osVersion: 'test',
      webViewVersion: 'test'
    })
  },
  Storage: {
    get: jest.fn(),
    set: jest.fn(),
    remove: jest.fn(),
    clear: jest.fn()
  }
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

// Wait utilities
export const waitForPoseDetection = () =>
  new Promise(resolve => setTimeout(resolve, 100));

export const waitForAnimation = () =>
  new Promise(resolve => setTimeout(resolve, 300));

export {
  customRender as render,
  createApiError,
  createMockApiResponse,
  createFormData,
  createMockFile,
  createMockVideoElement,
  waitForElementToBeRemoved,
  createMockPoseDetection
}; 