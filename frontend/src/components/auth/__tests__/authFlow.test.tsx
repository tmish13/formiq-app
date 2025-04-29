import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from '../../../contexts/AuthContext';
import Login from '../../../pages/auth/Login';
import Register from '../../../pages/auth/Register';
import { ProtectedRoute } from '../../ProtectedRoute';
import { apiService } from '../../../services/apiService';
import { testRender } from '../../../test-utils';

// Mock API service
jest.mock('../../../services/apiService', () => ({
  apiService: {
    auth: {
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      validate: jest.fn()
    }
  }
}));

// Mock protected component
const ProtectedComponent = () => <div>Protected Content</div>;

const TestApp = () => (
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

    testRender(<TestApp />, { initialRoute: '/login' });

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

    testRender(<TestApp />, { initialRoute: '/protected' });

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

    testRender(<TestApp />, { initialRoute: '/login' });

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
    testRender(<TestApp />, { initialRoute: '/register' });

    // Submit empty form
    fireEvent.click(screen.getByText(/Sign up/i));

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText(/Email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Password is required/i)).toBeInTheDocument();
    });

    // Fill with invalid email
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'invalid-email' }
    });

    // Should show email validation error
    await waitFor(() => {
      expect(screen.getByText(/Invalid email format/i)).toBeInTheDocument();
    });

    // Fill with mismatched passwords
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), {
      target: { value: 'password456' }
    });

    // Should show password mismatch error
    await waitFor(() => {
      expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
    });
  });

  it('handles logout correctly', async () => {
    // Mock successful login
    (apiService.auth.login as jest.Mock).mockResolvedValueOnce({
      user: { id: '1', email: 'test@example.com' },
      tokens: { access: 'access-token', refresh: 'refresh-token' }
    });

    const { store } = testRender(<TestApp />, { initialRoute: '/login' });

    // Login
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@example.com' }
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'password123' }
    });
    fireEvent.click(screen.getByText(/Sign in/i));

    // Wait for protected content
    await waitFor(() => {
      expect(screen.getByText(/Protected Content/i)).toBeInTheDocument();
    });

    // Mock successful logout
    (apiService.auth.logout as jest.Mock).mockResolvedValueOnce({});

    // Click logout button
    fireEvent.click(screen.getByText(/Logout/i));

    // Should be redirected to login
    await waitFor(() => {
      expect(screen.getByText(/Sign in/i)).toBeInTheDocument();
    });

    // Verify auth state is cleared
    expect(store.getState().auth.user).toBeNull();
  });
}); 