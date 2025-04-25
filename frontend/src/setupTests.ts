// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like: expect(element).toHaveTextContent(/react/i)
import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';
import { cleanup, configure } from '@testing-library/react';
import { server } from './mocks/server';
import React from 'react';
import 'whatwg-fetch';
import { LocalStorageMock, clearMockStorage } from './mocks/storage';

// Import mocks
import './mocks/cameraMock';
import './mocks/storage';

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
global.IntersectionObserver = class MockIntersectionObserver implements IntersectionObserver {
  readonly root: Element | null = null;
  readonly rootMargin: string = '0px';
  readonly thresholds: ReadonlyArray<number> = [0];
  
  constructor(private callback: IntersectionObserverCallback) {}
  
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
  takeRecords = () => [];
} as any;

// Mock navigator.mediaDevices
Object.defineProperty(navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: jest.fn().mockResolvedValue({}),
    enumerateDevices: jest.fn().mockResolvedValue([]),
  },
});

// Mock ResizeObserver
global.ResizeObserver = class MockResizeObserver implements ResizeObserver {
  constructor(private callback: ResizeObserverCallback) {}
  observe = jest.fn();
  unobserve = jest.fn();
  disconnect = jest.fn();
} as any;

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
  createObjectURL: jest.fn(() => 'mock-url'),
  revokeObjectURL: jest.fn()
};

Object.defineProperty(window, 'URL', {
  value: mockURL,
  writable: true
});

// Suppress console errors and warnings during tests
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

jest.spyOn(console, 'error').mockImplementation((...args) => {
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

// Start mock server before tests
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));

// Reset any request handlers that we may add during the tests,
// so they don't affect other tests
afterEach(() => {
  server.resetHandlers();
  cleanup(); // Added explicit cleanup
  jest.clearAllMocks();
  clearMockStorage(); // Clear mock storage after each test
});

// Clean up after the tests are finished
afterAll(() => server.close());

// Increase Jest timeout
jest.setTimeout(10000); 