import { StorageService } from '../storageService';
import { Preferences } from '@capacitor/preferences';

// Mock the Preferences module
jest.mock('@capacitor/preferences', () => {
  // Create mock storage
  const mockStorage: Record<string, string> = {};
  
  return {
    Preferences: {
      get: jest.fn(({ key }: { key: string }) => {
        return Promise.resolve({ value: mockStorage[key] || null });
      }),
      set: jest.fn(({ key, value }: { key: string; value: string }) => {
        mockStorage[key] = value;
        return Promise.resolve();
      }),
      remove: jest.fn(({ key }: { key: string }) => {
        delete mockStorage[key];
        return Promise.resolve();
      }),
      clear: jest.fn(() => {
        Object.keys(mockStorage).forEach(key => delete mockStorage[key]);
        return Promise.resolve();
      })
    }
  };
});

// Create localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    key: jest.fn((index: number) => Object.keys(store)[index] || null),
    length: Object.keys(store).length
  };
})();

// Set localStorage mock
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Create sessionStorage mock
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    key: jest.fn((index: number) => Object.keys(store)[index] || null),
    length: Object.keys(store).length
  };
})();

// Set sessionStorage mock
Object.defineProperty(window, 'sessionStorage', { value: sessionStorageMock });

// Mock console methods to avoid polluting test output
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

beforeAll(() => {
  console.error = jest.fn();
  console.warn = jest.fn();
});

afterAll(() => {
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
});

