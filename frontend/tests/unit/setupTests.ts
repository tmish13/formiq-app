import '@testing-library/jest-dom';
import { server } from '../../src/mocks/server';

// Enable API mocking
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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

jest.spyOn(console, 'warn').mockImplementation((...args) => {
  // Ignore warning messages from libraries
  if (
    args[0]?.includes?.('Warning: React does not recognize') ||
    args[0]?.includes?.('Warning: The tag') ||
    args[0]?.includes?.('requestAnimationFrame')
  ) {
    return;
  }

  originalConsoleWarn(...args);
});

// Increase Jest timeout
jest.setTimeout(10000);

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
});
window.IntersectionObserver = mockIntersectionObserver;

// Mock the ResizeObserver
window.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
}); 