import React from 'react';
import { screen, render } from '@testing-library/react';
import { ProtectedRoute } from '../ProtectedRoute';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../theme';
import { MemoryRouter } from 'react-router-dom';

const TestComponent = () => <div>Protected Content</div>;

// Mock the useAuth hook
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Import to enable mocking navigate and location
import * as router from 'react-router-dom';

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

import { useAuth } from '../../contexts/AuthContext';

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter>
        {ui}
      </MemoryRouter>
    </ThemeProvider>
  );
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    (useAuth as jest.Mock).mockClear();
  });

  it('should show loading state when authentication is in progress', () => {
    (useAuth as jest.Mock).mockReturnValue({
      isLoading: true,
      isAuthenticated: false,
    });

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should redirect to login page when user is not authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({
      isLoading: false,
      isAuthenticated: false,
    });

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(screen.getByTestId('navigate')).toHaveTextContent('Redirecting to /login');
  });

  it('should render protected content when user is authenticated', () => {
    (useAuth as jest.Mock).mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
    });

    renderWithProviders(
      <ProtectedRoute>
        <TestComponent />
      </ProtectedRoute>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
}); 