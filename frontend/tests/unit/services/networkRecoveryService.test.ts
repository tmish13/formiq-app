import { networkRecoveryService } from '../../../src/services/networkRecovery';
import { storageService } from '../../../src/services/storageService';

// Mock the storageService
jest.mock('../../../src/services/storageService', () => ({
  storageService: {
    get: jest.fn(),
    set: jest.fn(),
    remove: jest.fn()
  }
}));

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

// Mock addEventListener and removeEventListener
window.addEventListener = jest.fn();
window.removeEventListener = jest.fn();

// Mock setTimeout and clearTimeout
jest.useFakeTimers();

describe('NetworkRecoveryService', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    
    // Ensure network recovery service starts fresh
    networkRecoveryService.destroy();
    
    // Clear any stored requests
    const mockStorageSet = storageService.set as jest.Mock;
    mockStorageSet.mockResolvedValue(undefined);
    
    // Mock empty queue by default
    const mockStorageGet = storageService.get as jest.Mock;
    mockStorageGet.mockResolvedValue(null);
    
    // Force the service to reinitialize
    const initializeMethod = Object.getOwnPropertyDescriptor(
      Object.getPrototypeOf(networkRecoveryService),
      'initialize'
    )?.value;
    
    if (initializeMethod) {
      await initializeMethod.call(networkRecoveryService);
    }
    
    // Clear the queue after initialization
    await networkRecoveryService.clearQueue();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('initialization', () => {
    it('should initialize with event listeners', () => {
      // Event listeners should have been added during initialization
      expect(window.addEventListener).toHaveBeenCalledWith('online', expect.any(Function));
      expect(window.addEventListener).toHaveBeenCalledWith('offline', expect.any(Function));
    });

    it('should load pending requests from storage', async () => {
      // Mock storage to return pending requests
      const mockRequests = [
        { 
          id: 'test-id',
          url: '/test/1', 
          method: 'POST', 
          body: { test: 1 }, 
          headers: { 'Content-Type': 'application/json' },
          timestamp: Date.now(),
          retryCount: 0 
        }
      ];
      
      const mockStorageGet = storageService.get as jest.Mock;
      mockStorageGet.mockResolvedValueOnce(JSON.stringify(mockRequests));
      
      // Force the service to reload pending requests
      const loadMethod = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(networkRecoveryService),
        'loadPendingRequests'
      )?.value;
      
      if (loadMethod) {
        await loadMethod.call(networkRecoveryService);
      }
      
      expect(mockStorageGet).toHaveBeenCalledWith('pending_requests');
      expect(networkRecoveryService.getQueuedRequests()).toEqual(mockRequests);
    });

    it('should handle errors when loading pending requests', async () => {
      // Reset the service first
      networkRecoveryService.destroy();
      
      // Clear the queue
      await networkRecoveryService.clearQueue();
      
      // Verify the queue is empty initially
      expect(networkRecoveryService.getQueuedRequests()).toEqual([]);
      
      // Mock storage to throw an error
      const mockStorageGet = storageService.get as jest.Mock;
      mockStorageGet.mockRejectedValueOnce(new Error('Storage error'));
      
      // Force the service to reload pending requests
      const loadMethod = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(networkRecoveryService),
        'loadPendingRequests'
      )?.value;
      
      if (loadMethod) {
        await loadMethod.call(networkRecoveryService);
      }
      
      expect(mockStorageGet).toHaveBeenCalledWith('pending_requests');
      expect(networkRecoveryService.getQueuedRequests()).toEqual([]);
    });
  });

  describe('network status handling', () => {
    it('should handle going online', async () => {
      // Set isOnline to false first to simulate being offline
      Object.defineProperty(networkRecoveryService, 'isOnline', {
        value: false,
        writable: true
      });
      
      // Setup empty queue initially
      await networkRecoveryService.clearQueue();
      
      // Add a mock request to the queue
      const mockRequest = {
        url: '/test', 
        method: 'POST', 
        body: { test: true }, 
        headers: { 'Content-Type': 'application/json' }
      };
      
      await networkRecoveryService.queueRequest(mockRequest);
      
      // Verify request was queued
      expect(networkRecoveryService.getQueuedRequests().length).toBe(1);
      
      // Mock successful fetch
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true })
      });
      
      // Trigger going online
      const handleOnline = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(networkRecoveryService), 
        'handleOnline'
      )?.value;
      
      if (handleOnline) {
        await handleOnline.call(networkRecoveryService);
      }
      
      // Now it should be online
      expect(networkRecoveryService.isNetworkOnline()).toBe(true);
      
      // Advance timers to trigger request processing
      jest.advanceTimersByTime(500);
      
      // Request should have been processed
      expect(mockFetch).toHaveBeenCalled();
      
      // Queue should be empty after successful processing
      expect(networkRecoveryService.getQueuedRequests().length).toBe(0);
    });

    it('should handle going offline', () => {
      // Set isOnline to true first
      Object.defineProperty(networkRecoveryService, 'isOnline', {
        value: true,
        writable: true
      });
      
      // Trigger going offline
      const handleOffline = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(networkRecoveryService), 
        'handleOffline'
      )?.value;
      
      if (handleOffline) {
        handleOffline.call(networkRecoveryService);
        
        // Now it should be offline
        expect(networkRecoveryService.isNetworkOnline()).toBe(false);
      }
    });
  });

  describe('request queueing', () => {
    it('should queue requests when offline', async () => {
      // Set to offline
      Object.defineProperty(networkRecoveryService, 'isOnline', {
        value: false,
        writable: true
      });
      
      // Clear the queue first
      await networkRecoveryService.clearQueue();
      
      // Add a request
      const mockRequest = {
        url: '/test',
        method: 'POST',
        body: { test: true },
        headers: { 'Content-Type': 'application/json' }
      };
      
      await networkRecoveryService.queueRequest(mockRequest);
      
      // Verify request was queued
      const queuedRequests = networkRecoveryService.getQueuedRequests();
      expect(queuedRequests.length).toBe(1);
      expect(queuedRequests[0]).toMatchObject({
        url: '/test',
        method: 'POST',
        body: { test: true },
        headers: { 'Content-Type': 'application/json' }
      });
    });
  });

  describe('request processing', () => {
    it('should process requests successfully when online', async () => {
      // Set to online
      Object.defineProperty(networkRecoveryService, 'isOnline', {
        value: true,
        writable: true
      });
      
      // Clear any existing requests
      await networkRecoveryService.clearQueue();
      
      // Mock successful fetch response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: 'success' })
      });
      
      // Add a mock request
      const mockRequest = { 
        url: '/test/success', 
        method: 'POST', 
        body: { test: true }, 
        headers: { 'Content-Type': 'application/json' } 
      };
      
      await networkRecoveryService.queueRequest(mockRequest);
      
      // Advance timers to trigger request processing
      jest.advanceTimersByTime(500);
      
      expect(mockFetch).toHaveBeenCalledWith(
        mockRequest.url,
        expect.objectContaining({
          method: mockRequest.method,
          body: JSON.stringify(mockRequest.body),
          headers: mockRequest.headers
        })
      );
      
      // Queue should be empty after successful processing
      expect(networkRecoveryService.getQueuedRequests().length).toBe(0);
    });
    
    it('should retry failed requests', async () => {
      // Set to online
      Object.defineProperty(networkRecoveryService, 'isOnline', {
        value: true,
        writable: true
      });
      
      // Clear any existing requests
      await networkRecoveryService.clearQueue();
      
      // Mock a failed fetch response followed by a successful one
      mockFetch.mockRejectedValueOnce(new Error('Network error'))
               .mockResolvedValueOnce({
                 ok: true,
                 status: 200,
                 json: async () => ({ data: 'success on retry' })
               });
      
      // Add a mock request to the queue manually
      const queueRequest = {
        id: 'test-retry-id',
        url: '/test/retry',
        method: 'POST',
        body: { test: true },
        headers: { 'Content-Type': 'application/json' },
        timestamp: Date.now(),
        retryCount: 0
      };
      
      const addMethod = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(networkRecoveryService),
        'addToQueue'
      )?.value;
      
      if (addMethod) {
        await addMethod.call(networkRecoveryService, queueRequest);
      }
      
      // Advance timers to trigger request processing
      jest.advanceTimersByTime(500);
      
      // Verify first fetch attempt failed
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // Request should still be in queue but with retryCount = 1
      let requests = networkRecoveryService.getQueuedRequests();
      expect(requests.length).toBe(1);
      expect(requests[0].retryCount).toBe(1);
      
      // Advance timers to trigger request processing again
      jest.advanceTimersByTime(500);
      
      // Verify second fetch attempt was made
      expect(mockFetch).toHaveBeenCalledTimes(2);
      
      // Queue should be empty after successful retry
      requests = networkRecoveryService.getQueuedRequests();
      expect(requests.length).toBe(0);
    });
    
    it('should give up after max retries', async () => {
      // Set to online
      Object.defineProperty(networkRecoveryService, 'isOnline', {
        value: true,
        writable: true
      });
      
      // Clear any existing requests
      await networkRecoveryService.clearQueue();
      
      // Always fail fetch for this test
      mockFetch.mockRejectedValue(new Error('Persistent network error'));
      
      // Add a mock request with max retries already attempted
      const queueRequest = {
        id: 'test-max-retries-id',
        url: '/test/max-retries',
        method: 'POST',
        body: { test: true },
        headers: { 'Content-Type': 'application/json' },
        timestamp: Date.now(),
        retryCount: 5 // Assuming max retries is 5
      };
      
      const addMethod = Object.getOwnPropertyDescriptor(
        Object.getPrototypeOf(networkRecoveryService),
        'addToQueue'
      )?.value;
      
      if (addMethod) {
        await addMethod.call(networkRecoveryService, queueRequest);
      }
      
      // Advance timers to trigger request processing
      jest.advanceTimersByTime(500);
      
      // Verify fetch was attempted
      expect(mockFetch).toHaveBeenCalledTimes(1);
      
      // The request should be removed from queue after max retries
      const requests = networkRecoveryService.getQueuedRequests();
      expect(requests.length).toBe(0);
    });
  });
}); 