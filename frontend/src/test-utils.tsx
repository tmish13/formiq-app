// This file is kept for backward compatibility with existing tests
// It now re-exports the centralized testing utilities
import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Provider } from 'react-redux';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { theme } from './theme';
import rootReducer from './store/rootReducer';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { mockTheme } from './theme/mockTheme';
import { Theme } from './theme';

// Re-export everything
export * from '@testing-library/react';

// Create a store for testing
export const createTestStore = (preloadedState = {}) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState,
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

// Options for the test render function
interface TestRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  initialRoute?: string;
  useMemoryRouter?: boolean;
  routePath?: string;
  initialState?: any;
  withoutTheme?: boolean;
  withoutRouter?: boolean;
  withoutRedux?: boolean;
  preloadedState?: any;
  store?: any;
}

// Custom render function that wraps components with all necessary providers
export function testRender(
  ui: React.ReactElement,
  {
    initialRoute = '/',
    useMemoryRouter = false,
    routePath,
    initialState = {},
    preloadedState = {},
    store = createTestStore(initialState || preloadedState),
    withoutTheme = false,
    withoutRouter = false,
    withoutRedux = false,
    ...renderOptions
  }: TestRenderOptions = {}
): RenderResult & { user: ReturnType<typeof userEvent.setup>; store: ReturnType<typeof createTestStore> } {
  const Wrapper = ({ children }: { children: React.ReactNode }) => {
    let wrappedChildren = children;

    // Wrap with route if path is provided
    if (routePath && useMemoryRouter) {
      wrappedChildren = (
        <Routes>
          <Route path={routePath} element={<>{wrappedChildren}</>} />
        </Routes>
      );
    }

    // Wrap with router if needed
    if (!withoutRouter) {
      const Router = useMemoryRouter ? MemoryRouter : BrowserRouter;
      wrappedChildren = (
        <Router initialEntries={useMemoryRouter ? [initialRoute] : undefined}>
          {wrappedChildren}
        </Router>
      );
    }

    // Wrap with Redux if needed
    if (!withoutRedux) {
      wrappedChildren = (
        <Provider store={store}>
          {wrappedChildren}
        </Provider>
      );
    }

    // Wrap with theme if needed
    if (!withoutTheme) {
      wrappedChildren = (
        <ThemeProvider theme={theme}>
          {wrappedChildren}
        </ThemeProvider>
      );
    }

    return <>{wrappedChildren}</>;
  };

  const result = render(ui, { wrapper: Wrapper, ...renderOptions });
  
  return {
    ...result,
    user: userEvent.setup(),
    store,
  };
}

// For backward compatibility
export const renderWithProviders = testRender;

// Helper function to create API errors for testing
export const createApiError = (
  status: number,
  message: string,
  code?: string,
  data?: unknown
) => ({
  status,
  message,
  code,
  data,
});

// Helper function to create mock API responses
export const createMockApiResponse = <T extends unknown>(data: T) => ({
  ok: true,
  status: 200,
  json: () => Promise.resolve(data),
});

// Helper function to create mock files for testing
export const createMockFile = (
  name: string,
  type: string,
  size: number
) => {
  const file = new File([''], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

// Helper function to generate test user data
export const generateTestUser = (overrides = {}) => ({
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  ...overrides,
});

// Helper function to generate test form analysis data
export const generateTestFormAnalysis = (overrides = {}) => ({
  id: '123',
  exercise_type: 'squat',
  score: 85,
  video_url: 'http://example.com/video.mp4',
  overall_feedback: 'Good form overall',
  issues: ['Knees caving in'],
  suggestions: ['Keep chest up'],
  ...overrides,
}); 