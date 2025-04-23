import React from 'react';
import { screen, render, waitFor } from '@testing-library/react';
import { ProtectedRoute } from '../ProtectedRoute';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../theme';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

const TestComponent = () => <div>Protected Content</div>;

// Mock the authService
jest.mock('../../services/auth', () => ({
  authService: {
    isAuthenticated: jest.fn(),
    validateToken: jest.fn(),
    getCurrentUser: jest.fn()
  }
}));

// Import to enable mocking navigate and location
import * as router from 'react-router-dom';
import { authService } from '../../services/auth';

// Mock useLocation and Navigate
jest.spyOn(router, 'useLocation').mockImplementation(() => ({ 
  pathname: '/current',
  search: '',
  hash: '',
  state: null,
  key: 'default'
}));

// Mock Navigate component
jest.spyOn(router, 'Navigate').mockImplementation(({ to }: { to: string }) => (
  <div data-testid="navigate">Redirecting to {to}</div>
));

// Create a mock redux store
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: (state = { user: null, isLoading: false, isAuthenticated: false }, action) => state,
    },
    preloadedState: {
      auth: {
        user: null,
        isLoading: false,
        isAuthenticated: false,
        ...initialState,
      }
    }
  });
};

const renderWithProviders = (ui: React.ReactElement, initialState = {}) => {
  const store = createMockStore(initialState);
  return render(
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <MemoryRouter>
          {ui}
        </MemoryRouter>
      </ThemeProvider>
    </Provider>
  );
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should show loading state when authentication is in progress', () => {
    // Mock that we're validating the session
    (authService.isAuthenticated as jest.Mock).mockReturnValue(true);
    (authService.validateToken as jest.Mock).mockImplementation(() => {
      return new Promise(() => {
        // Never resolve to keep isValidating true
      });
    });

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>,
      { isLoading: true }
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should redirect to login page when user is not authenticated', () => {
    // Mock that we're not authenticated
    (authService.isAuthenticated as jest.Mock).mockReturnValue(false);

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>,
      { isAuthenticated: false }
    );

    expect(screen.getByTestId('navigate')).toHaveTextContent('Redirecting to /login');
  });

  it('should render protected content when user is authenticated', async () => {
    // Mock authenticated user with immediate resolution
    (authService.isAuthenticated as jest.Mock).mockReturnValue(true);
    (authService.validateToken as jest.Mock).mockResolvedValue(true);
    (authService.getCurrentUser as jest.Mock).mockReturnValue({
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'user'
    });

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>,
      { 
        isAuthenticated: true,
        user: {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          role: 'user'
        } 
      }
    );

    // Wait for validation to complete properly with waitFor
    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    }, { timeout: 1000 });
  });
}); 