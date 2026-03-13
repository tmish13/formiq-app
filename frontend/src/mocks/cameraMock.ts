import { jest } from '@jest/globals';
import type { Photo, PermissionStatus } from '@capacitor/camera';

// Mock camera API
export const mockCamera = {
  getPhoto: jest.fn<() => Promise<Photo>>().mockResolvedValue({
    base64String: 'mock-base64-string',
    format: 'jpeg',
    saved: false,
    webPath: 'mock-web-path'
  }),
  checkPermissions: jest.fn<() => Promise<PermissionStatus>>().mockResolvedValue({
    camera: 'granted',
    photos: 'granted'
  }),
  requestPermissions: jest.fn<() => Promise<PermissionStatus>>().mockResolvedValue({
    camera: 'granted',
    photos: 'granted'
  })
};
