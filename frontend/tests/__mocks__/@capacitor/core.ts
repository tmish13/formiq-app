export const Capacitor = {
  isNative: false,
  platform: 'web',
  isPluginAvailable: jest.fn().mockReturnValue(true),
};

export class WebPlugin {
  constructor() {}
}

export const registerPlugin = jest.fn().mockReturnValue({
  checkPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
  requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
  getPhoto: jest.fn().mockResolvedValue({ path: 'mock/path/to/photo.jpg' }),
}); 