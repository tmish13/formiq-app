import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { RootState } from '../store';
import { ModernThemeProvider } from '../contexts/ModernThemeContext';

// Create a mock store for testing
export const createMockStore = (preloadedState: Partial<RootState> = {}) => {
  return configureStore({
    reducer: {
      auth: (state = {}) => state,
      formCheck: (state = {}) => state,
      subscription: (state = {}) => state,
      workout: (state = {}) => state,
      formAnalysis: (state = {}) => state,
    },
    preloadedState: preloadedState as RootState,
  });
};

// Wrapper component that includes all providers
const AllTheProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const store = createMockStore();
  
  return (
    <Provider store={store}>
      <ModernThemeProvider>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </ModernThemeProvider>
    </Provider>
  );
};

// Custom render function with all providers
const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) => render(ui, { wrapper: AllTheProviders, ...options });

// Re-export everything
export * from '@testing-library/react';

// Override render method
export { customRender as render };

// Export a function to render with a specific store state
export const renderWithProviders = (
  ui: React.ReactElement,
  { preloadedState = {}, ...renderOptions } = {}
) => {
  const store = createMockStore(preloadedState);
  
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>
      <ModernThemeProvider>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </ModernThemeProvider>
    </Provider>
  );
  
  return {
    store,
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
  };
};
