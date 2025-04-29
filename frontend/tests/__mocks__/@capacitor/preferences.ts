import { jest } from '@jest/globals';

interface PreferencesPlugin {
  get(options: { key: string }): Promise<{ value: any }>;
  set(options: { key: string; value: any }): Promise<void>;
  remove(options: { key: string }): Promise<void>;
  clear(): Promise<void>;
  keys(): Promise<{ keys: string[] }>;
}

// Mock storage for tests
const mockStorage: Record<string, string> = {};

// Create exportable mock functions
export const mockPreferencesSet = jest.fn(({ key, value }: { key: string; value: any }) => {
  mockStorage[key] = value;
  return Promise.resolve();
});

export const mockPreferencesGet = jest.fn(({ key }: { key: string }) => {
  return Promise.resolve({ value: mockStorage[key] || null });
});

export const mockPreferencesRemove = jest.fn(({ key }: { key: string }) => {
  delete mockStorage[key];
  return Promise.resolve();
});

export const mockPreferencesClear = jest.fn(() => {
  Object.keys(mockStorage).forEach(key => {
    delete mockStorage[key];
  });
  return Promise.resolve();
});

export const mockPreferencesKeys = jest.fn(() => {
  return Promise.resolve({ keys: Object.keys(mockStorage) });
});

// Helper function to initialize the mock store with values
export const initializeWithValues = (initialValues: Record<string, string>) => {
  Object.entries(initialValues).forEach(([key, value]) => {
    mockStorage[key] = value;
  });
};

// Create the Preferences mock that uses the mockFunctions
export const Preferences: PreferencesPlugin = {
  set: mockPreferencesSet,
  get: mockPreferencesGet,
  remove: mockPreferencesRemove,
  clear: mockPreferencesClear,
  keys: mockPreferencesKeys
};

// Initialize with default mock values
initializeWithValues({
  'formiq_analysis_cache': JSON.stringify({
    'analysis-1': { data: 'test data' }
  }),
  'formiq_sync_status': JSON.stringify({
    lastSync: '2024-04-14T10:00:00Z',
    pending: 5
  }),
  'formiq_settings': JSON.stringify({
    theme: 'dark', 
    notifications: true
  }),
  'formiq_csrf_token': 'test-csrf-token',
});

export default Preferences; 