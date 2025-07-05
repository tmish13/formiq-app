/**
 * Integration Test: Authentication Flow with JWT Token Refresh
 * 
 * Tests the complete authentication system including login, logout,
 * token refresh, and session persistence across app restarts.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IntegrationTestUtils, config } from '../setup';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { store } from '../../../src/store';
import { ThemeProvider } from '../../../src/contexts/ThemeContext';
import LoginPage from '../../../src/pages/auth/LoginPage';
import RegisterPage from '../../../src/pages/auth/RegisterPage';
import DashboardPage from '../../../src/pages/dashboard/DashboardPage';
import { authSlice } from '../../../src/store/slices/authSlice';
import * as authService from '../../../src/services/apiService';

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Provider store={store}>
    <BrowserRouter>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </BrowserRouter>
  </Provider>
);

describe('Authentication Flow Integration Tests', () => {
  const mockCredentials = {
    email: config.auth.mockCredentials.username,
    password: config.auth.mockCredentials.password,
  };

  beforeEach(() => {
    // Clear authentication state before each test
    store.dispatch(authSlice.actions.logout());
    localStorage.clear();
    sessionStorage.clear();
    
    // Mock API calls if not using real backend
    if (!config.backend.enableRealApi) {
      jest.spyOn(authService, 'login').mockResolvedValue({
        success: true,
        data: {
          access_token: 'mock_access_token_12345',
          refresh_token: 'mock_refresh_token_67890',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: 'user-123',
            email: mockCredentials.email,
            first_name: 'Test',
            last_name: 'User',
            subscription_plan: 'premium',
            email_verified: true,
          },
        },
      });

      jest.spyOn(authService, 'refreshToken').mockResolvedValue({
        success: true,
        data: {
          access_token: 'new_mock_access_token_54321',
          expires_in: 3600,
        },
      });

      jest.spyOn(authService, 'logout').mockResolvedValue({
        success: true,
        data: { message: 'Logged out successfully' },
      });

      jest.spyOn(authService, 'register').mockResolvedValue({
        success: true,
        data: {
          user: {
            id: 'new-user-456',
            email: 'newuser@formiq.com',
            first_name: 'New',
            last_name: 'User',
          },
          message: 'Registration successful. Please verify your email.',
        },
      });
    }
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Login Flow', () => {
    it('should successfully log in with valid credentials', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      );

      // Verify login form is displayed
      expect(screen.getByRole('heading', { name: /login|sign in/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();

      // Fill in credentials
      await user.type(screen.getByLabelText(/email/i), mockCredentials.email);
      await user.type(screen.getByLabelText(/password/i), mockCredentials.password);

      // Submit login form
      const loginButton = screen.getByRole('button', { name: /login|sign in/i });
      await user.click(loginButton);

      // Verify loading state
      await waitFor(() => {
        expect(screen.getByText(/logging in|signing in/i)).toBeInTheDocument();
      });

      // Verify successful login
      await waitFor(() => {
        // Check if redirected to dashboard or success message
        const dashboardElement = screen.queryByText(/dashboard|welcome/i);
        const successMessage = screen.queryByText(/login successful|welcome back/i);
        
        expect(dashboardElement || successMessage).toBeInTheDocument();
      });

      // Verify authentication state in Redux store
      const authState = store.getState().auth;
      expect(authState.isAuthenticated).toBe(true);
      expect(authState.user).toBeTruthy();
      expect(authState.user?.email).toBe(mockCredentials.email);
      expect(authState.accessToken).toBeTruthy();
    });

    it('should handle login errors appropriately', async () => {
      const user = userEvent.setup();
      
      // Mock login failure
      if (!config.backend.enableRealApi) {
        jest.spyOn(authService, 'login').mockRejectedValue({
          error: {
            status: 401,
            message: 'Invalid email or password',
          },
        });
      }

      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      );

      // Fill in invalid credentials
      await user.type(screen.getByLabelText(/email/i), 'invalid@email.com');
      await user.type(screen.getByLabelText(/password/i), 'wrongpassword');

      // Submit login form
      const loginButton = screen.getByRole('button', { name: /login|sign in/i });
      await user.click(loginButton);

      // Verify error message is displayed
      await waitFor(() => {
        expect(screen.getByText(/invalid.*email.*password|login failed/i)).toBeInTheDocument();
      });

      // Verify authentication state remains false
      const authState = store.getState().auth;
      expect(authState.isAuthenticated).toBe(false);
      expect(authState.user).toBeNull();
    });

    it('should validate form fields', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <LoginPage />
        </TestWrapper>
      );

      // Try to submit empty form
      const loginButton = screen.getByRole('button', { name: /login|sign in/i });
      await user.click(loginButton);

      // Verify validation errors
      await waitFor(() => {
        expect(screen.getByText(/email.*required|please enter.*email/i)).toBeInTheDocument();
        expect(screen.getByText(/password.*required|please enter.*password/i)).toBeInTheDocument();
      });

      // Test invalid email format
      await user.type(screen.getByLabelText(/email/i), 'invalid-email');
      await user.click(loginButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid.*email.*format|please enter.*valid.*email/i)).toBeInTheDocument();
      });
    });
  });

  describe('Registration Flow', () => {
    it('should successfully register a new user', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <RegisterPage />
        </TestWrapper>
      );

      // Verify registration form is displayed
      expect(screen.getByRole('heading', { name: /register|sign up|create account/i })).toBeInTheDocument();

      // Fill in registration form
      await user.type(screen.getByLabelText(/first.*name/i), 'New');
      await user.type(screen.getByLabelText(/last.*name/i), 'User');
      await user.type(screen.getByLabelText(/email/i), 'newuser@formiq.com');
      await user.type(screen.getByLabelText(/^password/i), 'NewPassword123!');
      await user.type(screen.getByLabelText(/confirm.*password/i), 'NewPassword123!');

      // Accept terms if required
      const termsCheckbox = screen.queryByLabelText(/terms|privacy/i);
      if (termsCheckbox) {
        await user.click(termsCheckbox);
      }

      // Submit registration form
      const registerButton = screen.getByRole('button', { name: /register|sign up|create account/i });
      await user.click(registerButton);

      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/registration successful|account created/i)).toBeInTheDocument();
        expect(screen.getByText(/verify.*email|check.*email/i)).toBeInTheDocument();
      });
    });

    it('should validate password requirements', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <RegisterPage />
        </TestWrapper>
      );

      // Test weak password
      await user.type(screen.getByLabelText(/^password/i), 'weak');
      await user.type(screen.getByLabelText(/confirm.*password/i), 'weak');

      const registerButton = screen.getByRole('button', { name: /register|sign up|create account/i });
      await user.click(registerButton);

      await waitFor(() => {
        expect(screen.getByText(/password.*requirements|password.*weak/i)).toBeInTheDocument();
      });

      // Test password mismatch
      await user.clear(screen.getByLabelText(/^password/i));
      await user.clear(screen.getByLabelText(/confirm.*password/i));
      await user.type(screen.getByLabelText(/^password/i), 'StrongPassword123!');
      await user.type(screen.getByLabelText(/confirm.*password/i), 'DifferentPassword123!');

      await user.click(registerButton);

      await waitFor(() => {
        expect(screen.getByText(/passwords.*match|passwords.*same/i)).toBeInTheDocument();
      });
    });
  });

  describe('Token Refresh Mechanism', () => {
    it('should automatically refresh expired tokens', async () => {
      // Setup authenticated state with expired token
      const expiredToken = 'expired_token_12345';
      const mockUser = {
        id: 'user-123',
        email: mockCredentials.email,
        first_name: 'Test',
        last_name: 'User',
      };

      store.dispatch(authSlice.actions.loginSuccess({
        user: mockUser,
        accessToken: expiredToken,
        refreshToken: 'valid_refresh_token',
      }));

      // Mock API call that would trigger token refresh
      if (!config.backend.enableRealApi) {
        jest.spyOn(authService, 'getUserProfile').mockRejectedValueOnce({
          error: { status: 401, message: 'Token expired' },
        }).mockResolvedValueOnce({
          success: true,
          data: mockUser,
        });
      }

      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Wait for automatic token refresh
      await waitFor(
        () => {
          const authState = store.getState().auth;
          expect(authState.accessToken).not.toBe(expiredToken);
          expect(authState.accessToken).toBe('new_mock_access_token_54321');
        },
        { timeout: 5000 }
      );

      // Verify user remains authenticated
      const finalAuthState = store.getState().auth;
      expect(finalAuthState.isAuthenticated).toBe(true);
      expect(finalAuthState.user).toEqual(mockUser);
    });

    it('should logout user when refresh token is invalid', async () => {
      // Setup authenticated state
      store.dispatch(authSlice.actions.loginSuccess({
        user: {
          id: 'user-123',
          email: mockCredentials.email,
          first_name: 'Test',
          last_name: 'User',
        },
        accessToken: 'expired_token',
        refreshToken: 'invalid_refresh_token',
      }));

      // Mock failed token refresh
      if (!config.backend.enableRealApi) {
        jest.spyOn(authService, 'refreshToken').mockRejectedValue({
          error: { status: 401, message: 'Invalid refresh token' },
        });

        jest.spyOn(authService, 'getUserProfile').mockRejectedValue({
          error: { status: 401, message: 'Token expired' },
        });
      }

      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Wait for automatic logout
      await waitFor(
        () => {
          const authState = store.getState().auth;
          expect(authState.isAuthenticated).toBe(false);
          expect(authState.user).toBeNull();
        },
        { timeout: 5000 }
      );

      // Verify user is redirected to login
      await waitFor(() => {
        expect(screen.getByText(/login|sign in/i)).toBeInTheDocument();
      });
    });
  });

  describe('Session Persistence', () => {
    it('should persist authentication state across page reloads', async () => {
      const mockUser = {
        id: 'user-123',
        email: mockCredentials.email,
        first_name: 'Test',
        last_name: 'User',
      };

      // Simulate authenticated state with localStorage
      const authData = {
        user: mockUser,
        accessToken: 'valid_token_12345',
        refreshToken: 'valid_refresh_token',
        isAuthenticated: true,
      };

      localStorage.setItem('auth', JSON.stringify(authData));

      // Simulate app restart by creating new store instance
      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Wait for state restoration
      await waitFor(() => {
        const authState = store.getState().auth;
        expect(authState.isAuthenticated).toBe(true);
        expect(authState.user).toEqual(mockUser);
      });
    });

    it('should clear persisted state on logout', async () => {
      const user = userEvent.setup();
      
      // Setup authenticated state
      store.dispatch(authSlice.actions.loginSuccess({
        user: {
          id: 'user-123',
          email: mockCredentials.email,
          first_name: 'Test',
          last_name: 'User',
        },
        accessToken: 'valid_token',
        refreshToken: 'valid_refresh_token',
      }));

      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Find and click logout button
      const logoutButton = screen.getByRole('button', { name: /logout|sign out/i });
      await user.click(logoutButton);

      // Verify logout confirmation if present
      const confirmLogout = screen.queryByRole('button', { name: /confirm|yes/i });
      if (confirmLogout) {
        await user.click(confirmLogout);
      }

      // Wait for logout completion
      await waitFor(() => {
        const authState = store.getState().auth;
        expect(authState.isAuthenticated).toBe(false);
        expect(authState.user).toBeNull();
      });

      // Verify localStorage is cleared
      const storedAuth = localStorage.getItem('auth');
      expect(storedAuth).toBeNull();

      // Verify redirect to login page
      await waitFor(() => {
        expect(screen.getByText(/login|sign in/i)).toBeInTheDocument();
      });
    });
  });

  describe('Protected Route Access', () => {
    it('should redirect unauthenticated users to login', async () => {
      // Ensure user is not authenticated
      store.dispatch(authSlice.actions.logout());

      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Verify redirect to login page
      await waitFor(() => {
        expect(screen.getByText(/login|sign in/i)).toBeInTheDocument();
      });
    });

    it('should allow authenticated users to access protected routes', async () => {
      // Setup authenticated state
      store.dispatch(authSlice.actions.loginSuccess({
        user: {
          id: 'user-123',
          email: mockCredentials.email,
          first_name: 'Test',
          last_name: 'User',
        },
        accessToken: 'valid_token',
        refreshToken: 'valid_refresh_token',
      }));

      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Verify dashboard content is displayed
      await waitFor(() => {
        expect(screen.getByText(/dashboard|welcome/i)).toBeInTheDocument();
      });
    });
  });

  describe('Real-time Authentication Status', () => {
    it('should handle concurrent session expiry across tabs', async () => {
      // Setup authenticated state
      store.dispatch(authSlice.actions.loginSuccess({
        user: {
          id: 'user-123',
          email: mockCredentials.email,
          first_name: 'Test',
          last_name: 'User',
        },
        accessToken: 'valid_token',
        refreshToken: 'valid_refresh_token',
      }));

      render(
        <TestWrapper>
          <DashboardPage />
        </TestWrapper>
      );

      // Simulate logout from another tab
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'auth',
        newValue: null,
        oldValue: JSON.stringify({ isAuthenticated: true }),
      }));

      // Verify automatic logout in current tab
      await waitFor(() => {
        const authState = store.getState().auth;
        expect(authState.isAuthenticated).toBe(false);
      });

      // Verify redirect to login
      await waitFor(() => {
        expect(screen.getByText(/login|sign in/i)).toBeInTheDocument();
      });
    });
  });
});