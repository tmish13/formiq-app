// Mock for networkService.ts
export const NetworkStatus = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  CONNECTING: 'connecting',
};

export const useNetworkStatus = jest.fn().mockReturnValue({
  status: {
    connected: true,
    connectionType: 'wifi',
  },
  isOnline: true,
});

export const networkService = {
  initialize: jest.fn().mockResolvedValue(true),
  onStatusChange: jest.fn(),
  getCurrentStatus: jest.fn().mockReturnValue({
    connected: true,
    connectionType: 'wifi',
  }),
  addStatusChangeListener: jest.fn().mockReturnValue({ remove: jest.fn() }),
  removeStatusChangeListener: jest.fn(),
}; 