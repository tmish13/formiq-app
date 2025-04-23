/// <reference types="@testing-library/jest-dom" />
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll } from 'vitest';
import { server } from '../mocks/server';
import { mockCapacitor } from './test-utils';

// Automatically cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock Capacitor plugins
jest.mock('@capacitor/camera', () => ({
  Camera: mockCapacitor.Camera
}));

jest.mock('@capacitor/preferences', () => ({
  Preferences: mockCapacitor.Preferences
}));

jest.mock('@capacitor/network', () => ({
  Network: mockCapacitor.Network
}));

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: () => null,
  unobserve: () => null,
  disconnect: () => null
});
window.IntersectionObserver = mockIntersectionObserver;

// MSW Setup
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock ResizeObserver
class MockResizeObserver {
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: MockResizeObserver
});

// Mock matchMedia
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