import { Preferences } from '@capacitor/preferences';

const mockStorage = new Map<string, string>();

jest.mock('@capacitor/preferences', () => ({
  Preferences: {
    get: jest.fn().mockImplementation(async ({ key }) => ({ value: mockStorage.get(key) || null })),
    set: jest.fn().mockImplementation(async ({ key, value }) => {
      mockStorage.set(key, value);
      return;
    }),
    remove: jest.fn().mockImplementation(async ({ key }) => {
      mockStorage.delete(key);
      return;
    }),
    clear: jest.fn().mockImplementation(async () => {
      mockStorage.clear();
      return;
    }),
    keys: jest.fn().mockImplementation(async () => ({ keys: Array.from(mockStorage.keys()) })),
  },
}));

// Helper function to clear the mock storage
export const clearMockStorage = () => {
  mockStorage.clear();
};

// Export the mock for direct access in tests
export const mockStorageService = {
  get: jest.fn().mockImplementation(async ({ key }) => ({ value: mockStorage.get(key) || null })),
  set: jest.fn().mockImplementation(async ({ key, value }) => {
    mockStorage.set(key, value);
    return;
  }),
  remove: jest.fn().mockImplementation(async ({ key }) => {
    mockStorage.delete(key);
    return;
  }),
  clear: jest.fn().mockImplementation(async () => {
    mockStorage.clear();
    return;
  }),
  keys: jest.fn().mockImplementation(async () => ({ keys: Array.from(mockStorage.keys()) })),
}; 