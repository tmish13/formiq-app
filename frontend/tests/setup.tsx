import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';
import { cleanup, configure } from '@testing-library/react';
import { server } from './utils/testServer';
import React from 'react';
import 'whatwg-fetch';
import { LocalStorageMock } from './__mocks__/storage';
import { clearMockStorage } from './mocks/storage';

// Import mocks
import './__mocks__/cameraMock.js';
import './mocks/storage';

// Polyfill TextEncoder and TextDecoder
global.TextEncoder = TextEncoder as any;
global.TextDecoder = TextDecoder as any;

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

// Setup mock for window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // Deprecated
    removeListener: jest.fn(), // Deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
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

// Browser API Mocks
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

// Network status mock
Object.defineProperty(navigator, 'onLine', {
  configurable: true,
  value: true,
});

// Mock matchMedia (this appears to be duplicated from above, removing one)
// Object.defineProperty(window, 'matchMedia', {
//   writable: true,
//   value: jest.fn().mockImplementation(query => ({
//     matches: false,
//     media: query,
//     onchange: null,
//     addListener: jest.fn(),
//     removeListener: jest.fn(),
//     addEventListener: jest.fn(),
//     removeEventListener: jest.fn(),
//     dispatchEvent: jest.fn(),
//   })),
// }); 