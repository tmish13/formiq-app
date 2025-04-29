import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from 'styled-components';
import { AuthProvider } from '../../../contexts/AuthContext';
import Login from "../Login";
import Register from "../Register";
import { ProtectedRoute } from '../../../components/ProtectedRoute';
import { apiService } from '../../../services/apiService';
import { mockTheme } from '../../../theme/mockTheme';

// Create a proper mock theme that matches DefaultTheme
const testTheme = {
  ...mockTheme,
  transitions: {
    duration: {
      shortest: '150ms',
      shorter: '200ms',
      short: '250ms',
      standard: '300ms',
      complex: '375ms',
      enteringScreen: '225ms',
      leavingScreen: '195ms',
      medium: '300ms'
    },
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)'
    }
  }
};

// Mock API service
jest.mock('../../../services/apiService', () => ({
  apiService: {
    auth: {
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      validate: jest.fn(),
      refreshToken: jest.fn()
    }
  }
}));

// Mock protected component
const ProtectedComponent = () => <div>Protected Content</div>;

const TestApp = () => (
  <BrowserRouter>
    <ThemeProvider theme={testTheme}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <ProtectedComponent />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Navigate to="/login" />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  </BrowserRouter>
);

describe('Authentication Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('completes full registration and login flow', async () => {
    // Mock successful registration
    (apiService.auth.register as jest.Mock).mockResolvedValueOnce({
      user: { id: '1', email: 'test@example.com' },
      tokens: { access: 'access-token', refresh: 'refresh-token' }
    });

    render(<TestApp />);

    // Should start at login page
    expect(screen.getByText(/Sign in/i)).toBeInTheDocument();

    // Navigate to register
    fireEvent.click(screen.getByText(/Create an account/i));

    // Fill registration form
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), {
      target: { value: 'password123' }
    });

    // Submit registration
    fireEvent.click(screen.getByText(/Sign up/i));

    // Wait for registration success
    await waitFor(() => {
      expect(apiService.auth.register).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123'
      });
    });

    // Mock successful login
    (apiService.auth.login as jest.Mock).mockResolvedValueOnce({
      user: { id: '1', email: 'test@example.com' },
      tokens: { access: 'access-token', refresh: 'refresh-token' }
    });

    // Should be redirected to login
    await waitFor(() => {
      expect(screen.getByText(/Sign in/i)).toBeInTheDocument();
    });

    // Fill login form
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });

    // Submit login
    fireEvent.click(screen.getByText(/Sign in/i));

    // Wait for login success and protected route access
    await waitFor(() => {
      expect(apiService.auth.login).toHaveBeenCalledWith(
        'test@example.com',
        'password123'
      );
      expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
    });
  });

  it('prevents access to protected routes when not authenticated', async () => {
    // Mock failed validation
    (apiService.auth.validate as jest.Mock).mockRejectedValueOnce(
      new Error('Not authenticated')
    );

    render(<TestApp />);

    // Try to access protected route
    window.history.pushState({}, '', '/protected');

    // Should be redirected to login
    await waitFor(() => {
      expect(screen.getByText(/Sign in/i)).toBeInTheDocument();
    });
  });

  it('handles login errors correctly', async () => {
    // Mock failed login
    (apiService.auth.login as jest.Mock).mockRejectedValueOnce(
      new Error('Invalid credentials')
    );

    render(<TestApp />);

    // Fill login form
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'wrongpassword' }
    });

    // Submit login
    fireEvent.click(screen.getByText(/Sign in/i));

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('handles registration validation errors', async () => {
    render(<TestApp />);

    // Navigate to register
    fireEvent.click(screen.getByText(/Create an account/i));

    // Submit empty form
    fireEvent.click(screen.getByText(/Sign up/i));

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('handles token expiration and refresh', async () => {
    // Mock successful login
    (apiService.auth.login as jest.Mock).mockResolvedValueOnce({
      user: { id: '1', email: 'test@example.com' },
      tokens: { access: 'access-token', refresh: 'refresh-token' }
    });
    
    // Mock token validation to fail
    (apiService.auth.validate as jest.Mock).mockRejectedValueOnce(
      new Error('Token expired')
    );
    
    // Mock token refresh to succeed
    (apiService.auth.refreshToken as jest.Mock).mockResolvedValueOnce({
      tokens: { access: 'new-access-token', refresh: 'new-refresh-token' }
    });
    
    render(<TestApp />);
    
    // Login
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText(/Sign in/i));
    
    // Wait for login success
    await waitFor(() => {
      expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
    });
    
    // Simulate token expiration
    window.dispatchEvent(new Event('storage'));
    
    // Should refresh token and maintain session
    await waitFor(() => {
      expect(apiService.auth.refreshToken).toHaveBeenCalledWith('refresh-token');
      expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
    });
  });

  it('handles session timeout due to inactivity', async () => {
    // Mock successful login
    (apiService.auth.login as jest.Mock).mockResolvedValueOnce({
      user: { id: '1', email: 'test@example.com' },
      tokens: { access: 'access-token', refresh: 'refresh-token' }
    });
    
    render(<TestApp />);
    
    // Login
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText(/Sign in/i));
    
    // Wait for login success
    await waitFor(() => {
      expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
    });
    
    // Simulate inactivity timeout
    jest.advanceTimersByTime(31 * 60 * 1000); // 31 minutes
    
    // Should be redirected to login
    await waitFor(() => {
      expect(screen.getByText(/Sign in/i)).toBeInTheDocument();
    });
  });

  it('handles logout correctly', async () => {
    // Mock successful login
    (apiService.auth.login as jest.Mock).mockResolvedValueOnce({
      user: { id: '1', email: 'test@example.com' },
      tokens: { access: 'access-token', refresh: 'refresh-token' }
    });
    
    // Mock successful logout
    (apiService.auth.logout as jest.Mock).mockResolvedValueOnce({});
    
    render(<TestApp />);
    
    // Login
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText(/Sign in/i));
    
    // Wait for login success
    await waitFor(() => {
      expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
    });
    
    // Logout
    fireEvent.click(screen.getByText(/Logout/i));
    
    // Should be redirected to login
    await waitFor(() => {
      expect(screen.getByText(/Sign in/i)).toBeInTheDocument();
      expect(apiService.auth.logout).toHaveBeenCalled();
    });
  });
}); 