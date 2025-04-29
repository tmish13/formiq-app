import { jest } from '@jest/globals';

// Mock camera API
export const mockCamera = {
  getPhoto: jest.fn().mockResolvedValue({
    base64String: 'mock-base64-string',
    format: 'jpeg',
    saved: false,
    webPath: 'mock-web-path'
  }),
  checkPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
  requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' })
}; 