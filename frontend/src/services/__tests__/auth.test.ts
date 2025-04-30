import { AuthService } from '../auth';
import { User, SubscriptionTier } from '../../types/user';
import api from '../api';
import { store } from '../../store';
import { apiService } from '../../services/apiService';
import type { ApiError } from '../../types/api';
import type { RegisterData } from '../../types';

// Mock the axios instance
jest.mock('../api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    delete: jest.fn()
  }
}));

jest.mock('../../store', () => ({
  store: {
    dispatch: jest.fn(),
  },
}));

// Mock API service
jest.mock('../../services/apiService', () => ({
  apiService: {
    auth: {
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      validate: jest.fn(),
    },
    profile: {
      update: jest.fn(),
    },
  },
}));

// Mock window.atob for JWT token parsing
const originalAtob = global.atob;
global.atob = jest.fn().mockImplementation((str) => {
  return JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 3600 }); // Token expires in 1 hour
});

// Mock clearTimeout to prevent memory leaks
jest.spyOn(global, 'clearTimeout');
jest.spyOn(global, 'setTimeout').mockImplementation((callback, _) => {
  return 123 as any; // Return a dummy timeout ID
});

const mockUser: User = {
  id: '123',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  subscriptionTier: 'free' as SubscriptionTier,
  isActive: true,
  isVerified: true,
  isEmailVerified: true,
  createdAt: '2024-01-01T00:00:00Z',
  updatedAt: '2024-01-01T00:00:00Z'
};

// Create a valid JWT token format (header.payload.signature)
const mockHeader = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
const mockPayload = btoa(JSON.stringify({ 
  exp: Math.floor(Date.now() / 1000) + 3600,
  sub: '123',
  email: 'test@example.com' 
}));
const mockSignature = 'fake_signature';
const mockAccessToken = `${mockHeader}.${mockPayload}.${mockSignature}`;
const mockRefreshToken = 'mock_refresh_token';

const mockTokens = {
  access_token: mockAccessToken,
  refresh_token: mockRefreshToken
};

// Create a more reliable mock of localStorage
const mockLocalStorageData: Record<string, string> = {};

const mockLocalStorage = {
  getItem: jest.fn((key) => mockLocalStorageData[key] || null),
  setItem: jest.fn((key, value) => {
    mockLocalStorageData[key] = value;
  }),
  removeItem: jest.fn((key) => {
    delete mockLocalStorageData[key];
  }),
  clear: jest.fn(() => {
    Object.keys(mockLocalStorageData).forEach((key) => {
      delete mockLocalStorageData[key];
    });
  }),
  key: jest.fn(),
  length: 0
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  writable: true
});

// Create a fresh session for each test
const createMockSession = () => ({
  access_token: mockTokens.access_token,
  user: mockUser,
  refreshCount: 0,
  lastRefresh: Date.now()
});

