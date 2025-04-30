// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like: expect(element).toHaveTextContent(/react/i)
import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';
import { cleanup, configure } from '@testing-library/react';
import { server } from './mocks/server';
import React from 'react';
import 'whatwg-fetch';
import { LocalStorageMock, clearMockStorage } from './mocks/storage';
import { MockMediaRecorder } from './__mocks__/browser/mediaRecorder';
import { jest } from '@jest/globals';

// Import mocks
import './mocks/cameraMock';
import './mocks/storage';

// Ensure Jest is available globally
if (typeof global.jest === 'undefined') {
  global.jest = require('jest-mock');
}

// Now that jest is available, we can use it for mocks
const mockJest = global.jest;

// Mock URL
class MockURL {
  constructor(url: string, base?: string) {
    return {
      href: url,
      origin: 'http://localhost',
      protocol: 'http:',
      username: '',
      password: '',
      host: 'localhost',
      hostname: 'localhost',
      port: '',
      pathname: '/',
      search: '',
      searchParams: new URLSearchParams(),
      hash: '',
      toString: () => url,
      toJSON: () => url,
    };
  }

  static createObjectURL = jest.fn().mockReturnValue('mock-url');
  static revokeObjectURL = jest.fn();
}

global.URL = MockURL as any;

// Mock TextEncoder/TextDecoder
global.TextEncoder = TextEncoder as any;
global.TextDecoder = TextDecoder as any;

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
class IntersectionObserver {
  observe = mockJest.fn();
  disconnect = mockJest.fn();
  unobserve = mockJest.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: IntersectionObserver,
});

// Mock ResizeObserver
class ResizeObserver {
  observe = mockJest.fn();
  disconnect = mockJest.fn();
  unobserve = mockJest.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: ResizeObserver,
});

// Mock navigator.mediaDevices
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: mockJest.fn().mockResolvedValue({}),
    enumerateDevices: mockJest.fn().mockResolvedValue([]),
  },
});

// Configure testing library
configure({
  testIdAttribute: 'data-testid',
});

// Setup mock for localStorage
Object.defineProperty(window, 'localStorage', {
  value: new LocalStorageMock(),
  writable: true
});

// Setup mock for sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: new LocalStorageMock(),
  writable: true
});

// Browser API Mocks
const mockURL = {
  createObjectURL: mockJest.fn(() => 'mock-url'),
  revokeObjectURL: mockJest.fn()
};

Object.defineProperty(window, 'URL', {
  value: mockURL,
  writable: true
});

// Suppress console errors and warnings during tests
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

mockJest.spyOn(console, 'error').mockImplementation((...args) => {
  // Ignore error messages from React DOM/Testing Library
  if (
    args[0]?.includes?.('Warning: An update to') ||
    args[0]?.includes?.('Warning: Cannot update a component') ||
    args[0]?.includes?.('Warning: validateDOMNesting') ||
    args[0]?.includes?.('Warning: Each child in a list') ||
    args[0]?.includes?.('Invalid DOM property') ||
    args[0]?.includes?.('Error: Login error')
  ) {
    return;
  }

  originalConsoleError(...args);
});

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => {
  server.resetHandlers();
  cleanup(); // Added explicit cleanup
  mockJest.clearAllMocks();
  clearMockStorage(); // Clear mock storage after each test
});

// Clean up after the tests are finished
afterAll(() => server.close());

// Increase Jest timeout
mockJest.setTimeout(10000);
global.URL = require('url').URL;

// Mock Capacitor
mockJest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => false,
    getPlatform: () => 'web',
  },
}));

mockJest.mock('@capacitor/camera', () => ({
  Camera: {
    checkPermissions: mockJest.fn().mockResolvedValue({ camera: 'granted' }),
    requestPermissions: mockJest.fn().mockResolvedValue({ camera: 'granted' }),
    getPhoto: mockJest.fn().mockResolvedValue({ webPath: 'mock-photo-path' }),
  },
}));

