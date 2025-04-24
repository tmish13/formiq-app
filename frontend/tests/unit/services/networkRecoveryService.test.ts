import { NetworkRecoveryService } from '../../../src/services/networkRecovery';
import { StorageService } from '../../../src/services/storageService';

jest.mock('../../../src/services/storageService');

describe('NetworkRecoveryService', () => {
  let service: NetworkRecoveryService;
  let mockStorageService: jest.Mocked<StorageService>;

  beforeEach(async () => {
    // Clear the singleton instance before each test
    (NetworkRecoveryService as any).instance = undefined;
    
    // Setup mock storage service
    mockStorageService = {
      get: jest.fn().mockResolvedValue(null),
      set: jest.fn().mockResolvedValue(undefined),
      remove: jest.fn().mockResolvedValue(undefined),
      clear: jest.fn().mockResolvedValue(undefined),
      getInstance: jest.fn().mockReturnThis()
    } as any;

    (StorageService.getInstance as jest.Mock).mockReturnValue(mockStorageService);
    
    // Get service instance and wait for initialization
    service = NetworkRecoveryService.getInstance();
    // Wait for any pending promises to resolve
    await new Promise(resolve => setTimeout(resolve, 0));
  });

  afterEach(() => {
    service.destroy();
    jest.clearAllMocks();
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
      
      mockStorageService.get.mockResolvedValue(JSON.stringify(mockRequests));
      
      // Create new instance to trigger initialization with mock data
      service = NetworkRecoveryService.getInstance();
      await new Promise(resolve => setTimeout(resolve, 0));
      
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
      expect(service.getQueuedRequests()).toContainEqual(expect.objectContaining({
        url: request.url,
        method: request.method
      }));
      expect(mockStorageService.set).toHaveBeenCalledWith('pending_requests', expect.any(String));
    }, 15000);

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
      
      // Mock coming back online
      Object.defineProperty(navigator, 'onLine', { value: true, configurable: true });
      window.dispatchEvent(new Event('online'));
      
      // Wait for queue processing
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(service.getQueuedRequests()).toHaveLength(0);
      expect(mockStorageService.remove).toHaveBeenCalledWith('pending_requests');
    }, 15000);
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
    }, 15000);
  });
}); 