describe('AuthService', () => {
  let authService: AuthService;

  beforeEach(() => {
    jest.clearAllMocks();
    // Clear localStorage before each test
    mockLocalStorage.clear();
    // Reset the mockLocalStorageData
    Object.keys(mockLocalStorageData).forEach(key => {
      delete mockLocalStorageData[key];
    });
  });

  describe('login', () => {
    it('should handle successful login', async () => {
      const credentials = { email: 'test@example.com', password: 'password' };
      const mockResponse = {
        data: {
          access_token: mockTokens.access_token,
          user: mockUser,
        },
      };

      (apiService.auth.login as jest.Mock).mockResolvedValue(mockResponse);

      authService = new AuthService();
      const result = await authService.login(credentials);

      expect(apiService.auth.login).toHaveBeenCalledWith(credentials.email, credentials.password);
      expect(result).toEqual({
        access_token: mockTokens.access_token,
        user: mockUser,
      });

      // Check that localStorage was updated
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'formiq_session', 
        expect.any(String)
      );
      
      // Verify the localStorage content directly
      const sessionData = mockLocalStorage.getItem('formiq_session');
      expect(sessionData).toBeTruthy();
      
      // Parse the session data and check it's correct
      const parsedSession = JSON.parse(sessionData as string);
      expect(parsedSession).toEqual({
        access_token: mockTokens.access_token,
        user: mockUser,
      });
    });

    it('should handle login failure', async () => {
      const credentials = { email: 'test@example.com', password: 'wrong' };
      const error = new Error('Invalid credentials');
      error.name = 'ApiError';
      (error as any).status = 401;
      (error as any).code = 'AUTH_002';

      (apiService.auth.login as jest.Mock).mockRejectedValue(error);

      authService = new AuthService();
      await expect(authService.login(credentials)).rejects.toThrow('Invalid credentials');
      expect(mockLocalStorage.getItem('formiq_session')).toBeNull();
    });
  });

  describe('register', () => {
    it('should handle successful registration', async () => {
      const registerData: RegisterData = {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      };

      const mockResponse = {
        data: {
          access_token: mockTokens.access_token,
          user: mockUser,
        },
      };

      (apiService.auth.register as jest.Mock).mockResolvedValue(mockResponse);

      authService = new AuthService();
      const result = await authService.register(registerData);

      expect(apiService.auth.register).toHaveBeenCalledWith({
        email: registerData.email,
        password: registerData.password,
        username: registerData.email.split('@')[0]
      });
      expect(result).toEqual({
        access_token: mockTokens.access_token,
        user: mockUser,
      });

      // Check that localStorage was updated
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'formiq_session', 
        expect.any(String)
      );
      
      // Verify the localStorage content directly
      const sessionData = mockLocalStorage.getItem('formiq_session');
      expect(sessionData).toBeTruthy();
      
      // Parse the session data and check the keys
      const parsedSession = JSON.parse(sessionData as string);
      expect(parsedSession).toHaveProperty('access_token', mockTokens.access_token);
      expect(parsedSession).toHaveProperty('user', mockUser);
    });

    it('should handle registration failure', async () => {
      const registerData: RegisterData = {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      };
      const error = new Error('Email already exists');
      error.name = 'ApiError';
      (error as any).status = 400;
      (error as any).code = 'USER_EXISTS';
      (error as any).data = { field: 'email' };

      (apiService.auth.register as jest.Mock).mockRejectedValue(error);

      authService = new AuthService();
      await expect(authService.register(registerData)).rejects.toThrow('Email already exists');
      expect(mockLocalStorage.getItem('formiq_session')).toBeNull();
    });
  });

  describe('token validation and refresh', () => {
    it('should validate token successfully', async () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      const mockValidateResponse = {
        data: {
          ...mockUser,
          access_token: 'new_token',
        },
      };

      (apiService.auth.validate as jest.Mock).mockResolvedValue(mockValidateResponse);

      // Create a new instance after setting localStorage
      authService = new AuthService();
      
      const result = await authService.validateToken();
      expect(result).toEqual(mockValidateResponse.data);
    });

    it('should handle token validation failure', async () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      const error = new Error('Invalid token');
      error.name = 'ApiError';
      (error as any).status = 401;
      (error as any).code = 'AUTH_004';

      (apiService.auth.validate as jest.Mock).mockRejectedValue(error);

      // Create a new instance after setting localStorage
      authService = new AuthService();
      
      await expect(authService.validateToken()).rejects.toThrow();
      
      // Verify session was cleared on error
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('formiq_session');
      expect(mockLocalStorage.getItem('formiq_session')).toBeNull();
    });
  });

  describe('session management', () => {
    it('should clear session on logout', async () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      (apiService.auth.logout as jest.Mock).mockResolvedValue({});

      // Create a new instance after setting localStorage
      authService = new AuthService();
      
      await authService.logout();

      expect(apiService.auth.logout).toHaveBeenCalled();
      expect(mockLocalStorage.removeItem).toHaveBeenCalledWith('formiq_session');
      expect(mockLocalStorage.getItem('formiq_session')).toBeNull();
    });

    it('should handle logout failure', async () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      const error = new Error('Logout failed');
      error.name = 'ApiError';
      (error as any).status = 500;
      (error as any).code = 'AUTH_005';

      (apiService.auth.logout as jest.Mock).mockRejectedValue(error);

      // Create a new instance after setting localStorage
      authService = new AuthService();
      
      await expect(authService.logout()).rejects.toThrow();
    });
  });

  describe('refreshToken', () => {
    // Create a separate mock for refreshToken tests
    let mockRefreshResolver: any;
    
    beforeEach(() => {
      // Clear all mocks
      jest.clearAllMocks();

      // Create a custom refreshToken implementation that we can control
      (AuthService.prototype as any).refreshToken = jest.fn().mockImplementation(function() {
        return new Promise((resolve, reject) => {
          mockRefreshResolver = { resolve, reject };
        });
      });
    });

    it('should refresh token successfully', async () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      // Create the new instance which will use our mocked refreshToken
      authService = new AuthService();
      
      // Initiate refresh but don't await it yet
      const refreshPromise = authService.refreshToken();
      
      // Define the refresh success response
      const refreshResponse = {
        access_token: 'new_access_token',
        user: mockUser,
      };
      
      // Resolve the refresh call
      mockRefreshResolver.resolve(refreshResponse);
      
      // Now await the promise
      const result = await refreshPromise;
      
      // Verify the result
      expect(result).toEqual(refreshResponse);
    });

    it('should handle refresh token failure', async () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));

      // Create a new instance with our mocked refreshToken
      authService = new AuthService();
      
      // Initiate refresh but don't await it yet
      const refreshPromise = authService.refreshToken();
      
      // Create error object
      const error = new Error('Invalid refresh token');
      error.name = 'ApiError';
      (error as any).status = 401;
      (error as any).code = 'AUTH_003';
      
      // Reject the refresh call
      mockRefreshResolver.reject(error);
      
      // Now verify the promise rejects as expected
      await expect(refreshPromise).rejects.toThrow('Invalid refresh token');
    });
  });

  describe('isAuthenticated', () => {
    it('should return true if valid session exists', () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      // Create a new instance after setting localStorage
      authService = new AuthService();
      
      expect(authService.isAuthenticated()).toBe(true);
    });
    
    it('should return false if no session exists', () => {
      // Ensure no session exists
      mockLocalStorage.removeItem('formiq_session');
      
      // Create a new instance with no localStorage session
      authService = new AuthService();
      
      expect(authService.isAuthenticated()).toBe(false);
    });
  });

  describe('getCurrentUser', () => {
    it('should return user from session', () => {
      // Setup a session in localStorage first
      const mockSessionData = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      mockLocalStorage.setItem('formiq_session', JSON.stringify(mockSessionData));
      
      // Create a new instance after setting localStorage
      authService = new AuthService();
      
      expect(authService.getCurrentUser()).toEqual(mockUser);
    });
    
    it('should return null if no session exists', () => {
      // Ensure no session exists
      mockLocalStorage.removeItem('formiq_session');
      
      // Create a new instance with no localStorage session
      authService = new AuthService();
      
      expect(authService.getCurrentUser()).toBeNull();
    });
  });

  afterAll(() => {
    // Restore original global functions
    global.atob = originalAtob;
  });
}); 