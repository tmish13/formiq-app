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

const mockStorage = new Map<string, string>();

export const mockStorageService = {
  get: jest.fn((key: string) => mockStorage.get(key)),
  set: jest.fn((key: string, value: string) => mockStorage.set(key, value)),
  remove: jest.fn((key: string) => mockStorage.delete(key)),
  clear: jest.fn(() => mockStorage.clear()),
  getItem: jest.fn((key: string) => mockStorage.get(key)),
  setItem: jest.fn((key: string, value: string) => mockStorage.set(key, value)),
  removeItem: jest.fn((key: string) => mockStorage.delete(key)),
};

export const clearMockStorage = () => mockStorage.clear();

jest.mock('../../src/services/storageService', () => ({
  storageService: mockStorageService,
}));

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