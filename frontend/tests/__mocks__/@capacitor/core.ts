export const Capacitor = {
  isNative: false,
  platform: 'web',
  isNativePlatform: jest.fn().mockReturnValue(false),
  isPluginAvailable: jest.fn().mockReturnValue(true),
};

export class WebPlugin {
  // Define basic methods that plugins would have
  addListener() {
    return { remove: jest.fn() };
  }
  removeAllListeners() {}
  checkPermissions() {
    return Promise.resolve({});
  }
  requestPermissions() {
    return Promise.resolve({});
  }
}

export const registerPlugin = jest.fn().mockReturnValue({
  checkPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
  requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
  getPhoto: jest.fn().mockResolvedValue({ path: 'mock/path/to/photo.jpg' }),
}); 