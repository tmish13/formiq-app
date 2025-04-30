import { Network } from '@capacitor/network';
import { Capacitor } from '@capacitor/core';
import { networkService, NetworkStatus, defaultNetworkStatus } from '../networkService';
import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Mock Capacitor to control isNativePlatform result
const mockIsNativePlatform = jest.fn();
jest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => mockIsNativePlatform()
  }
}));

// Mock the network status with predefined return values
const mockNetworkStatus = {
  connected: true,
  connectionType: 'wifi'
};

// Create mock functions for Network module
const mockGetStatus = jest.fn().mockResolvedValue(mockNetworkStatus);
const mockRemoveListener = jest.fn();
const mockAddListener = jest.fn().mockImplementation((eventName: string, callback: (status: any) => void) => {
  return { remove: mockRemoveListener };
});

// Mock the Network module
jest.mock('@capacitor/network', () => ({
  Network: {
    getStatus: () => mockGetStatus(),
    addListener: (eventName, callback) => mockAddListener(eventName, callback)
  }
}));

// Create test server
const server = setupServer(
  // Mock successful response
  rest.get('/api/health', (req, res, ctx) => {
    return res(ctx.json({ status: 'ok' }));
  }),

  // Mock error response
  rest.get('/api/error', (req, res, ctx) => {
    return res(ctx.status(500));
  }),

  // Mock timeout
  rest.get('/api/timeout', (req, res, ctx) => {
    return res(ctx.delay(5000));
  })
);

describe('NetworkService', () => {
  let mockListener: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset mocks
    mockListener = jest.fn();
    mockIsNativePlatform.mockReset();
    mockGetStatus.mockClear();
    mockRemoveListener.mockClear();
    mockAddListener.mockClear();
    
    // Reset networkService instance by calling cleanup
    networkService.cleanup();
    
    // Make sure the initialized state is reset
    // @ts-ignore - accessing private property for testing
    networkService['initialized'] = false;
    // @ts-ignore - accessing private property for testing
    networkService['networkListener'] = null;
    
    // Reset window.navigator.onLine
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true
    });
  });

  describe('initialization', () => {
    it('should initialize with web implementation when not on native platform', async () => {
      mockIsNativePlatform.mockReturnValue(false);
      
      const status = await networkService.getStatus();
      
      expect(status).toEqual({
        connected: true,
        connectionType: 'wifi'
      });
      
      expect(mockGetStatus).not.toHaveBeenCalled();
    });

    it('should initialize with native implementation on native platform', async () => {
      mockIsNativePlatform.mockReturnValue(true);
      mockGetStatus.mockResolvedValue({
        connected: true,
        connectionType: 'wifi'
      });
      
      const status = await networkService.getStatus();
      
      expect(status).toEqual({
        connected: true,
        connectionType: 'wifi'
      });
      
      expect(mockGetStatus).toHaveBeenCalled();
    });

    it('should handle initialization errors gracefully', async () => {
      mockIsNativePlatform.mockReturnValue(true);
      mockGetStatus.mockRejectedValueOnce(new Error('Network error'));
      
      const status = await networkService.getStatus();
      
      expect(status).toEqual({
        connected: navigator.onLine,
        connectionType: navigator.onLine ? 'wifi' : 'none'
      });
    });
  });

  describe('status monitoring', () => {
    it('should update status when going offline in web implementation', async () => {
      mockIsNativePlatform.mockReturnValue(false);
      
      // Initialize service
      await networkService.getStatus();
      
      const subscription = networkService.subscribe(mockListener);
      
      // Simulate going offline
      window.dispatchEvent(new Event('offline'));
      
      expect(mockListener).toHaveBeenCalledWith({
        connected: false,
        connectionType: 'none'
      });

      subscription();
    });

    it('should update status when going online in web implementation', async () => {
      mockIsNativePlatform.mockReturnValue(false);
      
      // Initialize service
      await networkService.getStatus();
      
      const subscription = networkService.subscribe(mockListener);
      
      // Simulate going online
      window.dispatchEvent(new Event('online'));
      
      expect(mockListener).toHaveBeenCalledWith({
        connected: true,
        connectionType: 'wifi'
      });

      subscription();
    });

    it('should handle status changes in native implementation', async () => {
      mockIsNativePlatform.mockReturnValue(true);
      
      // Initialize service
      await networkService.getStatus();
      
      // Subscribe to network events
      const subscription = networkService.subscribe(mockListener);
      
      // Verify listener was registered
      expect(mockAddListener).toHaveBeenCalledWith('networkStatusChange', expect.any(Function));
      
      // Get the callback that was registered
      const registeredCallback = mockAddListener.mock.calls[0][1];
      
      // Simulate network status change by calling the callback
      registeredCallback({
        connected: false,
        connectionType: 'none'
      });
      
      expect(mockListener).toHaveBeenCalledWith({
        connected: false,
        connectionType: 'none'
      });

      subscription();
    });
  });

  describe('subscription management', () => {
    it('should allow subscribing and unsubscribing to status changes', async () => {
      mockIsNativePlatform.mockReturnValue(false);
      
      // Initialize service
      await networkService.getStatus();
      
      const unsubscribe = networkService.subscribe(mockListener);
      
      // Trigger status change
      window.dispatchEvent(new Event('offline'));
      expect(mockListener).toHaveBeenCalled();
      
      // Unsubscribe
      unsubscribe();
      
      // Reset mock
      mockListener.mockReset();
      
      // Trigger status change again
      window.dispatchEvent(new Event('online'));
      expect(mockListener).not.toHaveBeenCalled();
    });
  });

  describe('cleanup', () => {
    it('should cleanup web event listeners', () => {
      mockIsNativePlatform.mockReturnValue(false);
      
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');
      
      // Initialize service
      networkService.getStatus();
      
      networkService.cleanup();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('online', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('offline', expect.any(Function));
    });

    it('should cleanup native listeners', async () => {
      mockIsNativePlatform.mockReturnValue(true);
      
      // Initialize the service
      await networkService.getStatus();
      
      // Verify addListener was called
      expect(mockAddListener).toHaveBeenCalled();
      
      // Create a reference to the network listener
      // @ts-ignore - accessing private property for testing
      networkService['networkListener'] = { remove: mockRemoveListener };
      
      // Call cleanup
      networkService.cleanup();
      
      // Verify the listener was removed
      expect(mockRemoveListener).toHaveBeenCalled();
    });
  });

  describe('online status check', () => {
    it('should return true when online', async () => {
      mockIsNativePlatform.mockReturnValue(false);
      Object.defineProperty(window.navigator, 'onLine', {
        configurable: true,
        value: true
      });

      const isOnline = await networkService.isOnline();
      expect(isOnline).toBe(true);
    });

    it('should return false when offline', async () => {
      mockIsNativePlatform.mockReturnValue(false);
      Object.defineProperty(window.navigator, 'onLine', {
        configurable: true,
        value: false
      });

      const isOnline = await networkService.isOnline();
      expect(isOnline).toBe(false);
    });
  });
}); 