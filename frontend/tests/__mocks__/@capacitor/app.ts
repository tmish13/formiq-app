// Mock implementation of @capacitor/app
export const App = {
  getLaunchUrl: jest.fn().mockResolvedValue({ url: '' }),
  getInfo: jest.fn().mockResolvedValue({
    name: 'Test App',
    id: 'com.test.app',
    build: '1.0.0',
    version: '1.0.0'
  }),
  getState: jest.fn().mockResolvedValue({ isActive: true }),
  exitApp: jest.fn(),
  minimizeApp: jest.fn(),
  addListener: jest.fn().mockReturnValue({
    remove: jest.fn()
  }),
  removeAllListeners: jest.fn()
}; 