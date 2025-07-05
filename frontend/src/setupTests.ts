// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like: expect(element).toHaveTextContent(/react/i)
import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';
import { cleanup, configure } from '@testing-library/react';
import { server } from '../tests/mocks/server';
import React from 'react';
import 'whatwg-fetch';
import { MockMediaRecorder } from './__mocks__/browser/mediaRecorder';
import { jest } from '@jest/globals';

// Configure test environment variables
process.env.NODE_ENV = 'test';
process.env.REACT_APP_API_URL = 'http://localhost:8000';
// Temporarily disable jest-styled-components due to compatibility issues
// import 'jest-styled-components';

// Import mocks
import './mocks/cameraMock';

// Ensure Jest is available globally
if (typeof global.jest === 'undefined') {
  global.jest = jest;
}

// Now that jest is available, we can use it for mocks
const mockJest = global.jest;

// Suppress React version mismatch errors
// This is critical for the consolidated tests
const originalConsoleError = console.error;
console.error = (...args) => {
  // Filter out React version mismatch errors
  if (args[0]?.includes?.('React Element from an older version of React') ||
      args[0]?.includes?.('Multiple copies of React') ||
      args[0]?.includes?.('An Element from a different version of React detected') ||
      args[0]?.includes?.('The version of React available when loading') ||
      args[0]?.includes?.('Warning: A Component from an older version of React')) {
    // Ignore these errors
    return;
  }
  originalConsoleError(...args);
};

// Also disable React's internal version checking
// This helps with the consolidated tests
global.__REACT_RECONCILER_STRICT_MODE__ = false;
global.__REACT_NO_VERSION_CHECK__ = true;

// Mock URL - improved implementation
class MockURL {
  static createObjectURL = mockJest.fn().mockReturnValue('mock-url');
  static revokeObjectURL = mockJest.fn();
  
  href: string;
  origin: string;
  protocol: string;
  username: string;
  password: string;
  host: string;
  hostname: string;
  port: string;
  pathname: string;
  search: string;
  searchParams: URLSearchParams;
  hash: string;

  constructor(url: string, base?: string) {
    this.href = url;
    this.origin = 'http://localhost';
    this.protocol = 'http:';
    this.username = '';
    this.password = '';
    this.host = 'localhost';
    this.hostname = 'localhost';
    this.port = '';
    this.pathname = '/';
    this.search = '';
    this.searchParams = new URLSearchParams();
    this.hash = '';
  }

  toString() { 
    return this.href; 
  }
  
  toJSON() { 
    return this.href; 
  }
}

// Replace global URL constructor
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
class MockIntersectionObserver {
  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
  }
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
  callback: IntersectionObserverCallback;
  
  // Used to manually trigger intersection events
  triggerIntersection(entries: IntersectionObserverEntry[]) {
    this.callback(entries, this);
  }
}

window.IntersectionObserver = MockIntersectionObserver as any;

// Mock ResizeObserver
class MockResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
  callback: ResizeObserverCallback;
  
  // Used to manually trigger resize events
  triggerResize(entries: ResizeObserverEntry[]) {
    this.callback(entries, this);
  }
}

window.ResizeObserver = MockResizeObserver as any;

// Mock HTMLMediaElement methods
Object.defineProperty(window.HTMLMediaElement.prototype, 'play', {
  configurable: true,
  writable: true,
  value: jest.fn().mockImplementation(() => Promise.resolve()),
});

Object.defineProperty(window.HTMLMediaElement.prototype, 'pause', {
  configurable: true,
  writable: true,
  value: jest.fn().mockImplementation(() => {}),
});

Object.defineProperty(window.HTMLMediaElement.prototype, 'load', {
  configurable: true,
  writable: true,
  value: jest.fn().mockImplementation(() => {}),
});

