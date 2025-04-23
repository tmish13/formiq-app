import { Network } from '@capacitor/network';

jest.mock('@capacitor/network', () => ({
  Network: {
    addListener: jest.fn(),
    removeAllListeners: jest.fn(),
    getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' }),
  },
}));

export const mockNetworkStatus = {
  addListener: jest.fn(),
  removeAllListeners: jest.fn(),
  getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' }),
  mockConnected: true,
  mockConnectionType: 'wifi',
};

export const setMockNetworkStatus = (connected: boolean, connectionType: string) => {
  mockNetworkStatus.mockConnected = connected;
  mockNetworkStatus.mockConnectionType = connectionType;
  mockNetworkStatus.getStatus.mockResolvedValue({ connected, connectionType });
}; 