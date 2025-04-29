import { jest } from '@jest/globals';

interface PreferencesPlugin {
  get(options: { key: string }): Promise<{ value: any }>;
  set(options: { key: string; value: any }): Promise<void>;
  remove(options: { key: string }): Promise<void>;
  clear(): Promise<void>;
}

const mockGet = async (options: { key: string }): Promise<{ value: any }> => ({ value: null });
const mockSet = async (options: { key: string; value: any }): Promise<void> => {};
const mockRemove = async (options: { key: string }): Promise<void> => {};
const mockClear = async (): Promise<void> => {};

export const Preferences: PreferencesPlugin = {
  get: jest.fn(mockGet),
  set: jest.fn(mockSet),
  remove: jest.fn(mockRemove),
  clear: jest.fn(mockClear)
};

export default Preferences; 