import { Capacitor } from '@capacitor/core';

jest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: jest.fn().mockReturnValue(false),
    getPlatform: jest.fn().mockReturnValue('web'),
    isPluginAvailable: jest.fn().mockReturnValue(false),
    registerPlugin: jest.fn(),
    platform: 'web',
  },
}));

export const mockCapacitor = {
  isNativePlatform: jest.fn().mockReturnValue(false),
  getPlatform: jest.fn().mockReturnValue('web'),
  isPluginAvailable: jest.fn().mockReturnValue(false),
  registerPlugin: jest.fn(),
  platform: 'web',
}; 