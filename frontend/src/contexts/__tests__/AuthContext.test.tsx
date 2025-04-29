import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { sessionService } from '../../services/sessionService';
import { apiService } from '../../services/apiService';
import { renderWithProviders } from '../../utils/test-utils';
import { User, UserRole, SubscriptionTier } from '../../types/user';
import { AuthTokens } from '../../types/auth';
import { clearMockStorage } from '../../../tests/mocks/storage';

// Mock API service
jest.mock('../../services/apiService', () => ({
  apiService: {
    auth: {
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      validate: jest.fn()
    },
    profile: {
      update: jest.fn()
    }
  }
}));

// Mock session service
jest.mock('../../services/sessionService', () => ({
  sessionService: {
    getTokens: jest.fn(),
    setTokens: jest.fn(),
    clearTokens: jest.fn(),
    setSessionData: jest.fn(),
    getSessionData: jest.fn(),
    clearSession: jest.fn(),
    validateSession: jest.fn(),
    initActivityTracking: jest.fn()
  }
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock data
const mockUser: User = {
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user' as UserRole,
  isActive: true,
  isVerified: true,
  isEmailVerified: true,
  subscriptionTier: 'free' as SubscriptionTier,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z'
};

const mockTokens: AuthTokens = {
  accessToken: 'test-access-token',
  refreshToken: 'test-refresh-token',
  expiresIn: 3600
};

const mockNewTokens: AuthTokens = {
  accessToken: 'new-access-token',
  refreshToken: 'new-refresh-token',
  expiresIn: 3600
};

// Extended test component that uses AuthContext with more functionality
const TestComponent: React.FC = () => {
  const { 
    isAuthenticated, 
    isLoading, 
    user, 
    login, 
    register, 
    logout, 
    error 
  } = useAuth();

  return (
    <div>
      {isLoading && <div data-testid="loading">Loading...</div>}
      {!isLoading && !isAuthenticated && (
        <div>
          <div data-testid="login-state">Please login</div>
          <button 
            data-testid="login-button"
            onClick={() => login('test@example.com', 'password')}
          >
            Login
          </button>
          <button 
            data-testid="register-button"
            onClick={() => register('new@example.com', 'password', 'newuser')}
          >
            Register
          </button>
          {error && <div data-testid="error-message">{error}</div>}
        </div>
      )}
      {!isLoading && isAuthenticated && user && (
        <div>
          <div data-testid="authenticated-state">
            Welcome, {user.name}
          </div>
          <button data-testid="logout-button" onClick={logout}>
            Logout
          </button>
        </div>
      )}
    </div>
  );
};

// Render with the auth provider
const renderWithAuth = (preloadedState = {}) => {
  const result = renderWithProviders(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>,
    {
      preloadedState: {
        auth: {},
        formCheck: {},
        subscription: {},
        workout: {},
        formAnalysis: {},
        ...preloadedState
      }
    }
  );
  return result;
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    clearMockStorage();
  });

  it('should initialize with login state when no session exists', async () => {
    // Mock session validation to return false (no valid session)
    (sessionService.validateSession as jest.Mock).mockReturnValue(false);

    renderWithAuth();

    // Wait for the login state to appear (with a longer timeout)
    await waitFor(() => screen.getByTestId('login-state'), { timeout: 5000 });
    
    // Verify that session validation was called
    expect(sessionService.validateSession).toHaveBeenCalled();
    expect(sessionService.initActivityTracking).toHaveBeenCalled();
  });

  it('should show authenticated state when session is valid', async () => {
    // Mock session validation to return true (valid session)
    (sessionService.validateSession as jest.Mock).mockReturnValue(true);
    (sessionService.getTokens as jest.Mock).mockReturnValue(mockTokens);
    (apiService.auth.validate as jest.Mock).mockResolvedValue({ 
      data: mockUser,
      status: 200 
    });

    renderWithAuth();

    // After loading, it should show authenticated state
    await waitFor(() => screen.getByTestId('authenticated-state'), { timeout: 5000 });
    
    // Verify that validation API was called
    expect(apiService.auth.validate).toHaveBeenCalled();
    expect(screen.getByText(`Welcome, ${mockUser.name}`)).toBeInTheDocument();
  });

  it('should handle login successfully', async () => {
    // Mock successful login
    (apiService.auth.login as jest.Mock).mockResolvedValue({
      data: { user: mockUser, tokens: mockTokens },
      status: 200
    });

    renderWithAuth();

    // Wait for login state
    await waitFor(() => screen.getByTestId('login-state'));

    // Click login button
    fireEvent.click(screen.getByTestId('login-button'));

    // Wait for authenticated state
    await waitFor(() => screen.getByTestId('authenticated-state'));

    // Verify API calls and state updates
    expect(apiService.auth.login).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password'
    });
    expect(sessionService.setTokens).toHaveBeenCalledWith(mockTokens);
    expect(sessionService.setSessionData).toHaveBeenCalledWith({ user: mockUser });
    expect(screen.getByText(`Welcome, ${mockUser.name}`)).toBeInTheDocument();
  });

  it('should handle login failure', async () => {
    // Mock failed login
    (apiService.auth.login as jest.Mock).mockRejectedValue(new Error('Login failed'));

    renderWithAuth();

    // Wait for login state
    await waitFor(() => screen.getByTestId('login-state'));

    // Click login button
    fireEvent.click(screen.getByTestId('login-button'));

    // Wait for error message
    await waitFor(() => screen.getByTestId('error-message'));

    // Verify error state
    expect(screen.getByText('Login failed')).toBeInTheDocument();
  });

  it('should handle logout', async () => {
    // Start with authenticated state
    (sessionService.validateSession as jest.Mock).mockReturnValue(true);
    (sessionService.getTokens as jest.Mock).mockReturnValue(mockTokens);
    (apiService.auth.validate as jest.Mock).mockResolvedValue({ 
      data: mockUser,
      status: 200 
    });

    renderWithAuth();

    // Wait for authenticated state
    await waitFor(() => screen.getByTestId('authenticated-state'));

    // Click logout button
    fireEvent.click(screen.getByTestId('logout-button'));

    // Wait for login state
    await waitFor(() => screen.getByTestId('login-state'));

    // Verify session was cleared
    expect(sessionService.clearSession).toHaveBeenCalled();
  });

  it('should handle registration successfully', async () => {
    // Mock successful registration
    (apiService.auth.register as jest.Mock).mockResolvedValue({
      data: { user: mockUser, tokens: mockTokens },
      status: 200
    });

    renderWithAuth();

    // Wait for login state
    await waitFor(() => screen.getByTestId('login-state'));

    // Click register button
    fireEvent.click(screen.getByTestId('register-button'));

    // Wait for authenticated state
    await waitFor(() => screen.getByTestId('authenticated-state'));

    // Verify API calls and state updates
    expect(apiService.auth.register).toHaveBeenCalledWith({
      email: 'new@example.com',
      password: 'password',
      username: 'newuser'
    });
    expect(sessionService.setTokens).toHaveBeenCalledWith(mockTokens);
    expect(sessionService.setSessionData).toHaveBeenCalledWith({ user: mockUser });
    expect(screen.getByText(`Welcome, ${mockUser.name}`)).toBeInTheDocument();
  });

  it('should handle token refresh successfully', async () => {
    // Set up authenticated state
    (sessionService.validateSession as jest.Mock).mockReturnValue(true);
    (sessionService.getTokens as jest.Mock).mockReturnValue(mockTokens);
    (apiService.auth.validate as jest.Mock).mockResolvedValue({
      data: mockUser,
      status: 200
    });
    
    // Mock refresh token API
    (apiService.auth.refreshToken as jest.Mock).mockResolvedValue({
      data: { tokens: mockNewTokens },
      status: 200
    });

    const { getByTestId } = renderWithAuth();

    // Wait for authenticated state to appear
    await waitFor(() => getByTestId('authenticated-state'), { timeout: 5000 });

    // Perform token refresh
    await act(async () => {
      fireEvent.click(getByTestId('refresh-button'));
    });

    // Check that API and service methods were called
    expect(apiService.auth.refreshToken).toHaveBeenCalledWith(mockTokens.refreshToken);
    expect(sessionService.setTokens).toHaveBeenCalledWith(mockNewTokens);
  });

  it('should handle user profile update successfully', async () => {
    // Set up authenticated state
    (sessionService.validateSession as jest.Mock).mockReturnValue(true);
    (sessionService.getTokens as jest.Mock).mockReturnValue(mockTokens);
    (apiService.auth.validate as jest.Mock).mockResolvedValue({
      data: mockUser,
      status: 200
    });
    
    // Mock profile update API
    const updatedUser = { 
      ...mockUser, 
      firstName: 'Updated'
    };
    
    (apiService.profile.update as jest.Mock).mockResolvedValue({
      data: updatedUser,
      status: 200
    });
    
    (sessionService.getSessionData as jest.Mock).mockReturnValue({
      lastLogin: '2023-01-01T00:00:00Z'
    });

    const { getByTestId } = renderWithAuth();

    // Wait for authenticated state to appear
    await waitFor(() => getByTestId('authenticated-state'), { timeout: 5000 });

    // Perform profile update
    await act(async () => {
      fireEvent.click(getByTestId('update-user-button'));
    });

    // Check that API was called with correct data
    expect(apiService.profile.update).toHaveBeenCalledWith({ firstName: 'Updated' });
    
    // Check that session data was updated
    expect(sessionService.setSessionData).toHaveBeenCalledWith({
      lastLogin: '2023-01-01T00:00:00Z'
    });
    
    // Wait for updated welcome message
    await waitFor(() => {
      expect(screen.getByText(`Welcome, Updated ${mockUser.name}`)).toBeInTheDocument();
    }, { timeout: 5000 });
  });
});