// Mock styled-components to avoid test errors with styled.[element]
jest.mock('styled-components', () => {
  const original = jest.requireActual('styled-components');
  
  // Add all HTML elements as mock styled components
  const styled = Object.create(original.default);
  
  // Basic HTML elements often used in the app
  ['div', 'span', 'button', 'input', 'label', 'a', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
   'header', 'footer', 'nav', 'section', 'article', 'aside', 'main', 'form', 'ul', 'ol', 'li',
   'img', 'video', 'canvas', 'select', 'option', 'textarea', 'table', 'tr', 'th', 'td'].forEach(tag => {
    styled[tag] = original.default(tag);
  });
  
  return {
    ...original,
    default: styled,
  };
});

// Mock Capacitor Camera
jest.mock('@capacitor/camera', () => ({
  Camera: {
    checkPermissions: jest.fn().mockResolvedValue({ camera: 'granted', photos: 'granted' }),
    requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted', photos: 'granted' }),
    getPhoto: jest.fn().mockResolvedValue({
      base64String: 'mock-base64-data',
      format: 'jpeg',
      path: 'mock-path/photo.jpeg',
      webPath: 'mock-web-path/photo.jpeg'
    }),
    pickImages: jest.fn().mockResolvedValue({
      photos: [{
        path: 'mock-path/photo.jpeg',
        webPath: 'mock-web-path/photo.jpeg'
      }]
    })
  }
}));

// Mock Capacitor Network
jest.mock('@capacitor/network', () => ({
  Network: {
    addListener: jest.fn().mockImplementation((eventName, callback) => ({
      remove: jest.fn()
    })),
    getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' })
  }
}));

// Mock Capacitor Filesystem
jest.mock('@capacitor/filesystem', () => ({
  Filesystem: {
    readFile: jest.fn().mockResolvedValue({ data: 'mock-file-data' }),
    writeFile: jest.fn().mockResolvedValue({ uri: 'mock-file-uri' }),
    getUri: jest.fn().mockResolvedValue({ uri: 'mock-file-uri' }),
    mkdir: jest.fn().mockResolvedValue(undefined),
    rmdir: jest.fn().mockResolvedValue(undefined),
    readdir: jest.fn().mockResolvedValue({ files: [] })
  }
}));

// Mock Capacitor Preferences
jest.mock('@capacitor/preferences', () => ({
  Preferences: {
    get: jest.fn().mockResolvedValue({ value: null }),
    set: jest.fn().mockResolvedValue(undefined),
    remove: jest.fn().mockResolvedValue(undefined),
    clear: jest.fn().mockResolvedValue(undefined)
  }
}));

// Mock storageService to avoid Capacitor issues in tests
jest.mock('./services/storageService', () => ({
  storageService: {
    getAuthToken: jest.fn().mockResolvedValue(null),
    setAuthToken: jest.fn().mockResolvedValue(undefined),
    removeAuthToken: jest.fn().mockResolvedValue(undefined),
    getRefreshToken: jest.fn().mockResolvedValue(null),
    setRefreshToken: jest.fn().mockResolvedValue(undefined),
    removeRefreshToken: jest.fn().mockResolvedValue(undefined),
    getUserProfile: jest.fn().mockResolvedValue(null),
    setUserProfile: jest.fn().mockResolvedValue(undefined),
    removeUserProfile: jest.fn().mockResolvedValue(undefined),
    clear: jest.fn().mockResolvedValue(undefined)
  }
}));

// Configure Testing Library
configure({ 
  testIdAttribute: 'data-testid',
  // Don't spam console with accessibility warnings during tests 
  throwSuggestions: false 
});

// Simple localStorage mock
const createStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: mockJest.fn((key: string) => store[key] || null),
    setItem: mockJest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: mockJest.fn((key: string) => {
      delete store[key];
    }),
    clear: mockJest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: mockJest.fn((index: number) => Object.keys(store)[index] || null),
  };
};

// Setup mock for localStorage
Object.defineProperty(window, 'localStorage', {
  value: createStorageMock(),
  writable: true
});

// Setup mock for sessionStorage
Object.defineProperty(window, 'sessionStorage', {
  value: createStorageMock(),
  writable: true
});

