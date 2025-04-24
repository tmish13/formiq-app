import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { ThemeProvider as StyledThemeProvider } from 'styled-components';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import rootReducer from '../../src/store/rootReducer';
import { mockTheme } from '../__mocks__/theme/themeMock';

// Increase default Jest timeout for async tests
jest.setTimeout(10000);

// Mock localStorage
class LocalStorageMock {
  private store: Record<string, string> = {};

  clear() {
    this.store = {};
  }

  getItem(key: string) {
    return this.store[key] || null;
  }

  setItem(key: string, value: string) {
    this.store[key] = String(value);
  }

  removeItem(key: string) {
    delete this.store[key];
  }

  get length() {
    return Object.keys(this.store).length;
  }

  key(index: number) {
    return Object.keys(this.store)[index] || null;
  }
}

// Set up localStorage mock
Object.defineProperty(window, 'localStorage', {
  value: new LocalStorageMock(),
});

// Set up matchMedia mock
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

// Create a store for testing
export const createTestStore = (preloadedState = {}) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState,
    middleware: (getDefaultMiddleware) => 
      getDefaultMiddleware({
        serializableCheck: false,
      }),
  });
};

// Create a query client for testing
export const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

// TestWrapper component
interface TestWrapperProps {
  children: React.ReactNode;
  route?: string;
  preloadedState?: any;
}

export const TestWrapper = ({ 
  children, 
  route = '/', 
  preloadedState = {} 
}: TestWrapperProps) => {
  const store = createTestStore(preloadedState);
  const queryClient = createTestQueryClient();

  return React.createElement(
    MuiThemeProvider,
    { theme: mockTheme },
    React.createElement(
      StyledThemeProvider,
      { theme: mockTheme },
      React.createElement(
        Provider,
        { store: store, children: React.createElement(
          QueryClientProvider,
          { client: queryClient },
          React.createElement(
            MemoryRouter,
            { initialEntries: [route] },
            children
          )
        ) }
      )
    )
  );
};

// Custom render function that includes all providers
export const renderWithProviders = (
  ui: React.ReactElement,
  {
    route = '/',
    preloadedState = {},
    ...renderOptions
  } = {}
): RenderResult => {
  return render(
    React.createElement(
      TestWrapper, 
      { route, preloadedState, children: ui }
    ),
    renderOptions
  );
};

// For backward compatibility
export const AllProviders = TestWrapper;

// Mock components for tests
export const mockComponents = {
  FormCheck: ({ children }: { children?: React.ReactNode }) => 
    React.createElement('div', { 'data-testid': 'form-check-component' }, 
      children || 'Form Check Component'
    ),
  
  Camera: ({ children }: { children?: React.ReactNode }) => 
    React.createElement('div', { 'data-testid': 'camera-component' }, 
      children || 'Camera Component'
    ),
  
  VideoPlayer: ({ children }: { children?: React.ReactNode }) => 
    React.createElement('div', { 'data-testid': 'video-player' }, 
      children || 'Video Player Component'
    ),
  
  Chart: ({ children }: { children?: React.ReactNode }) => 
    React.createElement('div', { 'data-testid': 'chart-component' }, 
      children || 'Chart Component'
    )
};

// Common mock functions used in tests
export const mockFunctions = {
  uploadFile: jest.fn().mockResolvedValue({ data: { id: 'file-123', url: 'https://example.com/file.mp4' } }),
  analyzeVideo: jest.fn().mockResolvedValue({ 
    data: { 
      id: 'analysis-123',
      score: 85,
      feedback: [
        { timestamp: 1.5, message: 'Good form', severity: 'success' },
      ] 
    } 
  }),
  login: jest.fn().mockResolvedValue({ 
    data: { 
      token: 'mock-token', 
      user: { id: 'user-123', email: 'test@example.com' } 
    } 
  }),
  fetchData: jest.fn().mockResolvedValue({ data: [] }),
};

// Common mock data structures used in tests
export const mockData = {
  user: {
    id: 'user-123',
    email: 'test@example.com',
    name: 'Test User',
    isActive: true,
  },
  formCheck: {
    id: 'fc-123',
    exercise: 'Squat',
    videoUrl: 'https://example.com/video.mp4',
    score: 85,
    feedback: [
      { timestamp: 1.5, message: 'Keep your back straight', severity: 'warning' },
      { timestamp: 3.2, message: 'Good depth', severity: 'success' },
    ],
    createdAt: '2023-04-15T12:00:00Z',
  },
  workout: {
    id: 'workout-123',
    name: 'Full Body Workout',
    exercises: [
      { id: 'ex-1', name: 'Squat', sets: 3, reps: 10 },
      { id: 'ex-2', name: 'Push-up', sets: 3, reps: 15 },
    ],
    createdAt: '2023-04-10T10:00:00Z',
  },
};

// Re-export everything from RTL
export * from '@testing-library/react';
export { renderWithProviders as render }; 