export const NetworkStatus = {
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected'
};

export const mockNetwork = {
  getStatus: jest.fn().mockImplementation(() => Promise.resolve({ connected: true, connectionType: 'wifi' })),
  addListener: jest.fn().mockImplementation((eventName, listenerFunc) => {
    return {
      remove: () => {}
    };
  }),
  removeAllListeners: jest.fn().mockImplementation(() => Promise.resolve())
};

export default mockNetwork; 