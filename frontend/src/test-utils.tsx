// This file is kept for backward compatibility with existing tests
// It now re-exports the centralized testing utilities
import React from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import { ThemeProvider as StyledThemeProvider } from 'styled-components';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import rootReducer from './store/rootReducer';
import { mockTheme } from '../tests/__mocks__/theme/themeMock';

// Re-export everything
export * from '@testing-library/react';

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

  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <StyledThemeProvider theme={mockTheme}>
          <MuiThemeProvider theme={mockTheme}>
            <MemoryRouter initialEntries={[route]}>
              {children}
            </MemoryRouter>
          </MuiThemeProvider>
        </StyledThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
};

// Custom render function that includes providers
export const renderWithProviders = (
  ui: React.ReactElement,
  {
    route = '/',
    preloadedState = {},
    ...renderOptions
  } = {}
): RenderResult => {
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <TestWrapper route={route} preloadedState={preloadedState}>
      {children}
    </TestWrapper>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// For backward compatibility
export const testRender = renderWithProviders;

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