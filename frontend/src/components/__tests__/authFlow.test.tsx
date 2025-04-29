import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../theme';
import Login from '../../pages/auth/Login';
import Register from '../../pages/auth/Register';
import { ProtectedRoute } from '../ProtectedRoute';
import { authService } from '../../services/auth';
import { User } from '../../types/user';

// Mock the auth service
jest.mock('../../services/auth', () => ({
  authService: {
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    isAuthenticated: jest.fn(),
    getCurrentUser: jest.fn(),
    validateToken: jest.fn(),
  },
}));

// Mock the router hooks
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

const mockUser: User = {
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  subscriptionTier: 'free',
  isActive: true,
  isVerified: true,
  isEmailVerified: true,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z',
};

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
      },
    },
  });
};

// Test component for protected route
const ProtectedComponent = () => <div>Protected Content</div>;

describe('Authentication Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should complete the full authentication flow', async () => {
    // Setup initial state
    const store = createMockStore();
    
    // Mock successful registration
    (authService.register as jest.Mock).mockResolvedValueOnce({
      success: true,
      user: mockUser,
    });

    // Mock successful login
    (authService.login as jest.Mock).mockResolvedValueOnce({
      success: true,
      user: mockUser,
      token: 'mock-token',
    });

    // Mock authentication checks
    (authService.isAuthenticated as jest.Mock).mockReturnValue(true);
    (authService.getCurrentUser as jest.Mock).mockResolvedValue(mockUser);
    (authService.validateToken as jest.Mock).mockResolvedValue(true);

    // Render the app with routes
    render(
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={['/register']}>
            <Routes>
              <Route path="/register" element={<Register />} />
              <Route path="/login" element={<Login />} />
              <Route
                path="/protected"
                element={
                  <ProtectedRoute>
                    <ProtectedComponent />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </Provider>
    );

    // 1. Register a new user
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const nameInput = screen.getByLabelText(/name/i);
    const registerButton = screen.getByRole('button', { name: /register/i });

    await act(async () => {
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.change(nameInput, { target: { value: 'Test User' } });
      fireEvent.click(registerButton);
    });

    // Verify registration was successful
    await waitFor(() => {
      expect(authService.register).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User',
      });
    });

    // 2. Login with the registered user
    const loginEmailInput = screen.getByLabelText(/email/i);
    const loginPasswordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await act(async () => {
      fireEvent.change(loginEmailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(loginPasswordInput, { target: { value: 'password123' } });
      fireEvent.click(loginButton);
    });

    // Verify login was successful
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      });
    });

    // 3. Access protected route
    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument();
    });

    // 4. Logout
    const logoutButton = screen.getByRole('button', { name: /logout/i });
    await act(async () => {
      fireEvent.click(logoutButton);
    });

    // Verify logout was successful
    await waitFor(() => {
      expect(authService.logout).toHaveBeenCalled();
    });

    // 5. Verify protected route is no longer accessible
    await waitFor(() => {
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });

  it('should handle registration validation errors', async () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={['/register']}>
            <Routes>
              <Route path="/register" element={<Register />} />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </Provider>
    );

    // Try to register with invalid data
    const registerButton = screen.getByRole('button', { name: /register/i });
    await act(async () => {
      fireEvent.click(registerButton);
    });

    // Verify validation errors are displayed
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    });
  });

  it('should handle login validation errors', async () => {
    const store = createMockStore();

    render(
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={['/login']}>
            <Routes>
              <Route path="/login" element={<Login />} />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </Provider>
    );

    // Try to login with invalid data
    const loginButton = screen.getByRole('button', { name: /login/i });
    await act(async () => {
      fireEvent.click(loginButton);
    });

    // Verify validation errors are displayed
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('should handle authentication errors', async () => {
    const store = createMockStore();

    // Mock failed login
    (authService.login as jest.Mock).mockRejectedValueOnce(new Error('Invalid credentials'));

    render(
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={['/login']}>
            <Routes>
              <Route path="/login" element={<Login />} />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </Provider>
    );

    // Try to login with valid data
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    await act(async () => {
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } });
      fireEvent.click(loginButton);
    });

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it('should handle token expiration', async () => {
    const store = createMockStore({
      user: mockUser,
      isAuthenticated: true,
    });

    // Mock token validation failure
    (authService.validateToken as jest.Mock).mockResolvedValueOnce(false);
    (authService.isAuthenticated as jest.Mock).mockReturnValueOnce(true);

    render(
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={['/protected']}>
            <Routes>
              <Route
                path="/protected"
                element={
                  <ProtectedRoute>
                    <ProtectedComponent />
                  </ProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </Provider>
    );

    // Verify user is redirected to login
    await waitFor(() => {
      expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
    });
  });
}); 