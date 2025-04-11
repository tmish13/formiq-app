import React from 'react';
import { screen, render } from '@testing-library/react';
import { BrowserRouter, useLocation, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../ProtectedRoute';
import { AuthProvider } from '../../contexts/AuthContext';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../theme';

const TestComponent = () => <div>Protected Content</div>;

// Mock the useAuth hook
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: jest.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock react-router-dom hooks
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useLocation: jest.fn(),
  Navigate: jest.fn(({ to }) => <div data-testid="navigate">Redirecting to {to}</div>),
}));

import { useAuth } from '../../contexts/AuthContext';

const renderWithProviders = (ui: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      <BrowserRouter>
        <AuthProvider>
          {ui}
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
};

describe('ProtectedRoute', () => {
  beforeEach(() => {
    (useAuth as jest.Mock).mockClear();
    (useLocation as jest.Mock).mockReturnValue({ pathname: '/current' });
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