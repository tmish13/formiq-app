import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { theme } from '../../src/theme';
import rootReducer from '../../src/store/rootReducer';

// Create a test store
export const createTestStore = (preloadedState = {}) => {
  return configureStore({
    reducer: rootReducer,
    preloadedState
  });
};

// Create a wrapper with all providers
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  const store = createTestStore();
  
  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </ThemeProvider>
    </Provider>
  );
};

// Custom render function
const customRender = (
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) => render(ui, { wrapper: AllTheProviders, ...options });

// Mock Capacitor plugins
export const mockCapacitor = {
  Camera: {
    getPhoto: jest.fn().mockResolvedValue({
      path: 'path/to/photo.jpg',
      webPath: 'blob:photo.jpg',
      format: 'jpeg'
    })
  },
  Preferences: {
    get: jest.fn().mockResolvedValue({ value: 'test-token' }),
    set: jest.fn().mockResolvedValue(undefined)
  },
  Network: {
    getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' }),
    addListener: jest.fn().mockReturnValue({ remove: jest.fn() })
  }
};

// Mock form check data
export const mockFormCheck = {
  id: '456',
  exercise: 'squat',
  feedback: ['Good depth', 'Keep chest up'],
  score: 85,
  createdAt: new Date().toISOString()
};

// Mock user data
export const mockUser = {
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user'
};

// re-export everything
export * from '@testing-library/react';
export { customRender as render }; 