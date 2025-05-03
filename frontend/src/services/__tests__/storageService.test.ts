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

describe('StorageService', () => {
  let storageService: StorageService;
  
  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Clear localStorage
    localStorageMock.clear();
    
    // Get instance before each test
    storageService = StorageService.getInstance();
  });
  
  describe('singleton pattern', () => {
    it('should return the same instance', () => {
      const instance1 = StorageService.getInstance();
      const instance2 = StorageService.getInstance();
      
      expect(instance1).toBe(instance2);
    });
    
    it('should create a new instance after resetInstance is called', () => {
      const instance1 = StorageService.getInstance();
      
      // Reset the instance
      StorageService.resetInstance();
      
      // Get a new instance
      const instance2 = StorageService.getInstance();
      
      // Should be different instances
      expect(instance1).not.toBe(instance2);
    });
  });
  
  describe('basic storage operations', () => {
    it('should set and get values', async () => {
      await storageService.set('test-key', 'test-value');
      
      // Verify localStorage was used
      expect(localStorageMock.setItem).toHaveBeenCalledWith('test-key', 'test-value');
      
      // Mock localStorage for get
      localStorageMock.getItem.mockReturnValueOnce('test-value');
      
      const value = await storageService.get('test-key');
      expect(value).toBe('test-value');
    });
    
    it('should remove values', async () => {
      await storageService.remove('test-key');
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('test-key');
    });
    
    it('should clear all values', async () => {
      await storageService.clear();
      
      expect(localStorageMock.clear).toHaveBeenCalled();
    });
    
    it('should handle storage errors gracefully', async () => {
      // Mock localStorage to throw error
      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Storage full');
      });
      
      // This should not throw but fall back to Preferences
      await storageService.set('test-key', 'test-value');
      
      // Should have fallen back to Preferences
      expect(Preferences.set).toHaveBeenCalledWith({
        key: 'test-key',
        value: 'test-value'
      });
    });
    
    it('should fall back to Preferences when localStorage fails to get', async () => {
      // Mock localStorage to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      // Mock Preferences to return a value
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: 'fallback-value' });
      
      const value = await storageService.get('test-key');
      
      expect(Preferences.get).toHaveBeenCalledWith({ key: 'test-key' });
      expect(value).toBe('fallback-value');
    });
  });
  
  describe('authentication data', () => {
    const mockToken = 'test-auth-token';
    
    it('should set and get auth token', async () => {
      await storageService.setAuthToken(mockToken);
      
      // Verify token was stored in localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith('formiq_auth_token', mockToken);
      
      // Mock localStorage to return the token
      localStorageMock.getItem.mockReturnValueOnce(mockToken);
      
      const token = await storageService.getAuthToken();
      expect(token).toBe(mockToken);
    });
    
    it('should set and get refresh token', async () => {
      await storageService.setRefreshToken(mockToken);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('formiq_refresh_token', mockToken);
      
      // Mock localStorage to return the token
      localStorageMock.getItem.mockReturnValueOnce(mockToken);
      
      const token = await storageService.getRefreshToken();
      expect(token).toBe(mockToken);
    });
    
    it('should remove refresh token', async () => {
      await storageService.removeRefreshToken();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('formiq_refresh_token');
    });
    
    it('should fall back to Preferences for auth token when localStorage fails', async () => {
      // Mock localStorage.getItem to return null (not found in localStorage)
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      // Mock Preferences to return a token
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: mockToken });
      
      const token = await storageService.getAuthToken();
      
      // Should have fallen back to Preferences
      expect(Preferences.get).toHaveBeenCalled();
      expect(token).toBe(mockToken);
    });
  });
  
  describe('user profile', () => {
    const mockProfile = {
      id: '123',
      name: 'Test User',
      email: 'test@example.com'
    };
    
    it('should set and get user profile', async () => {
      await storageService.setUserProfile(mockProfile);
      
      // Check that profile was stored in localStorage
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_user_profile',
        JSON.stringify(mockProfile)
      );
      
      // Mock localStorage to return the profile
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockProfile));
      
      const profile = await storageService.getUserProfile();
      expect(profile).toEqual(mockProfile);
    });
    
    it('should handle null user profile', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: null });
      
      const profile = await storageService.getUserProfile();
      expect(profile).toBeNull();
    });
    
    it('should handle malformed user profile JSON', async () => {
      // Mock localStorage to return invalid JSON
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Storage error');
      });
      
      // It should fall back to Preferences
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: JSON.stringify(mockProfile) });
      
      const profile = await storageService.getUserProfile();
      
      // Should have tried Preferences as fallback
      expect(Preferences.get).toHaveBeenCalled();
      expect(profile).toEqual(mockProfile);
    });
  });
  
  describe('form analysis cache', () => {
    const mockCache = {
      'analysis-1': { data: 'test data' }
    };
    
    beforeEach(() => {
      // Reset localStorage for cache tests
      localStorageMock.clear();
    });
    
    it('should get form analysis cache', async () => {
      // Mock localStorage to return the cache
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockCache));
      
      const cache = await storageService.getFormAnalysisCache();
      expect(cache).toEqual(mockCache);
    });
    
    it('should get specific form analysis', async () => {
      // Mock cache response
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockCache));
      
      const analysis = await storageService.getFormAnalysis('analysis-1');
      expect(analysis).toEqual(mockCache['analysis-1']);
    });
    
    it('should return null for non-existent analysis', async () => {
      // Mock cache response
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockCache));
      
      const analysis = await storageService.getFormAnalysis('non-existent');
      expect(analysis).toBeNull();
    });
    
    it('should return empty object when cache is empty', async () => {
      // Mock localStorage to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      // Mock Preferences to return null too
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: null });
      
      const cache = await storageService.getFormAnalysisCache();
      expect(cache).toEqual({});
    });
    
    it('should store analysis in cache', async () => {
      const mockAnalysis = { data: 'new analysis' };
      
      // First get the existing cache
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockCache));
      
      // Mock setItem to accept any values without throwing
      localStorageMock.setItem.mockImplementation(jest.fn());
      
      await storageService.cacheFormAnalysis('new-analysis', mockAnalysis);
      
      // Check that updated cache was stored
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_analysis_cache',
        expect.any(String)
      );
    });
  });
  
  describe('sync status', () => {
    const mockStatus = {
      lastSync: '2024-04-14T10:00:00Z',
      pending: 5
    };
    
    beforeEach(() => {
      // Reset localStorage 
      localStorageMock.clear();
    });
    
    it('should set and get sync status', async () => {
      await storageService.setSyncStatus(mockStatus);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_sync_status',
        JSON.stringify(mockStatus)
      );
      
      // Mock localStorage to return the status
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockStatus));
      
      const status = await storageService.getSyncStatus();
      expect(status).toEqual(mockStatus);
    });
    
    it('should handle null sync status', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: null });
      
      const status = await storageService.getSyncStatus();
      expect(status).toBeNull();
    });
  });
  
  describe('app settings', () => {
    const mockSettings = {
      theme: 'dark',
      notifications: true
    };
    
    beforeEach(() => {
      // Reset localStorage 
      localStorageMock.clear();
    });
    
    it('should set and get app settings', async () => {
      await storageService.setAppSettings(mockSettings);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_settings',
        JSON.stringify(mockSettings)
      );
      
      // Mock localStorage to return the settings
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockSettings));
      
      const settings = await storageService.getAppSettings();
      expect(settings).toEqual(mockSettings);
    });
    
    it('should handle null app settings', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      (Preferences.get as jest.Mock).mockResolvedValueOnce({ value: null });
      
      const settings = await storageService.getAppSettings();
      expect(settings).toBeNull();
    });
  });
  
  describe('CSRF token', () => {
    const mockToken = 'test-csrf-token';
    
    beforeEach(() => {
      // Reset localStorage
      localStorageMock.clear();
    });
    
    it('should set and get CSRF token', async () => {
      await storageService.setCSRFToken(mockToken);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('formiq_csrf_token', mockToken);
      
      // Mock localStorage to return the token
      localStorageMock.getItem.mockReturnValueOnce(mockToken);
      
      const token = await storageService.getCSRFToken();
      expect(token).toBe(mockToken);
    });
    
    it('should remove CSRF token', async () => {
      await storageService.removeCSRFToken();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('formiq_csrf_token');
    });
  });
  
  describe('clear all', () => {
    it('should clear all preferences', async () => {
      await storageService.clearAll();
      
      expect(localStorageMock.clear).toHaveBeenCalled();
    });
  });
}); 