import { TextEncoder as NodeTextEncoder, TextDecoder as NodeTextDecoder } from 'util';
import '@testing-library/jest-dom';
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Polyfill TextEncoder/TextDecoder
global.TextEncoder = NodeTextEncoder as typeof global.TextEncoder;
global.TextDecoder = NodeTextDecoder as typeof global.TextDecoder;

// This configures a request mocking server with the given request handlers.
export const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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
  observe = jest.fn();
  disconnect = jest.fn();
  unobserve = jest.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver,
});

// Mock MediaStream
const mockMediaStream = {
  active: true,
  id: 'mock-stream-id',
  onaddtrack: null,
  onremovetrack: null,
  addTrack: jest.fn(),
  removeTrack: jest.fn(),
  getTracks: () => [{ stop: jest.fn() }],
  getVideoTracks: () => [{ stop: jest.fn() }],
  getAudioTracks: () => [],
  clone: function() { return { ...this }; },
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
};

// @ts-ignore - Mocking MediaStream for tests
global.MediaStream = jest.fn(() => mockMediaStream); 