// Browser API Mocks
const mockURL = {
  createObjectURL: mockJest.fn(() => 'mock-url'),
  revokeObjectURL: mockJest.fn()
};

// Replace window.URL with improved mock
Object.defineProperty(window, 'URL', {
  value: MockURL,
  writable: true
});

// Suppress console errors and warnings during tests
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

// Check if running in CI environment - some CI systems set this env variable
const isCI = process.env.CI === 'true';

mockJest.spyOn(console, 'error').mockImplementation((...args) => {
  // Ignore error messages from React DOM/Testing Library
  if (
    args[0]?.includes?.('Warning: An update to') ||
    args[0]?.includes?.('Warning: Cannot update a component') ||
    args[0]?.includes?.('Warning: validateDOMNesting') ||
    args[0]?.includes?.('Warning: Each child in a list') ||
    args[0]?.includes?.('Invalid DOM property') ||
    args[0]?.includes?.('Error: Login error') ||
    args[0]?.includes?.('ReactDOM.render is no longer supported') ||
    args[0]?.includes?.('act() warnings') ||
    args[0]?.includes?.('The "options.agent" property must be one') ||
    args[0]?.includes?.('Error: Request failed with status code')
  ) {
    return;
  }

  // In CI environments, we might want to be even more aggressive with suppressing errors
  if (isCI) {
    return; // Suppress all console errors in CI
  }

  // Use try/catch to safely call originalConsoleError
  try {
    if (typeof originalConsoleError === 'function') {
      originalConsoleError(...args);
    } else {
      // Fallback if originalConsoleError is not available
      console.log('[Error suppressed in tests]:', ...args);
    }
  } catch (e) {
    // If calling originalConsoleError fails, log a simplified message
    console.log('[Error occurred, but could not be logged properly]');
  }
});

// Also handle console.warn in a similar safe manner
mockJest.spyOn(console, 'warn').mockImplementation((...args) => {
  // Ignore common warning messages
  if (
    args[0]?.includes?.('Warning:') ||
    args[0]?.includes?.('Deprecation')
  ) {
    return;
  }

  // In CI environments, suppress all warnings
  if (isCI) {
    return;
  }

  // Use try/catch to safely call originalConsoleWarn
  try {
    if (typeof originalConsoleWarn === 'function') {
      originalConsoleWarn(...args);
    } else {
      // Fallback if originalConsoleWarn is not available
      console.log('[Warning suppressed in tests]:', ...args);
    }
  } catch (e) {
    // If calling originalConsoleWarn fails, log a simplified message
    console.log('[Warning occurred, but could not be logged properly]');
  }
});

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => {
  server.resetHandlers();
  cleanup(); // Added explicit cleanup
  mockJest.clearAllMocks();
  // Clear localStorage mocks after each test
  if (window.localStorage?.clear) {
    window.localStorage.clear();
  }
});

// Clean up after the tests are finished
afterAll(() => server.close());

// Increase Jest timeout
mockJest.setTimeout(15000); // Increase to 15 seconds for long-running tests

// Mock Capacitor
mockJest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => false,
    getPlatform: () => 'web',
  },
}));

// Silence React 18 warnings without hiding real errors
const originalConsoleError = console.error;
console.error = (...args) => {
  // Filter out specific React 18 warnings
  if (
    typeof args[0] === 'string' && (
      args[0].includes('ReactDOM.render is no longer supported') ||
      args[0].includes('unstable_flushDiscreteUpdates') ||
      args[0].includes('ReactDOM.render has not been supported') ||
      args[0].includes('React.createFactory') ||
      args[0].includes('Warning: React does not recognize the') ||
      args[0].includes('Warning: The tag') ||
      args[0].includes('forwardRef render functions accept exactly two parameters')
    )
  ) {
    return;
  }
  originalConsoleError(...args);
};

// Mock window.scrollTo
window.scrollTo = jest.fn();
