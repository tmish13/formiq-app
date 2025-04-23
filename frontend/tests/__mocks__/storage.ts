/**
 * Mock implementation of localStorage for tests
 */
export class LocalStorageMock {
  private store: Record<string, string> = {};

  clear() {
    this.store = {};
  }

  getItem(key: string) {
    return this.store[key] || null;
  }

  setItem(key: string, value: string) {
    this.store[key] = String(value);
  }

  removeItem(key: string) {
    delete this.store[key];
  }

  get length() {
    return Object.keys(this.store).length;
  }

  key(index: number) {
    return Object.keys(this.store)[index] || null;
  }
}

/**
 * Mock storage service for tests
 */
export const mockStorageService = {
  get: jest.fn().mockImplementation((key: string) => {
    return JSON.parse(localStorage.getItem(key) || 'null');
  }),
  
  set: jest.fn().mockImplementation((key: string, value: any) => {
    localStorage.setItem(key, JSON.stringify(value));
  }),
  
  remove: jest.fn().mockImplementation((key: string) => {
    localStorage.removeItem(key);
  }),
  
  clear: jest.fn().mockImplementation(() => {
    localStorage.clear();
  }),
  
  getItem: jest.fn().mockImplementation((key: string) => {
    return localStorage.getItem(key);
  }),
  
  setItem: jest.fn().mockImplementation((key: string, value: string) => {
    localStorage.setItem(key, value);
  }),
  
  removeItem: jest.fn().mockImplementation((key: string) => {
    localStorage.removeItem(key);
  }),
  
  /**
   * Mock a JWT token in localStorage for auth tests
   */
  mockAuthToken: (token = 'mock-jwt-token', refreshToken = 'mock-refresh-token') => {
    const mockTokens = {
      accessToken: token,
      refreshToken: refreshToken,
      expiresIn: 3600
    };
    localStorage.setItem('auth_tokens', JSON.stringify(mockTokens));
    return mockTokens;
  },
  
  /**
   * Mock user session data in localStorage
   */
  mockUserSession: (userData = {
    id: 'user-123',
    email: 'test@example.com',
    username: 'testuser',
    preferences: { theme: 'light' }
  }) => {
    localStorage.setItem('user_data', JSON.stringify(userData));
    return userData;
  },
  
  /**
   * Clear auth data from localStorage
   */
  clearAuth: () => {
    localStorage.removeItem('auth_tokens');
    localStorage.removeItem('user_data');
  }
};

export const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0,
};

export const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  key: jest.fn(),
  length: 0,
};

// Capacitor Preferences mock
export const preferencesMock = {
  get: jest.fn().mockResolvedValue({ value: null }),
  set: jest.fn().mockResolvedValue(undefined),
  remove: jest.fn().mockResolvedValue(undefined),
  clear: jest.fn().mockResolvedValue(undefined),
  keys: jest.fn().mockResolvedValue({ keys: [] }),
  configure: jest.fn().mockResolvedValue(undefined),
};

// Setup mock for @capacitor/preferences
jest.mock('@capacitor/preferences', () => ({
  Preferences: preferencesMock,
}));

// Setup localStorage and sessionStorage mocks on global object
Object.defineProperty(window, 'localStorage', { value: localStorageMock });
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock }); 