import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { BrowserRouter } from 'react-router-dom';
import { theme } from '../theme';
import { ErrorBoundary } from '../components/ErrorBoundary';
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

// Custom render function with providers
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
  mockStorage?: MockStorageService;
  mockNetwork?: MockNetworkRecoveryService;
}

export function renderWithProviders(
  ui: React.ReactElement,
  {
    initialRoute = '/',
    mockStorage = new MockStorageService(),
    mockNetwork = new MockNetworkRecoveryService(),
    ...renderOptions
  }: CustomRenderOptions = {}
) {
  // Override implementations
  (StorageService as any).instance = mockStorage;
  (NetworkRecoveryService as any).instance = mockNetwork;

  window.history.pushState({}, 'Test page', initialRoute);

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <BrowserRouter>
        <ThemeProvider theme={theme}>
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </ThemeProvider>
      </BrowserRouter>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    mockStorage,
    mockNetwork
  };
}

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

// Mock pose detection
export const mockPoseDetection = {
  createDetector: jest.fn().mockResolvedValue({
    estimatePoses: jest.fn().mockResolvedValue([
      {
        keypoints: [
          { x: 0, y: 0, score: 1, name: 'nose' },
          { x: 10, y: 10, score: 1, name: 'left_shoulder' },
          { x: -10, y: 10, score: 1, name: 'right_shoulder' }
        ],
        score: 0.9
      }
    ]),
    dispose: jest.fn()
  })
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