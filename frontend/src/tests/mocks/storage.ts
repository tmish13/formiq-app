const createStorageMock = () => {
  let store: { [key: string]: string } = {};
  return {
    getItem: jest.fn((key: string) => {
      return store[key] || null;
    }),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    key: jest.fn((index: number) => Object.keys(store)[index] || null),
    get length() {
      return Object.keys(store).length;
    }
  };
};

export const mockStorage = createStorageMock();

export const mockPreferences = {
  get: jest.fn(),
  set: jest.fn(),
  remove: jest.fn(),
  clear: jest.fn()
};

// Clear storage between tests
export const clearMockStorage = () => {
  mockStorage.clear();
  mockPreferences.get.mockClear();
  mockPreferences.set.mockClear();
  mockPreferences.remove.mockClear();
  mockPreferences.clear.mockClear();
};

export const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn()
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
}); 