// Mock services
mockJest.mock('./services/poseAnalysisService', () => ({
  __esModule: true,
  default: {
    initialize: mockJest.fn().mockResolvedValue(undefined),
    startAnalysis: mockJest.fn().mockResolvedValue(undefined),
    stopAnalysis: mockJest.fn().mockResolvedValue(undefined),
    analyzeForm: mockJest.fn().mockResolvedValue({
      confidence: 0.95,
      isReliable: true,
      keypoints: [],
      score: 0.95,
      angles: {},
      feedback: {
        posture: 'Good posture',
        alignment: 'Proper alignment',
        suggestions: ['Keep up the good form!']
      },
      timestamp: Date.now(),
      videoUrl: 'test-video-url'
    }),
    getAnalysisHistory: mockJest.fn().mockResolvedValue([]),
    saveAnalysis: mockJest.fn().mockResolvedValue(undefined),
    dispose: mockJest.fn(),
    on: mockJest.fn(),
    emit: mockJest.fn()
  },
  poseAnalysisService: {
    initialize: mockJest.fn().mockResolvedValue(undefined),
    startAnalysis: mockJest.fn().mockResolvedValue(undefined),
    stopAnalysis: mockJest.fn().mockResolvedValue(undefined),
    analyzeForm: mockJest.fn().mockResolvedValue({
      confidence: 0.95,
      isReliable: true,
      keypoints: [],
      score: 0.95,
      angles: {},
      feedback: {
        posture: 'Good posture',
        alignment: 'Proper alignment',
        suggestions: ['Keep up the good form!']
      },
      timestamp: Date.now(),
      videoUrl: 'test-video-url'
    }),
    getAnalysisHistory: mockJest.fn().mockResolvedValue([]),
    saveAnalysis: mockJest.fn().mockResolvedValue(undefined),
    dispose: mockJest.fn(),
    on: mockJest.fn(),
    emit: mockJest.fn()
  }
}));

mockJest.mock('./services/formAnalysisService', () => ({
  __esModule: true,
  default: {
    initialize: mockJest.fn().mockResolvedValue(undefined),
    startAnalysis: mockJest.fn().mockResolvedValue(undefined),
    stopAnalysis: mockJest.fn().mockResolvedValue(undefined),
    analyzeForm: mockJest.fn().mockResolvedValue({
      confidence: 0.95,
      isReliable: true,
      keypoints: [],
      score: 0.95,
      angles: {},
      feedback: {
        posture: 'Good posture',
        alignment: 'Proper alignment',
        suggestions: ['Keep up the good form!']
      },
      timestamp: Date.now(),
      videoUrl: 'test-video-url'
    }),
    getAnalysisHistory: mockJest.fn().mockResolvedValue([]),
    saveAnalysis: mockJest.fn().mockResolvedValue(undefined),
    dispose: mockJest.fn(),
    on: mockJest.fn(),
    emit: mockJest.fn()
  },
  formAnalysisService: {
    initialize: mockJest.fn().mockResolvedValue(undefined),
    startAnalysis: mockJest.fn().mockResolvedValue(undefined),
    stopAnalysis: mockJest.fn().mockResolvedValue(undefined),
    analyzeForm: mockJest.fn().mockResolvedValue({
      confidence: 0.95,
      isReliable: true,
      keypoints: [],
      score: 0.95,
      angles: {},
      feedback: {
        posture: 'Good posture',
        alignment: 'Proper alignment',
        suggestions: ['Keep up the good form!']
      },
      timestamp: Date.now(),
      videoUrl: 'test-video-url'
    }),
    getAnalysisHistory: mockJest.fn().mockResolvedValue([]),
    saveAnalysis: mockJest.fn().mockResolvedValue(undefined),
    dispose: mockJest.fn(),
    on: mockJest.fn(),
    emit: mockJest.fn()
  }
}));

// Mock localStorage
const localStorageMock = {
  getItem: mockJest.fn(),
  setItem: mockJest.fn(),
  removeItem: mockJest.fn(),
  clear: mockJest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock MediaDevices
Object.defineProperty(window.navigator, 'mediaDevices', {
  value: {
    getUserMedia: mockJest.fn().mockResolvedValue({
      getTracks: () => [{
        stop: mockJest.fn()
      }]
    }),
    enumerateDevices: mockJest.fn().mockResolvedValue([]),
  },
});

// Mock MediaRecorder
Object.defineProperty(window, 'MediaRecorder', { value: MockMediaRecorder });

// Mock ResizeObserver
window.ResizeObserver = mockJest.fn().mockImplementation(() => ({
  observe: mockJest.fn(),
  unobserve: mockJest.fn(),
  disconnect: mockJest.fn(),
}));
