// Mock for @capacitor/network
export const networkMock = {
  getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' }),
  addListener: jest.fn().mockReturnValue({ remove: jest.fn() }),
};

// Setup Network mock from @capacitor/network
jest.mock('@capacitor/network', () => ({
  Network: networkMock,
}));

// Mock for NetworkStatus custom hook results
export const mockNetworkStatus = {
  isOnline: true,
  connectionType: 'wifi',
};

// Mock for network service
export const mockNetworkService = {
  isOnline: jest.fn().mockReturnValue(true),
  getConnectionType: jest.fn().mockReturnValue('wifi'),
  addNetworkStatusListener: jest.fn().mockReturnValue(() => {}),
}; 