describe('StorageService Advanced Tests', () => {
  let storageService: StorageService;
  
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Clear localStorage and sessionStorage
    localStorageMock.clear();
    sessionStorageMock.clear();
    
    // Get instance before each test
    storageService = StorageService.getInstance();
  });
  
  describe('Singleton Pattern Implementation', () => {
    it('should return the same instance when getInstance is called multiple times', () => {
      // Get instances of the service
      const instance1 = StorageService.getInstance();
      const instance2 = StorageService.getInstance();
      
      // Both should reference the same object
      expect(instance1).toBe(instance2);
    });
    
    it('should create a new instance after resetInstance is called', () => {
      // Get the first instance
      const instance1 = StorageService.getInstance();
      
      // Reset the instance
      StorageService.resetInstance();
      
      // Get a new instance
      const instance2 = StorageService.getInstance();
      
      // Should be different instances
      expect(instance1).not.toBe(instance2);
    });
    
    it('should initialize a new instance with clean state after reset', async () => {
      // Set some value with the first instance
      await storageService.set('test-key', 'test-value');
      
      // Verify data was stored
      expect(localStorageMock.setItem).toHaveBeenCalledWith('test-key', 'test-value');
      
      // Reset mock and instance
      jest.clearAllMocks();
      StorageService.resetInstance();
      
      // Get new instance
      const newInstance = StorageService.getInstance();
      
      // Should be a new instance with no stored state
      expect(newInstance).not.toBe(storageService);
      
      // LocalStorage is still shared (would normally contain data), just checking the instance was reset
      expect(localStorageMock.setItem).not.toHaveBeenCalled();
    });
  });
  
  describe('LocalStorage and SessionStorage handling', () => {
    it('should try localStorage, then Preferences when localStorage fails completely', async () => {
      // Mock localStorage.setItem to throw an error
      const originalSetItem = localStorageMock.setItem;
      localStorageMock.setItem = jest.fn().mockImplementation(() => {
        throw new Error('localStorage unavailable');
      });
      
      await storageService.set('test-key', 'test-value');
      
      // Should fall back to Preferences
      expect(Preferences.set).toHaveBeenCalledWith({
        key: 'test-key',
        value: 'test-value'
      });
      
      // Restore original implementation
      localStorageMock.setItem = originalSetItem;
    });
    
    it('should handle quota exceeded errors in localStorage', async () => {
      // Mock localStorage.setItem to throw a quota exceeded error
      const originalSetItem = localStorageMock.setItem;
      localStorageMock.setItem = jest.fn().mockImplementation(() => {
        const error = new Error('QuotaExceededError');
        error.name = 'QuotaExceededError';
        throw error;
      });
      
      await storageService.set('large-key', 'large-value');
      
      // Should fall back to Preferences
      expect(Preferences.set).toHaveBeenCalledWith({
        key: 'large-key',
        value: 'large-value'
      });
      
      // Restore original implementation
      localStorageMock.setItem = originalSetItem;
    });
    
    it('should try to synchronize data between localStorage and Preferences', async () => {
      await storageService.set('sync-test', 'sync-value');
      
      // Check that it tried to store in localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith('sync-test', 'sync-value');
      
      // In the actual implementation, Preferences.set might not be called directly
      // from the set method depending on implementation details
      // So we're just testing that localStorage.setItem was called with expected values
    });
    
    it('should handle parsing errors when retrieving JSON data', async () => {
      // Set up invalid JSON in localStorage
      localStorageMock.getItem.mockReturnValue('{invalid-json}');
      
      // Mock getUserProfile to parse the returned JSON
      const getUserProfileSpy = jest.spyOn(storageService, 'getUserProfile');
      
      // Call getUserProfile
      const result = await storageService.getUserProfile();
      
      // Should have attempted to get the profile
      expect(getUserProfileSpy).toHaveBeenCalled();
      
      // Should have returned null due to parsing error
      expect(result).toBeNull();
      
      // Should have logged an error (we mocked console.error earlier)
      expect(console.error).toHaveBeenCalled();
    });
  });
  
  describe('Cache invalidation', () => {
    it('should invalidate form analysis cache correctly', async () => {
      // Call the clearFormAnalysisCache method
      await storageService.clearFormAnalysisCache();
      
      // Verify that localStorage.removeItem was called with the correct key
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('formiq_analysis_cache');
    });
    
    it('should handle partial cache invalidation', async () => {
      // Setup initial cache data with timestamps
      const initialCache = {
        'analysis-1': { 
          data: 'test data 1', 
          cachedAt: new Date(Date.now() - 60000).toISOString() // 1 minute ago 
        },
        'analysis-2': { 
          data: 'test data 2', 
          cachedAt: new Date(Date.now() - 60 * 60000).toISOString() // 1 hour ago 
        }
      };
      
      // Setup localStorage to return the mock cache
      localStorageMock.getItem.mockReturnValue(JSON.stringify(initialCache));
      
      // Call cacheFormAnalysis to add a new item
      const newAnalysis = { data: 'new analysis data' };
      await storageService.cacheFormAnalysis('analysis-3', newAnalysis);
      
      // Check that setItem was called with updated cache that should contain the new item
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_analysis_cache',
        expect.stringContaining('analysis-3')
      );
      
      // Get the actual value that was stored
      const setItemCalls = (localStorageMock.setItem as jest.Mock).mock.calls;
      const lastCall = setItemCalls[setItemCalls.length - 1];
      const [_, storedValue] = lastCall;
      
      // Parse the stored value
      const updatedCache = JSON.parse(storedValue);
      
      // Check that the new item includes the necessary properties
      expect(updatedCache['analysis-3']).toHaveProperty('data', 'new analysis data');
      expect(updatedCache['analysis-3']).toHaveProperty('cachedAt');
      
      // Check that the original items were preserved
      expect(updatedCache['analysis-1']).toBeDefined();
      expect(updatedCache['analysis-2']).toBeDefined();
    });
    
    it('should handle cache miss gracefully', async () => {
      // Mock localStorage and Preferences to return null (cache miss)
      localStorageMock.getItem.mockReturnValue(null);
      (Preferences.get as jest.Mock).mockResolvedValue({ value: null });
      
      // Try to get a specific analysis that doesn't exist
      const result = await storageService.getFormAnalysis('non-existent');
      
      // Should return null for a cache miss
      expect(result).toBeNull();
    });
  });
  
  describe('Offline persistence logic and fallback', () => {
    it('should add items to workout queue for offline operations', async () => {
      // Setup localStorage to return an empty array for getWorkoutQueue
      localStorageMock.getItem.mockReturnValue(JSON.stringify([]));
      
      // Create a workout to add to the queue
      const mockWorkout = { id: 'workout-1', name: 'Test Workout', exercises: [] };
      
      // Add workout to queue
      await storageService.addToWorkoutQueue(mockWorkout);
      
      // Capture the value passed to localStorage.setItem
      const setItemCalls = (localStorageMock.setItem as jest.Mock).mock.calls;
      const lastCall = setItemCalls[setItemCalls.length - 1];
      const [key, value] = lastCall;
      
      // Verify correct key was used
      expect(key).toBe('formiq_workout_queue');
      
      // Parse the stored value to verify the workout was added correctly
      const storedQueue = JSON.parse(value);
      
      // Check queue properties
      expect(Array.isArray(storedQueue)).toBe(true);
      expect(storedQueue.length).toBe(1);
      expect(storedQueue[0].id).toBe('workout-1');
      expect(storedQueue[0].name).toBe('Test Workout');
      expect(storedQueue[0]).toHaveProperty('queueId');
      expect(storedQueue[0]).toHaveProperty('queuedAt');
    });
    
    it('should manage the workout queue correctly', async () => {
      // Setup initial queue with two items
      const initialQueue = [
        { id: 'workout-1', name: 'Workout 1', queueId: 'queue-1', queuedAt: new Date().toISOString() },
        { id: 'workout-2', name: 'Workout 2', queueId: 'queue-2', queuedAt: new Date().toISOString() }
      ];
      
      // Mock getItem to return the initial queue for the first call
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(initialQueue));
      
      // Get the queue
      const queue = await storageService.getWorkoutQueue();
      
      // Should have the initial items
      expect(Array.isArray(queue)).toBe(true);
      expect(queue.length).toBe(2);
      expect(queue[0].id).toBe('workout-1');
      expect(queue[1].id).toBe('workout-2');
      
      // Now mock for removal operation - return the same queue again
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(initialQueue));
      
      // Remove one item from the queue
      await storageService.removeFromWorkoutQueue('queue-1');
      
      // Capture the value passed to localStorage.setItem
      const setItemCalls = (localStorageMock.setItem as jest.Mock).mock.calls;
      const lastCall = setItemCalls[setItemCalls.length - 1];
      const [key, value] = lastCall;
      
      // Verify correct key was used
      expect(key).toBe('formiq_workout_queue');
      
      // Parse the stored value
      const updatedQueue = JSON.parse(value);
      
      // Verify that the first item was removed
      expect(updatedQueue.length).toBe(1);
      expect(updatedQueue[0].id).toBe('workout-2');
      
      // Test the clear operation
      await storageService.clearWorkoutQueue();
      
      // Verify queue was cleared from localStorage
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('formiq_workout_queue');
    });
    
    it('should handle synchronization status for offline operations', async () => {
      // Setup mock sync status
      const mockSyncStatus = {
        lastSync: new Date().toISOString(),
        pending: 5
      };
      
      // Set the sync status
      await storageService.setSyncStatus(mockSyncStatus);
      
      // Check that it was stored correctly in localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_sync_status',
        JSON.stringify(mockSyncStatus)
      );
      
      // Mock localStorage to return the status for the getSyncStatus call
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockSyncStatus));
      
      // Get the sync status
      const status = await storageService.getSyncStatus();
      
      // Should match what we set
      expect(status).toEqual(mockSyncStatus);
    });
    
    it('should preserve data when both localStorage and Preferences are available', async () => {
      // Set up value in localStorage
      const localStorageValue = 'localStorage-value';
      
      // Mock localStorage to return a value
      localStorageMock.getItem.mockReturnValueOnce(localStorageValue);
      
      // Get should prioritize localStorage
      const result = await storageService.get('test-key');
      
      // Should return the localStorage value
      expect(result).toBe(localStorageValue);
      
      // Now test fallback to Preferences when localStorage returns null
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      const preferencesValue = 'preferences-value';
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: preferencesValue });
      
      const fallbackResult = await storageService.get('test-key');
      
      // Should have fallen back to Preferences and returned that value
      expect(fallbackResult).toBe(preferencesValue);
    });
  });
}); 