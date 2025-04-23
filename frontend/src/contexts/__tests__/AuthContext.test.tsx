import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../AuthContext';
import { sessionService } from '../../services/sessionService';
import { apiService } from '../../services/apiService';
import { testRender as render } from '../../../tests/utils/testRender';
import { User, LoginCredentials, AuthTokens, RegisterCredentials } from '../../types/auth';
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
  username: 'testuser',
  firstName: 'Test',
  lastName: 'User',
  roles: ['user'],
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
    error, 
    refreshTokens,
    updateUser 
  } = useAuth();

  return (
    <div>
      {isLoading && <div data-testid="loading">Loading...</div>}
      {!isLoading && !isAuthenticated && (
        <div>
          <div data-testid="login-state">Please login</div>
          <button 
            data-testid="login-button"
            onClick={() => login({ email: 'test@example.com', password: 'password' })}
          >
            Login
          </button>
          <button 
            data-testid="register-button"
            onClick={() => register({ 
              email: 'new@example.com', 
              password: 'password',
              username: 'newuser',
              firstName: 'New', 
              lastName: 'User'
            })}
          >
            Register
          </button>
          {error && <div data-testid="error-message">{error}</div>}
        </div>
      )}
      {!isLoading && isAuthenticated && user && (
        <div>
          <div data-testid="authenticated-state">
            Welcome, {user.firstName} {user.lastName}
          </div>
          <button data-testid="logout-button" onClick={logout}>
            Logout
          </button>
          <button 
            data-testid="refresh-button" 
            onClick={refreshTokens}
          >
            Refresh Token
          </button>
          <button 
            data-testid="update-user-button" 
            onClick={() => updateUser({ firstName: 'Updated' })}
          >
            Update Profile
          </button>
        </div>
      )}
    </div>
  );
};

// Render with the auth provider
const renderWithAuth = () => {
  return render(
    <AuthProvider>
      <TestComponent />
    </AuthProvider>
  );
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
    expect(screen.getByText(`Welcome, ${mockUser.firstName} ${mockUser.lastName}`)).toBeInTheDocument();
  });

  it('should handle login successfully', async () => {
    // Mock API return values
    (apiService.auth.login as jest.Mock).mockResolvedValue({ 
      data: { 
        user: mockUser, 
        tokens: mockTokens 
      },
      status: 200
    });
    (sessionService.validateSession as jest.Mock).mockReturnValue(false);

    const { getByTestId } = renderWithAuth();

    // Wait for the login state to appear
    await waitFor(() => getByTestId('login-state'), { timeout: 5000 });

    // Perform login
    await act(async () => {
      fireEvent.click(getByTestId('login-button'));
    });

    // Wait for authenticated state to appear
    await waitFor(() => getByTestId('authenticated-state'), { timeout: 5000 });

    // Check that API and service methods were called
    expect(apiService.auth.login).toHaveBeenCalledWith(
      'test@example.com',
      'password'
    );
    expect(sessionService.setTokens).toHaveBeenCalledWith(mockTokens);
    expect(sessionService.setSessionData).toHaveBeenCalled();
  });

  it('should handle registration successfully', async () => {
    // Mock API return values
    (apiService.auth.register as jest.Mock).mockResolvedValue({ 
      data: { 
        user: {
          ...mockUser,
          email: 'new@example.com',
          username: 'newuser',
          firstName: 'New',
          lastName: 'User'
        }, 
        tokens: mockTokens 
      },
      status: 200
    });
    (sessionService.validateSession as jest.Mock).mockReturnValue(false);

    const { getByTestId } = renderWithAuth();

    // Wait for the login state to appear
    await waitFor(() => getByTestId('login-state'), { timeout: 5000 });

    // Perform registration
    await act(async () => {
      fireEvent.click(getByTestId('register-button'));
    });

    // Wait for authenticated state to appear
    await waitFor(() => getByTestId('authenticated-state'), { timeout: 5000 });

    // Check that API and service methods were called with correct parameters
    expect(apiService.auth.register).toHaveBeenCalledWith({
      email: 'new@example.com',
      password: 'password',
      username: 'newuser',
      firstName: 'New',
      lastName: 'User'
    });
    expect(sessionService.setTokens).toHaveBeenCalledWith(mockTokens);
  });

  it('should handle logout successfully', async () => {
    // Set up authenticated state
    (sessionService.validateSession as jest.Mock).mockReturnValue(true);
    (sessionService.getTokens as jest.Mock).mockReturnValue(mockTokens);
    (apiService.auth.validate as jest.Mock).mockResolvedValue({
      data: mockUser,
      status: 200
    });
    
    // Mock API return values
    (apiService.auth.logout as jest.Mock).mockResolvedValue({ 
      data: { success: true },
      status: 200
    });

    const { getByTestId } = renderWithAuth();

    // Wait for authenticated state to appear
    await waitFor(() => getByTestId('authenticated-state'), { timeout: 5000 });

    // Perform logout
    await act(async () => {
      fireEvent.click(getByTestId('logout-button'));
    });

    // Check API calls
    expect(apiService.auth.logout).toHaveBeenCalled();
    expect(sessionService.clearSession).toHaveBeenCalled();

    // Wait for login state to appear
    await waitFor(() => getByTestId('login-state'), { timeout: 5000 });
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
      expect(screen.getByText(`Welcome, Updated ${mockUser.lastName}`)).toBeInTheDocument();
    }, { timeout: 5000 });
  });
});
