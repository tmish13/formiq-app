import { StorageService } from '../../../src/services/storageService';
import { Preferences } from '@capacitor/preferences';

// Create a proper localStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  
  return {
    getItem: jest.fn((key: string) => {
      return store[key] || null;
    }),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    key: jest.fn((index: number) => {
      return Object.keys(store)[index] || null;
    }),
    length: jest.fn(() => {
      return Object.keys(store).length;
    })
  };
})();

// Mock Capacitor Preferences
const mockPreferencesSet = jest.fn().mockResolvedValue(undefined);
const mockPreferencesGet = jest.fn().mockResolvedValue({ value: null });
const mockPreferencesRemove = jest.fn().mockResolvedValue(undefined);
const mockPreferencesClear = jest.fn().mockResolvedValue(undefined);

jest.mock('@capacitor/preferences', () => ({
  Preferences: {
    set: (...args: any[]) => mockPreferencesSet(...args),
    get: (...args: any[]) => mockPreferencesGet(...args),
    remove: (...args: any[]) => mockPreferencesRemove(...args),
    clear: (...args: any[]) => mockPreferencesClear(...args)
  }
}));

// Replace global localStorage with mock
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('StorageService', () => {
  let storageService: StorageService;

  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    
    // Reset localStorage
    localStorageMock.clear();
    
    // Reset Preferences mock default values
    mockPreferencesGet.mockReset().mockResolvedValue({ value: null });
    
    // Get singleton instance
    storageService = StorageService.getInstance();
  });

  describe('singleton pattern', () => {
    it('should return the same instance', () => {
      const instance1 = StorageService.getInstance();
      const instance2 = StorageService.getInstance();
      expect(instance1).toBe(instance2);
    });
  });

  describe('basic storage operations', () => {
    it('should set and get values', async () => {
      // Setup localStorage to return a value
      localStorageMock.getItem.mockReturnValueOnce('test-value');
      
      await storageService.set('test-key', 'test-value');
      const value = await storageService.get('test-key');
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('test-key', 'test-value');
      expect(value).toBe('test-value');
    });

    it('should remove values', async () => {
      await storageService.set('test-key', 'test-value');
      await storageService.remove('test-key');
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('test-key');
      
      // Mock localStorage to return null after removal
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      const value = await storageService.get('test-key');
      expect(value).toBeNull();
    });

    it('should clear all values', async () => {
      await storageService.set('key1', 'value1');
      await storageService.set('key2', 'value2');
      await storageService.clear();
      
      expect(localStorageMock.clear).toHaveBeenCalled();
      
      // Mock localStorage to return null after clearing
      localStorageMock.getItem.mockReturnValue(null);
      
      expect(await storageService.get('key1')).toBeNull();
      expect(await storageService.get('key2')).toBeNull();
    });

    it('should handle storage errors gracefully', async () => {
      // Mock localStorage.setItem to throw
      const mockError = new Error('Storage full');
      localStorageMock.setItem.mockImplementationOnce(() => {
        throw mockError;
      });

      // Should fall back to Preferences and not throw
      await expect(storageService.set('test-key', 'test-value')).resolves.toBeUndefined();
      
      // Should have attempted to use Preferences as fallback
      expect(mockPreferencesSet).toHaveBeenCalled();
    });
    
    it('should fall back to Preferences when localStorage fails to get', async () => {
      // Mock localStorage.getItem to throw
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Storage error');
      });
      
      // Mock Preferences to return a value
      mockPreferencesGet.mockResolvedValueOnce({ value: 'fallback-value' });
      
      const value = await storageService.get('test-key');
      
      // Should have fallen back to Preferences
      expect(mockPreferencesGet).toHaveBeenCalled();
      expect(value).toBe('fallback-value');
    });
  });

  describe('authentication data', () => {
    const mockToken = 'test-auth-token';

    beforeEach(() => {
      mockPreferencesGet.mockResolvedValue({ value: mockToken });
    });

    it('should set and get auth token', async () => {
      await storageService.setAuthToken(mockToken);
      
      // Verify token was stored in both localStorage and Preferences
      expect(localStorageMock.setItem).toHaveBeenCalledWith('formiq_auth_token', mockToken);
      expect(mockPreferencesSet).toHaveBeenCalledWith({
        key: 'formiq_auth_token',
        value: mockToken
      });

      // Mock localStorage to return the token
      localStorageMock.getItem.mockReturnValueOnce(mockToken);
      
      const token = await storageService.getAuthToken();
      expect(token).toBe(mockToken);
    });

    it('should set and get refresh token', async () => {
      await storageService.setRefreshToken(mockToken);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('formiq_refresh_token', mockToken);
      expect(mockPreferencesSet).toHaveBeenCalledWith({
        key: 'formiq_refresh_token',
        value: mockToken
      });

      // Mock localStorage to return the token
      localStorageMock.getItem.mockReturnValueOnce(mockToken);
      
      const token = await storageService.getRefreshToken();
      expect(token).toBe(mockToken);
    });

    it('should remove refresh token', async () => {
      await storageService.removeRefreshToken();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('formiq_refresh_token');
      expect(mockPreferencesRemove).toHaveBeenCalledWith({
        key: 'formiq_refresh_token'
      });
    });
    
    it('should fall back to Preferences for auth token when localStorage fails', async () => {
      // Mock localStorage.getItem to return null (not found in localStorage)
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      // Mock Preferences to return a token
      mockPreferencesGet.mockResolvedValueOnce({ value: mockToken });
      
      const token = await storageService.getAuthToken();
      
      // Should have fallen back to Preferences
      expect(mockPreferencesGet).toHaveBeenCalled();
      expect(token).toBe(mockToken);
    });
  });

  describe('user profile', () => {
    const mockProfile = {
      id: '123',
      name: 'Test User',
      email: 'test@example.com'
    };

    beforeEach(() => {
      mockPreferencesGet.mockResolvedValue({
        value: JSON.stringify(mockProfile)
      });
    });

    it('should set and get user profile', async () => {
      await storageService.setUserProfile(mockProfile);
      
      // Check that profile was stored in both storage mechanisms
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_user_profile', 
        JSON.stringify(mockProfile)
      );
      
      expect(mockPreferencesSet).toHaveBeenCalledWith({
        key: 'formiq_user_profile',
        value: JSON.stringify(mockProfile)
      });

      // Mock localStorage to return the profile
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockProfile));
      
      const profile = await storageService.getUserProfile();
      expect(profile).toEqual(mockProfile);
    });

    it('should handle null user profile', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      mockPreferencesGet.mockResolvedValueOnce({ value: null });
      
      const profile = await storageService.getUserProfile();
      expect(profile).toBeNull();
    });
    
    it('should handle malformed user profile JSON', async () => {
      // Mock localStorage to return invalid JSON
      localStorageMock.getItem.mockReturnValueOnce('{invalid-json}');
      
      // It should fall back to Preferences
      mockPreferencesGet.mockResolvedValueOnce({ value: JSON.stringify(mockProfile) });
      
      const profile = await storageService.getUserProfile();
      
      // Should have tried Preferences as fallback
      expect(mockPreferencesGet).toHaveBeenCalled();
      expect(profile).toEqual(mockProfile);
    });
  });

  describe('form analysis cache', () => {
    const mockCache = {
      'analysis-1': { data: 'test data' }
    };

    beforeEach(() => {
      // Mock localStorage to return the cache
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockCache));
    });

    it('should get form analysis cache', async () => {
      const cache = await storageService.getFormAnalysisCache();
      expect(cache).toEqual(mockCache);
    });

    it('should get specific form analysis', async () => {
      const analysis = await storageService.getFormAnalysis('analysis-1');
      expect(analysis).toEqual(mockCache['analysis-1']);
    });

    it('should return null for non-existent analysis', async () => {
      const analysis = await storageService.getFormAnalysis('non-existent');
      expect(analysis).toBeNull();
    });

    it('should return empty object when cache is empty', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      mockPreferencesGet.mockResolvedValueOnce({ value: null });
      
      const cache = await storageService.getFormAnalysisCache();
      expect(cache).toEqual({});
    });
    
    it('should store analysis in cache', async () => {
      const mockAnalysis = { data: 'new analysis' };
      
      // First get the existing cache
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockCache));
      
      // Either set directly in cache or add test implementation
      const cache = await storageService.getFormAnalysisCache();
      const updatedCache = {
        ...cache,
        'new-analysis': mockAnalysis
      };
      
      await storageService.set('formiq_analysis_cache', JSON.stringify(updatedCache));
      
      // Check that updated cache was stored
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_analysis_cache',
        expect.stringContaining('new-analysis')
      );
      
      // Verify the updated cache includes both the existing and new items
      const setCall = localStorageMock.setItem.mock.calls[0];
      const parsedCache = JSON.parse(setCall[1]);
      
      expect(parsedCache).toEqual({
        ...mockCache,
        'new-analysis': mockAnalysis
      });
    });
  });

  describe('sync status', () => {
    const mockStatus = {
      lastSync: '2024-04-14T10:00:00Z',
      pending: 5
    };

    beforeEach(() => {
      mockPreferencesGet.mockResolvedValue({
        value: JSON.stringify(mockStatus)
      });
    });

    it('should set and get sync status', async () => {
      await storageService.setSyncStatus(mockStatus);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_sync_status', 
        JSON.stringify(mockStatus)
      );
      
      expect(mockPreferencesSet).toHaveBeenCalledWith({
        key: 'formiq_sync_status',
        value: JSON.stringify(mockStatus)
      });

      // Mock localStorage to return the status
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockStatus));
      
      const status = await storageService.getSyncStatus();
      expect(status).toEqual(mockStatus);
    });

    it('should handle null sync status', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      mockPreferencesGet.mockResolvedValueOnce({ value: null });
      
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
      mockPreferencesGet.mockResolvedValue({
        value: JSON.stringify(mockSettings)
      });
    });

    it('should set and get app settings', async () => {
      await storageService.setAppSettings(mockSettings);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'formiq_settings', 
        JSON.stringify(mockSettings)
      );
      
      expect(mockPreferencesSet).toHaveBeenCalledWith({
        key: 'formiq_settings',
        value: JSON.stringify(mockSettings)
      });

      // Mock localStorage to return the settings
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(mockSettings));
      
      const settings = await storageService.getAppSettings();
      expect(settings).toEqual(mockSettings);
    });

    it('should handle null app settings', async () => {
      // Mock both storage mechanisms to return null
      localStorageMock.getItem.mockReturnValueOnce(null);
      mockPreferencesGet.mockResolvedValueOnce({ value: null });
      
      const settings = await storageService.getAppSettings();
      expect(settings).toBeNull();
    });
  });

  describe('CSRF token', () => {
    const mockToken = 'test-csrf-token';

    beforeEach(() => {
      mockPreferencesGet.mockResolvedValue({ value: mockToken });
    });

    it('should set and get CSRF token', async () => {
      await storageService.setCSRFToken(mockToken);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('formiq_csrf_token', mockToken);
      expect(mockPreferencesSet).toHaveBeenCalledWith({
        key: 'formiq_csrf_token',
        value: mockToken
      });

      // Mock localStorage to return the token
      localStorageMock.getItem.mockReturnValueOnce(mockToken);
      
      const token = await storageService.getCSRFToken();
      expect(token).toBe(mockToken);
    });

    it('should remove CSRF token', async () => {
      await storageService.removeCSRFToken();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('formiq_csrf_token');
      expect(mockPreferencesRemove).toHaveBeenCalledWith({
        key: 'formiq_csrf_token'
      });
    });
  });

  describe('clear all', () => {
    it('should clear all preferences', async () => {
      await storageService.clearAll();
      
      expect(localStorageMock.clear).toHaveBeenCalled();
      expect(mockPreferencesClear).toHaveBeenCalled();
    });
  });
}); 