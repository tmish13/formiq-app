import React from 'react';
import { render, RenderOptions, RenderResult, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from 'styled-components';
import { Provider } from 'react-redux';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { configureStore, EnhancedStore } from '@reduxjs/toolkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { theme } from '../../src/theme';
import rootReducer from '../../src/store/rootReducer';
import { setupServer } from 'msw/node';
import { defaultHandlers } from './msw';

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
      gcTime: 0,
      staleTime: 0,
    },
    mutations: {
      retry: false,
    }
  }
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
  withoutReactQuery?: boolean;
  preloadedState?: any;
  store?: EnhancedStore;
  routes?: { path: string; element: React.ReactNode }[];
}

// Return type for our render function
interface CustomRenderResult extends RenderResult {
  user: ReturnType<typeof userEvent.setup>;
  store: ReturnType<typeof createTestStore>;
  queryClient: QueryClient;
}

/**
 * Enhanced version of render that provides all providers needed for typical tests
 * Wraps components with Redux, Router, Theme, and React Query providers as needed
 * Also provides utilities for interacting with components
 */
export function testRender(
  ui: React.ReactElement,
  {
    initialRoute = '/',
    useMemoryRouter = true, // Default to MemoryRouter for tests
    routePath,
    routes,
    initialState = {},
    preloadedState = {},
    store = createTestStore(initialState || preloadedState),
    withoutTheme = false,
    withoutRouter = false,
    withoutRedux = false,
    withoutReactQuery = false,
    ...renderOptions
  }: TestRenderOptions = {}
): CustomRenderResult {
  // Create a query client for this test
  const queryClient = createTestQueryClient();
  
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

    // Wrap with custom routes if provided
    if (routes && routes.length > 0 && useMemoryRouter) {
      wrappedChildren = (
        <Routes>
          {routes.map(({ path, element }) => (
            <Route key={path} path={path} element={element} />
          ))}
          {/* Add default route for the component under test */}
          <Route path="*" element={<>{wrappedChildren}</>} />
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

    // Wrap with React Query if needed
    if (!withoutReactQuery) {
      wrappedChildren = (
        <QueryClientProvider client={queryClient}>
          {wrappedChildren}
        </QueryClientProvider>
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
    user: userEvent.setup({ delay: null }), // Use null delay for faster tests
    store,
    queryClient,
  };
}

/**
 * Helper method to pause execution for a specific amount of time
 * Useful for testing loading states or animations
 */
export const waitForTime = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Setup MSW for API mocking in tests
 * @param handlers MSW request handlers
 * @returns MSW server instance
 */
export const setupMockServer = (handlers: any[] = []) => {
  const server = setupServer(...defaultHandlers, ...handlers);
  
  beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());
  
  return server;
};

/**
 * Find an element by its text, with options to ensure exact match
 * More reliable than getByText with complex text content
 */
export const findElementByText = (text: string, exact = false, role?: string) => {
  if (role) {
    return screen.getByRole(role, { name: exact ? text : new RegExp(text, 'i') });
  }
  return screen.getByText(exact ? text : new RegExp(text, 'i'));
};

/**
 * Find an input by its label text
 * More reliable than getByLabelText in some cases
 */
export const findInputByLabel = (labelText: string, exact = false) => {
  return screen.getByLabelText(exact ? labelText : new RegExp(labelText, 'i'));
};

/**
 * Find a button by its text
 * Convenience wrapper around getByRole
 */
export const findButtonByText = (text: string, exact = false) => {
  return screen.getByRole('button', { name: exact ? text : new RegExp(text, 'i') });
};

/**
 * Find a link by its text
 * Convenience wrapper around getByRole
 */
export const findLinkByText = (text: string, exact = false) => {
  return screen.getByRole('link', { name: exact ? text : new RegExp(text, 'i') });
};

// Export for backward compatibility
export const renderWithProviders = testRender; 