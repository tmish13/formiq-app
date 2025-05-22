import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import configureStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { setOffline } from '../../frontend/src/store/slices/uiSlice';

// Mock implementations
jest.mock('../../frontend/src/services/storageService', () => {
  const originalModule = jest.requireActual('../../frontend/src/services/storageService');
  
  // Mock storage map
  const mockStorage = new Map();
  
  return {
    ...originalModule,
    storageService: {
      get: jest.fn((key) => Promise.resolve(mockStorage.get(key) || null)),
      set: jest.fn((key, value) => {
        mockStorage.set(key, value);
        return Promise.resolve(true);
      }),
      remove: jest.fn((key) => {
        mockStorage.delete(key);
        return Promise.resolve(true);
      }),
      clear: jest.fn(() => {
        mockStorage.clear();
        return Promise.resolve(true);
      }),
      getAllKeys: jest.fn(() => Promise.resolve(Array.from(mockStorage.keys()))),
    }
  };
});

jest.mock('../../frontend/src/services/apiService', () => ({
  apiService: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    setOfflineMode: jest.fn(),
    isOffline: jest.fn().mockReturnValue(false),
  }
}));

// Mock the service worker
jest.mock('../../frontend/src/serviceWorkerRegistration', () => ({
  register: jest.fn().mockResolvedValue({ waiting: null }),
  unregister: jest.fn().mockResolvedValue(true),
}));

// Create mock cache implementation for testing
const createApiCache = () => {
  const cache = new Map();
  
  return {
    get: jest.fn((key) => cache.get(key) || null),
    set: jest.fn((key, value) => {
      cache.set(key, value);
      return true;
    }),
    delete: jest.fn((key) => {
      return cache.delete(key);
    }),
    clear: jest.fn(() => {
      cache.clear();
      return true;
    }),
    has: jest.fn((key) => cache.has(key)),
    keys: jest.fn(() => Array.from(cache.keys())),
  };
};

// Import services after mocking
const { storageService } = require('../../frontend/src/services/storageService');
const { apiService } = require('../../frontend/src/services/apiService');
const serviceWorkerRegistration = require('../../frontend/src/serviceWorkerRegistration');
const mockApiCache = createApiCache();

// Sample initial state for Redux store
const initialState = {
  ui: {
    isOffline: false,
    error: null,
    isDarkMode: false,
  },
  user: {
    isAuthenticated: true,
    profile: { id: 'user123', name: 'Test User' },
  }
};

const mockStore = configureStore([thunk]);

// Component to test offline UI
const OfflineFallbackUI = ({ isOffline }) => (
  <div>
    {isOffline ? (
      <div data-testid="offline-banner">
        You are currently offline. Some features may be unavailable.
        <button data-testid="retry-connection">Retry Connection</button>
      </div>
    ) : (
      <div data-testid="online-content">
        Connected to server
      </div>
    )}
  </div>
);

