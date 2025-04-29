import { Network } from '@capacitor/network';
import { Capacitor } from '@capacitor/core';
import { networkService, NetworkStatus, defaultNetworkStatus } from '../../../src/services/networkService';
import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Mock Capacitor
jest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: jest.fn()
  }
}));

// Mock Network from @capacitor/network
jest.mock('@capacitor/network', () => ({
  Network: {
    getStatus: jest.fn(),
    addListener: jest.fn()
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
  let mockRemoveListener: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockListener = jest.fn();
    mockRemoveListener = jest.fn();

    // Reset window.navigator.onLine
    Object.defineProperty(window.navigator, 'onLine', {
      configurable: true,
      value: true
    });

    // Mock Network.addListener to return a cleanup function
    (Network.addListener as jest.Mock).mockReturnValue({
      remove: mockRemoveListener
    });
  });

  describe('initialization', () => {
    it('should initialize with web implementation when not on native platform', async () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      
      const status = await networkService.getStatus();
      expect(status).toEqual({
        connected: true,
        connectionType: 'wifi'
      });
    });

    it('should initialize with native implementation on native platform', async () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(true);
      (Network.getStatus as jest.Mock).mockResolvedValue({
        connected: true,
        connectionType: 'wifi'
      });

      const status = await networkService.getStatus();
      expect(status).toEqual({
        connected: true,
        connectionType: 'wifi'
      });
      expect(Network.getStatus).toHaveBeenCalled();
    });

    it('should handle initialization errors gracefully', async () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(true);
      (Network.getStatus as jest.Mock).mockRejectedValue(new Error('Network error'));

      const status = await networkService.getStatus();
      expect(status).toEqual({
        connected: navigator.onLine,
        connectionType: navigator.onLine ? 'wifi' : 'none'
      });
    });
  });

  describe('status monitoring', () => {
    it('should update status when going offline in web implementation', async () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      
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
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      
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
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(true);
      
      const subscription = networkService.subscribe(mockListener);
      
      // Simulate native network status change
      const mockCallback = (Network.addListener as jest.Mock).mock.calls[0][1];
      mockCallback({
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
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      
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
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      
      const removeEventListenerSpy = jest.spyOn(window, 'removeEventListener');
      
      networkService.cleanup();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('online', expect.any(Function));
      expect(removeEventListenerSpy).toHaveBeenCalledWith('offline', expect.any(Function));
    });

    it('should cleanup native listeners', () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(true);
      
      networkService.cleanup();
      
      expect(mockRemoveListener).toHaveBeenCalled();
    });
  });

  describe('online status check', () => {
    it('should return true when online', async () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      Object.defineProperty(window.navigator, 'onLine', {
        configurable: true,
        value: true
      });

      const isOnline = await networkService.isOnline();
      expect(isOnline).toBe(true);
    });

    it('should return false when offline', async () => {
      (Capacitor.isNativePlatform as jest.Mock).mockReturnValue(false);
      Object.defineProperty(window.navigator, 'onLine', {
        configurable: true,
        value: false
      });

      const isOnline = await networkService.isOnline();
      expect(isOnline).toBe(false);
    });
  });
}); 