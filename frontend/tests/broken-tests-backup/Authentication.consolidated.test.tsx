/**
 * Consolidated Tests for Authentication
 * 
 * This file tests authentication flows including:
 * 1. User registration
 * 2. User login
 * 3. Password reset
 * 4. Authentication guards
 * 5. Token management
 * 
 * Tests use a behavior-driven style focusing on user interactions
 * rather than implementation details.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import '@testing-library/jest-dom';

// Import shared mocks from utilities
import {
  http,
  HttpResponse,
  mockAuthService,
  setupMockServer,
  setupLocalStorageMock,
  createMockUser
} from '../utils/sharedMocks';

// Import components and services
import LoginForm from '../../src/components/auth/LoginForm';
import RegisterForm from '../../src/components/auth/RegisterForm';
import ResetPasswordForm from '../../src/components/auth/ResetPasswordForm';
// Note: AuthGuard and AuthProvider don't exist - using mocks instead

// Mock Material UI components
jest.mock('@mui/material', () => {
  const actual = jest.requireActual('@mui/material');
  return {
    ...actual,
    CircularProgress: () => <div data-testid="loading-spinner">Loading...</div>,
    TextField: ({ label, type, name, value, onChange, error, helperText, ...props }) => (
      <div>
        <label htmlFor={name}>{label}</label>
        <input
          id={name}
          name={name}
          type={type || 'text'}
          value={value}
          onChange={onChange}
          data-testid={name}
          {...props}
        />
        {error && <span data-testid={`${name}-error`}>{helperText}</span>}
      </div>
    ),
    Button: ({ children, onClick, type, disabled, ...props }) => (
      <button 
        onClick={onClick}
        type={type}
        disabled={disabled} 
        data-testid={props['data-testid'] || 'button'}
      >
        {children}
      </button>
    ),
    Alert: ({ severity, children }) => (
      <div data-testid={`alert-${severity}`}>{children}</div>
    ),
  };
});

// Mock React Router DOM
jest.mock('react-router-dom', () => {
  const originalModule = jest.requireActual('react-router-dom');
  
  return {
    ...originalModule,
    useNavigate: () => jest.fn(),
  };
});

// Setup mock server
const server = setupMockServer([
  // Login endpoint
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json();
    
    if (body.email === 'test@example.com' && body.password === 'password123') {
      return HttpResponse.json({
        user: createMockUser(),
        tokens: {
          accessToken: 'mock-token-123',
          refreshToken: 'mock-refresh-token-123'
        }
      });
    }
    
    return new HttpResponse(
      JSON.stringify({ message: 'Invalid credentials' }),
      { status: 401 }
    );
  }),
  
  // Register endpoint
  http.post('/api/auth/register', async ({ request }) => {
    const body = await request.json();
    
    if (!body.email || !body.password) {
      return new HttpResponse(
        JSON.stringify({ message: 'Email and password are required' }),
        { status: 400 }
      );
    }
    
    return HttpResponse.json(
      {
        user: createMockUser({ 
          id: 'new-user-123',
          email: body.email
        }),
        tokens: {
          accessToken: 'new-user-token-123',
          refreshToken: 'new-user-refresh-token-123'
        }
      },
      { status: 201 }
    );
  }),
  
  // Reset password endpoints
  http.post('/api/auth/forgot-password', async ({ request }) => {
    const body = await request.json();
    
    if (!body.email) {
      return new HttpResponse(
        JSON.stringify({ message: 'Email is required' }),
        { status: 400 }
      );
    }
    
    return HttpResponse.json({ message: 'Password reset email sent' });
  }),
  
  http.post('/api/auth/reset-password', async ({ request }) => {
    const body = await request.json();
    
    if (!body.token || !body.password) {
      return new HttpResponse(
        JSON.stringify({ message: 'Token and password are required' }),
        { status: 400 }
      );
    }
    
    return HttpResponse.json({ message: 'Password reset successful' });
  }),
  
  // Protected endpoint
  http.get('/api/user/profile', ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return new HttpResponse(null, { status: 401 });
    }
    
    return HttpResponse.json(createMockUser());
  })
]);

// Setup mock localStorage
const localStorageMock = setupLocalStorageMock();

// Test components
const Dashboard = () => <div data-testid="dashboard">Dashboard Content</div>;
const LoginPage = () => <LoginForm />;
const RegisterPage = () => <RegisterForm />;
const PublicPage = () => <div data-testid="public-page">Public Content</div>;

// Protected route with auth guard
const ProtectedApp = () => (
  <AuthProvider>
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/public" element={<PublicPage />} />
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <Dashboard />
            </AuthGuard>
          }
        />
      </Routes>
    </MemoryRouter>
  </AuthProvider>
);

// Helper to render components with auth provider
const renderWithAuth = (ui) => {
  return render(
    <AuthProvider>
      {ui}
    </AuthProvider>
  );
};

describe('Authentication Flows', () => {
  // Clear localStorage between tests
    beforeEach(() => {
    localStorageMock.clear();
  });
  
  // =========================================
  // Login Flow
  // =========================================
  describe('Login Flow', () => {
    it('WHEN a user enters valid credentials THEN they are logged in successfully', async () => {
      const user = userEvent.setup();
      renderWithAuth(<LoginForm />);
      
      // Fill out the login form
      await user.type(screen.getByTestId('email'), 'test@example.com');
      await user.type(screen.getByTestId('password'), 'password123');
      await user.click(screen.getByTestId('login-button'));
      
      // Verify success state
      await waitFor(() => {
        expect(screen.getByTestId('alert-success')).toBeInTheDocument();
      });
      
      // Verify token was stored in localStorage
      expect(localStorageMock.getItem('auth_token')).toBeTruthy();
    });
    
    it('WHEN a user enters invalid credentials THEN they see an error message', async () => {
      const user = userEvent.setup();
      renderWithAuth(<LoginForm />);
      
      // Fill out the login form with invalid password
      await user.type(screen.getByTestId('email'), 'test@example.com');
      await user.type(screen.getByTestId('password'), 'wrong-password');
      await user.click(screen.getByTestId('login-button'));
      
      // Verify error state
      await waitFor(() => {
        expect(screen.getByTestId('alert-error')).toBeInTheDocument();
      });
      
      // Verify no token was stored
      expect(localStorageMock.getItem('auth_token')).toBeFalsy();
    });
    
    it('WHEN login form has empty fields THEN submit button is disabled', async () => {
      renderWithAuth(<LoginForm />);
      
      // Verify button is initially disabled
      expect(screen.getByTestId('login-button')).toBeDisabled();
    });
  });
  
  // =========================================
  // Registration Flow
  // =========================================
  describe('Registration Flow', () => {
    it('WHEN a user registers with valid information THEN an account is created', async () => {
      const user = userEvent.setup();
      renderWithAuth(<RegisterForm />);
      
      // Fill out registration form
      await user.type(screen.getByTestId('name'), 'Test User');
      await user.type(screen.getByTestId('email'), 'newuser@example.com');
      await user.type(screen.getByTestId('password'), 'password123');
      await user.type(screen.getByTestId('confirmPassword'), 'password123');
      await user.click(screen.getByTestId('register-button'));
      
      // Verify success state
      await waitFor(() => {
        expect(screen.getByTestId('alert-success')).toBeInTheDocument();
      });
    });

    it('WHEN passwords do not match THEN an error message is shown', async () => {
      const user = userEvent.setup();
      renderWithAuth(<RegisterForm />);
      
      // Fill out form with mismatched passwords
      await user.type(screen.getByTestId('name'), 'Test User');
      await user.type(screen.getByTestId('email'), 'newuser@example.com');
      await user.type(screen.getByTestId('password'), 'password123');
      await user.type(screen.getByTestId('confirmPassword'), 'different-password');
      
      // Attempt to submit form
      await user.click(screen.getByTestId('register-button'));
      
      // Verify validation error
      expect(screen.getByTestId('confirmPassword-error')).toBeInTheDocument();
    });
  });
  
  // =========================================
  // Password Reset Flow
  // =========================================
  describe('Password Reset Flow', () => {
    it('WHEN a user requests a password reset THEN they receive a confirmation', async () => {
      const user = userEvent.setup();
      renderWithAuth(<ResetPasswordForm />);
      
      // Enter email for password reset
      await user.type(screen.getByTestId('email'), 'test@example.com');
      await user.click(screen.getByTestId('reset-button'));
      
      // Verify success message
      await waitFor(() => {
        expect(screen.getByTestId('alert-success')).toBeInTheDocument();
      });
    });
  });

  // =========================================
  // Authentication Guard
  // =========================================
  describe('Authentication Guard', () => {
    it('WHEN an authenticated user accesses a protected route THEN they see the content', async () => {
      // Pre-set token in localStorage to simulate logged-in state
      localStorageMock.setItem('auth_token', 'mock-token-123');
      
      render(<ProtectedApp />);
      
      // Verify user can access dashboard
      await waitFor(() => {
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
      });
    });
    
    it('WHEN an unauthenticated user tries to access a protected route THEN they are redirected to login', async () => {
      render(<ProtectedApp />);
      
      // Verify user is redirected to login page
      await waitFor(() => {
        expect(screen.getByTestId('login-button')).toBeInTheDocument();
      });
    });
  });
}); 