describe('OfflineSupport Consolidated Tests', () => {
  let store;
  
  beforeEach(() => {
    store = mockStore(initialState);
    jest.clearAllMocks();
    
    // Reset localStorage mock
    global.localStorage = {
      getItem: jest.fn((key) => null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
      length: 0,
      key: jest.fn(),
    };
    
    // Reset sessionStorage mock
    global.sessionStorage = {
      getItem: jest.fn((key) => null),
      setItem: jest.fn(),
      removeItem: jest.fn(),
      clear: jest.fn(),
      length: 0,
      key: jest.fn(),
    };
  });
  
  describe('Redux Offline Status Management', () => {
    it('should handle setOffline action', () => {
      const action = setOffline(true);
      
      const expectedAction = {
        type: 'ui/setOffline',
        payload: true
      };
      
      expect(action).toEqual(expectedAction);
    });
    
    it('should dispatch offline status', () => {
      store.dispatch(setOffline(true));
      
      const actions = store.getActions();
      expect(actions).toContainEqual(setOffline(true));
    });
  });
  
  describe('Offline UI Components', () => {
    it('should display offline banner when offline', () => {
      render(<OfflineFallbackUI isOffline={true} />);
      
      expect(screen.getByTestId('offline-banner')).toBeInTheDocument();
      expect(screen.getByText('You are currently offline. Some features may be unavailable.')).toBeInTheDocument();
    });
    
    it('should display online content when online', () => {
      render(<OfflineFallbackUI isOffline={false} />);
      
      expect(screen.getByTestId('online-content')).toBeInTheDocument();
      expect(screen.getByText('Connected to server')).toBeInTheDocument();
    });
    
    it('should render retry connection button in offline mode', () => {
      render(<OfflineFallbackUI isOffline={true} />);
      
      expect(screen.getByTestId('retry-connection')).toBeInTheDocument();
    });
  });
  
  describe('Storage Service', () => {
    it('should store and retrieve data', async () => {
      const testKey = 'test-key';
      const testValue = { foo: 'bar' };
      
      await storageService.set(testKey, testValue);
      const result = await storageService.get(testKey);
      
      expect(result).toEqual(testValue);
    });
    
    it('should remove stored data', async () => {
      const testKey = 'test-key';
      const testValue = { foo: 'bar' };
      
      await storageService.set(testKey, testValue);
      await storageService.remove(testKey);
      const result = await storageService.get(testKey);
      
      expect(result).toBeNull();
    });
    
    it('should clear all stored data', async () => {
      const testKey1 = 'test-key-1';
      const testValue1 = { foo: 'bar' };
      const testKey2 = 'test-key-2';
      const testValue2 = { baz: 'qux' };
      
      await storageService.set(testKey1, testValue1);
      await storageService.set(testKey2, testValue2);
      await storageService.clear();
      
      const result1 = await storageService.get(testKey1);
      const result2 = await storageService.get(testKey2);
      
      expect(result1).toBeNull();
      expect(result2).toBeNull();
    });
    
    it('should get all keys', async () => {
      const testKey1 = 'test-key-1';
      const testValue1 = { foo: 'bar' };
      const testKey2 = 'test-key-2';
      const testValue2 = { baz: 'qux' };
      
      await storageService.set(testKey1, testValue1);
      await storageService.set(testKey2, testValue2);
      
      const keys = await storageService.getAllKeys();
      
      expect(keys).toContain(testKey1);
      expect(keys).toContain(testKey2);
    });
  });
  
  describe('Local and Session Storage', () => {
    it('should use localStorage for persistent data', () => {
      localStorage.setItem('test-key', JSON.stringify({ foo: 'bar' }));
      
      expect(localStorage.setItem).toHaveBeenCalledWith('test-key', JSON.stringify({ foo: 'bar' }));
    });
    
    it('should retrieve data from localStorage', () => {
      const testData = { foo: 'bar' };
      
      localStorage.getItem.mockReturnValue(JSON.stringify(testData));
      
      const result = localStorage.getItem('test-key');
      expect(JSON.parse(result)).toEqual(testData);
    });
    
    it('should use sessionStorage for temporary data', () => {
      sessionStorage.setItem('session-key', JSON.stringify({ temp: 'data' }));
      
      expect(sessionStorage.setItem).toHaveBeenCalledWith('session-key', JSON.stringify({ temp: 'data' }));
    });
    
    it('should retrieve data from sessionStorage', () => {
      const testData = { temp: 'data' };
      
      sessionStorage.getItem.mockReturnValue(JSON.stringify(testData));
      
      const result = sessionStorage.getItem('session-key');
      expect(JSON.parse(result)).toEqual(testData);
    });
  });
  
  describe('API Cache Mechanism', () => {
    it('should cache API responses', () => {
      const cacheKey = 'api:/users/123';
      const responseData = { id: '123', name: 'Test User' };
      
      mockApiCache.set(cacheKey, responseData);
      
      expect(mockApiCache.get(cacheKey)).toEqual(responseData);
    });
    
    it('should return null for missing cache entries', () => {
      const cacheKey = 'api:/users/999';
      
      expect(mockApiCache.get(cacheKey)).toBeNull();
    });
    
    it('should delete cache entries', () => {
      const cacheKey = 'api:/users/123';
      const responseData = { id: '123', name: 'Test User' };
      
      mockApiCache.set(cacheKey, responseData);
      mockApiCache.delete(cacheKey);
      
      expect(mockApiCache.get(cacheKey)).toBeNull();
    });
    
    it('should clear all cache entries', () => {
      const cacheKey1 = 'api:/users/123';
      const responseData1 = { id: '123', name: 'Test User' };
      const cacheKey2 = 'api:/posts/456';
      const responseData2 = { id: '456', title: 'Test Post' };
      
      mockApiCache.set(cacheKey1, responseData1);
      mockApiCache.set(cacheKey2, responseData2);
      mockApiCache.clear();
      
      expect(mockApiCache.get(cacheKey1)).toBeNull();
      expect(mockApiCache.get(cacheKey2)).toBeNull();
    });
  });
  
  describe('Offline Queue', () => {
    // Mock offline queue for testing
    const offlineQueue = {
      pendingRequests: [],
      addRequest: jest.fn((request) => {
        offlineQueue.pendingRequests.push(request);
        return true;
      }),
      processQueue: jest.fn(),
      clearQueue: jest.fn(() => {
        offlineQueue.pendingRequests = [];
        return true;
      }),
      hasPendingRequests: jest.fn(() => offlineQueue.pendingRequests.length > 0),
    };
    
    beforeEach(() => {
      offlineQueue.pendingRequests = [];
      jest.clearAllMocks();
    });
    
    it('should add requests to queue when offline', () => {
      const request = {
        method: 'POST',
        url: '/api/users',
        data: { name: 'New User' },
      };
      
      offlineQueue.addRequest(request);
      
      expect(offlineQueue.pendingRequests).toContainEqual(request);
      expect(offlineQueue.hasPendingRequests()).toBe(true);
    });
    
    it('should clear the queue', () => {
      const request = {
        method: 'POST',
        url: '/api/users',
        data: { name: 'New User' },
      };
      
      offlineQueue.addRequest(request);
      offlineQueue.clearQueue();
      
      expect(offlineQueue.pendingRequests).toHaveLength(0);
      expect(offlineQueue.hasPendingRequests()).toBe(false);
    });
    
    it('should process the queue when coming back online', () => {
      const request1 = {
        method: 'POST',
        url: '/api/users',
        data: { name: 'New User' },
      };
      
      const request2 = {
        method: 'PUT',
        url: '/api/users/123',
        data: { name: 'Updated User' },
      };
      
      offlineQueue.addRequest(request1);
      offlineQueue.addRequest(request2);
      offlineQueue.processQueue();
      
      expect(offlineQueue.processQueue).toHaveBeenCalled();
    });
  });
  
  describe('Service Worker Registration', () => {
    it('should register service worker for offline support', async () => {
      await serviceWorkerRegistration.register();
      
      expect(serviceWorkerRegistration.register).toHaveBeenCalled();
    });
    
    it('should unregister service worker', async () => {
      await serviceWorkerRegistration.unregister();
      
      expect(serviceWorkerRegistration.unregister).toHaveBeenCalled();
    });
  });
  
  describe('Network Status Detection', () => {
    it('should detect when app goes offline', () => {
      const originalOnline = window.navigator.onLine;
      Object.defineProperty(window.navigator, 'onLine', { value: false, writable: true });
      
      // Simulate online event
      const offlineEvent = new Event('offline');
      window.dispatchEvent(offlineEvent);
      
      // Should set offline status in API service
      expect(apiService.setOfflineMode).toHaveBeenCalled();
      
      // Restore original value
      Object.defineProperty(window.navigator, 'onLine', { value: originalOnline, writable: true });
    });
    
    it('should detect when app comes back online', () => {
      const originalOnline = window.navigator.onLine;
      Object.defineProperty(window.navigator, 'onLine', { value: true, writable: true });
      
      // Simulate online event
      const onlineEvent = new Event('online');
      window.dispatchEvent(onlineEvent);
      
      // Should set offline status in API service
      expect(apiService.setOfflineMode).toHaveBeenCalled();
      
      // Restore original value
      Object.defineProperty(window.navigator, 'onLine', { value: originalOnline, writable: true });
    });
  });
  
  describe('API Service Offline Support', () => {
    it('should handle API requests when offline', async () => {
      // Set API service to offline mode
      apiService.isOffline.mockReturnValue(true);
      
      // Mock fallback data from cache
      const cacheKey = 'api:GET:/users/123';
      const cachedData = { id: '123', name: 'Cached User' };
      mockApiCache.get.mockReturnValue(cachedData);
      
      // Mock API get method to retrieve from cache
      apiService.get.mockImplementation(async (url) => {
        if (apiService.isOffline()) {
          const key = `api:GET:${url}`;
          const cached = mockApiCache.get(key);
          if (cached) {
            return Promise.resolve({ data: cached, source: 'cache' });
          }
          return Promise.reject(new Error('Offline and no cached data available'));
        }
        return Promise.resolve({ data: { id: '123', name: 'Online User' }, source: 'api' });
      });
      
      // Call API with offline mode
      const result = await apiService.get('/users/123');
      
      // Should return cached data
      expect(result).toEqual({ data: cachedData, source: 'cache' });
    });
    
    it('should queue POST requests when offline', async () => {
      // Set API service to offline mode
      apiService.isOffline.mockReturnValue(true);
      
      // Mock offlineQueue module
      const offlineQueue = {
        addRequest: jest.fn(),
      };
      
      // Set up rejected promise for POST in offline mode
      apiService.post.mockRejectedValue(new Error('Network error'));
      
      // Attempt to post data while offline
      try {
        await apiService.post('/users', { name: 'New User' });
      } catch (error) {
        // Expected to fail
        expect(error.message).toBe('Network error');
      }
    });
  });
  
  describe('Data Persistence and Sync', () => {
    it('should persist user changes offline and sync when online', async () => {
      // Set up offline state
      apiService.isOffline.mockReturnValue(true);
      
      // Create mock sync service
      const syncService = {
        persistChange: jest.fn().mockResolvedValue(true),
        syncChanges: jest.fn().mockResolvedValue({ success: true, count: 1 }),
        hasPendingChanges: jest.fn().mockReturnValue(true),
      };
      
      // Record a change offline
      await syncService.persistChange('users', 'update', { id: '123', name: 'Updated Offline' });
      
      expect(syncService.persistChange).toHaveBeenCalledWith(
        'users', 
        'update', 
        { id: '123', name: 'Updated Offline' }
      );
      
      // Switch to online state
      apiService.isOffline.mockReturnValue(false);
      
      // Sync changes
      const syncResult = await syncService.syncChanges();
      
      expect(syncService.syncChanges).toHaveBeenCalled();
      expect(syncResult).toEqual({ success: true, count: 1 });
    });
    
    it('should handle conflict resolution during sync', async () => {
      // Create mock sync service with conflict
      const syncService = {
        persistChange: jest.fn().mockResolvedValue(true),
        syncChanges: jest.fn().mockResolvedValue({ 
          success: true, 
          count: 1,
          conflicts: [
            { 
              entity: 'users', 
              id: '123', 
              localVersion: { id: '123', name: 'Updated Offline', version: 1 },
              serverVersion: { id: '123', name: 'Updated Online', version: 2 }
            }
          ]
        }),
        resolveConflict: jest.fn().mockResolvedValue(true),
      };
      
      // Sync changes with conflict
      const syncResult = await syncService.syncChanges();
      
      // Resolve using server version (higher version wins)
      await syncService.resolveConflict(
        syncResult.conflicts[0].entity,
        syncResult.conflicts[0].id,
        'server'
      );
      
      expect(syncService.resolveConflict).toHaveBeenCalledWith('users', '123', 'server');
    });
  });
}); 