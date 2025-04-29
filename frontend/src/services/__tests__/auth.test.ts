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
  updatedAt: '2024-01-01T00:00:00Z'
};

const mockTokens = {
  access_token: 'mock_access_token',
  refresh_token: 'mock_refresh_token'
};

const mockLocalStorage = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0
};

Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage
});

describe('AuthService', () => {
  let authService: AuthService;
  let localStorageSpy: jest.SpyInstance;

  const mockSession = {
    access_token: mockTokens.access_token,
    refresh_token: mockTokens.refresh_token,
    refreshCount: 0,
    lastRefresh: new Date().toISOString()
  };

  beforeEach(() => {
    localStorage.clear();
    localStorageSpy = jest.spyOn(Storage.prototype, 'getItem');
    authService = new AuthService();
    jest.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    localStorageSpy.mockRestore();
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

      const result = await authService.login(credentials);

      expect(apiService.auth.login).toHaveBeenCalledWith(credentials.email, credentials.password);
      expect(result).toEqual({
        access_token: mockTokens.access_token,
        user: mockUser,
      });

      const savedSession = localStorage.getItem('formiq_session');
      expect(savedSession).toBeTruthy();
      expect(JSON.parse(savedSession!)).toEqual({
        access_token: mockTokens.access_token,
        user: mockUser,
      });
    });

    it('should handle login failure', async () => {
      const credentials = { email: 'test@example.com', password: 'wrong' };
      const error: ApiError = {
        name: 'ApiError',
        status: 401,
        message: 'Invalid credentials',
        code: 'AUTH_002'
      };

      (apiService.auth.login as jest.Mock).mockRejectedValue(error);

      await expect(authService.login(credentials)).rejects.toThrow('Invalid credentials');
      expect(localStorage.getItem('formiq_session')).toBeNull();
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

      const savedSession = localStorage.getItem('formiq_session');
      expect(savedSession).toBeTruthy();
      expect(JSON.parse(savedSession!)).toEqual({
        access_token: mockTokens.access_token,
        user: mockUser,
        refreshCount: 0,
        lastRefresh: expect.any(Number)
      });
    });

    it('should handle registration failure', async () => {
      const registerData: RegisterData = {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      };
      const error: ApiError = {
        name: 'ApiError',
        status: 400,
        message: 'Email already exists',
        code: 'USER_EXISTS',
        data: { field: 'email' }
      };

      (apiService.auth.register as jest.Mock).mockRejectedValue(error);

      await expect(authService.register(registerData)).rejects.toThrow('Email already exists');
      expect(localStorage.getItem('formiq_session')).toBeNull();
    });
  });

  describe('token validation and refresh', () => {
    it('should validate token successfully', async () => {
      const mockSession = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService(); // Reinitialize with session

      const mockValidateResponse = {
        data: {
          ...mockUser,
          access_token: 'new_token',
        },
      };

      (apiService.auth.validate as jest.Mock).mockResolvedValue(mockValidateResponse);

      const result = await authService.validateToken();
      expect(result).toEqual(mockValidateResponse.data);
    });

    it('should handle token validation failure', async () => {
      const mockSession = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();

      const error: ApiError = {
        name: 'ApiError',
        status: 401,
        message: 'Invalid token',
        code: 'AUTH_004'
      };
      (apiService.auth.validate as jest.Mock).mockRejectedValue(error);

      await expect(authService.validateToken()).rejects.toThrow('Invalid token');
      expect(localStorage.getItem('formiq_session')).toBeNull();
    });
  });

  describe('session management', () => {
    it('should clear session on logout', async () => {
      const mockSession = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();

      (apiService.auth.logout as jest.Mock).mockResolvedValue({});

      await authService.logout();

      expect(apiService.auth.logout).toHaveBeenCalled();
      expect(localStorage.getItem('formiq_session')).toBeNull();
    });

    it('should handle logout failure', async () => {
      const mockSession = {
        access_token: mockTokens.access_token,
        user: mockUser,
      };
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();

      const error: ApiError = {
        name: 'ApiError',
        status: 500,
        message: 'Logout failed',
        code: 'SVC_601'
      };
      (apiService.auth.logout as jest.Mock).mockRejectedValue(error);

      await expect(authService.logout()).rejects.toThrow('Logout failed');
    });
  });

  describe('refreshToken', () => {
    it('should throw error if no active session', async () => {
      await expect(authService.refreshToken()).rejects.toThrow('No active session');
    });

    it('should refresh token successfully', async () => {
      // Set up initial session
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();

      const mockResponse = {
        data: {
          access_token: 'new_access_token',
          user: mockUser,
        },
      };

      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);

      const result = await authService.refreshToken();
      expect(result).toEqual({
        access_token: 'new_access_token',
        user: mockUser,
      });
    });

    it('should handle refresh token failure', async () => {
      // Set up initial session
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();

      const error: ApiError = {
        name: 'ApiError',
        status: 401,
        message: 'Invalid refresh token',
        code: 'AUTH_003'
      };
      (api.get as jest.Mock).mockRejectedValueOnce(error);

      await expect(authService.refreshToken()).rejects.toThrow('Invalid refresh token');
    });
  });

  describe('isAuthenticated', () => {
    it('should return false if no session exists', () => {
      expect(authService.isAuthenticated()).toBe(false);
    });

    it('should return true if valid session exists', () => {
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();
      expect(authService.isAuthenticated()).toBe(true);
    });
  });

  describe('getCurrentUser', () => {
    it('should return null if no session exists', () => {
      expect(authService.getCurrentUser()).toBeNull();
    });

    it('should return user from session', () => {
      localStorage.setItem('formiq_session', JSON.stringify(mockSession));
      authService = new AuthService();
      expect(authService.getCurrentUser()).toEqual(mockUser);
    });
  });
}); 