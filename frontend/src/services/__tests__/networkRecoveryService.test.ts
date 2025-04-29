// Increase timeout for all tests in this file
jest.setTimeout(30000);

import { NetworkRecoveryService } from '../networkRecovery';
import { StorageService } from '../storageService';

jest.mock('../storageService');

describe('NetworkRecoveryService', () => {
  let service: NetworkRecoveryService;
  let mockStorageService: jest.Mocked<StorageService>;

  beforeAll(() => {
    jest.useFakeTimers();
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  beforeEach(async () => {
    // Clear the singleton instance before each test
    (NetworkRecoveryService as any).instance = undefined;
    
    // Setup mock storage service with proper implementation
    mockStorageService = {
      get: jest.fn().mockImplementation(async (key: string) => {
        if (key === 'pending_requests') {
          return JSON.stringify([
            {
              id: '1',
              url: 'http://test.com',
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: { test: true },
              timestamp: Date.now(),
              retryCount: 0
            }
          ]);
        }
        return null;
      }),
      set: jest.fn().mockResolvedValue(undefined),
      remove: jest.fn().mockResolvedValue(undefined),
      clear: jest.fn().mockResolvedValue(undefined),
      getInstance: jest.fn().mockReturnThis()
    } as any;

    (StorageService.getInstance as jest.Mock).mockReturnValue(mockStorageService);
    
    // Get service instance and wait for initialization
    service = NetworkRecoveryService.getInstance();
    // Advance timers instead of using real timeout
    jest.advanceTimersByTime(100);
  });

  afterEach(() => {
    service.destroy();
    jest.clearAllMocks();
    jest.clearAllTimers();
  });

  describe('initialization', () => {
    it('should initialize with online status', async () => {
      expect(service.isNetworkOnline()).toBe(true);
      expect(mockStorageService.get).toHaveBeenCalledWith('pending_requests');
    });

    it('should load pending requests from storage', async () => {
      const mockRequests = [
        {
          id: '1',
          url: 'http://test.com',
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: { test: true },
          timestamp: Date.now(),
          retryCount: 0
        }
      ];
      
      expect(mockStorageService.get).toHaveBeenCalledWith('pending_requests');
      expect(service.getQueuedRequests()).toEqual(mockRequests);
    });
  });

  describe('queue management', () => {
    it('should queue a request when offline', async () => {
      // Mock offline status
      Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
      
      const request = {
        id: '1',
        url: 'http://test.com',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: { test: true },
        timestamp: Date.now(),
        retryCount: 0
      };
      
      await service.queueRequest(request);
      
      expect(service.getQueuedRequests()).toHaveLength(1);
      expect(service.getQueuedRequests()[0]).toMatchObject({
        url: request.url,
        method: request.method,
        headers: request.headers,
        body: request.body
      });
    });

    it('should process queue when coming back online', async () => {
      // Mock offline status
      Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
      
      const request = {
        id: '1',
        url: 'http://test.com',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: { test: true },
        timestamp: Date.now(),
        retryCount: 0
      };
      
      await service.queueRequest(request);
      
      // Mock online status
      Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
      
      // Trigger online event
      window.dispatchEvent(new Event('online'));
      
      // Advance timers instead of using real timeout
      jest.advanceTimersByTime(100);
      
      expect(service.getQueuedRequests()).toHaveLength(0);
    });

    it('should retry failed requests with exponential backoff', async () => {
      // Mock offline status
      Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
      
      const request = {
        id: '1',
        url: 'http://test.com',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: { test: true },
        timestamp: Date.now(),
        retryCount: 0
      };
      
      // Mock fetch to fail
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
      
      await service.queueRequest(request);
      
      // First retry after 5 seconds
      jest.advanceTimersByTime(5000);
      expect(service.getQueuedRequests()[0].retryCount).toBe(1);
      
      // Second retry after 10 seconds
      jest.advanceTimersByTime(10000);
      expect(service.getQueuedRequests()[0].retryCount).toBe(2);
      
      // Third retry after 20 seconds
      jest.advanceTimersByTime(20000);
      expect(service.getQueuedRequests()[0].retryCount).toBe(3);
    });
  });

  describe('event handling', () => {
    it('should emit events when queueing requests', async () => {
      const mockListener = jest.fn();
      service.on('request-queued', mockListener);
      
      const request = {
        id: '1',
        url: 'http://test.com',
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: { test: true },
        timestamp: Date.now(),
        retryCount: 0
      };
      
      await service.queueRequest(request);
      
      expect(mockListener).toHaveBeenCalledWith(expect.objectContaining({
        url: request.url,
        method: request.method
      }));
    });
  });
}); 