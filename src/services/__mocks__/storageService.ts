// Mock storage data for tests
const mockStorage = {
  'formiq_analysis_cache': JSON.stringify({
    'analysis-1': { data: 'test data' }
  }),
  'formiq_sync_status': JSON.stringify({
    lastSync: '2024-04-14T10:00:00Z',
    pending: 5
  }),
  'formiq_settings': JSON.stringify({
    theme: 'dark',
    notifications: true
  }),
  'formiq_csrf_token': 'test-csrf-token'
};

// Create a singleton mock class with the same interface as the real service
class MockStorageService {
  private static instance: MockStorageService;
  
  private constructor() {}
  
  public static getInstance(): MockStorageService {
    if (!MockStorageService.instance) {
      MockStorageService.instance = new MockStorageService();
    }
    return MockStorageService.instance;
  }

  async get(key: string): Promise<string | null> {
    return Promise.resolve(mockStorage[key] || null);
  }

  async set(key: string, value: string): Promise<void> {
    mockStorage[key] = value;
    return Promise.resolve();
  }

  async remove(key: string): Promise<void> {
    delete mockStorage[key];
    return Promise.resolve();
  }

  async clear(): Promise<void> {
    Object.keys(mockStorage).forEach(key => {
      delete mockStorage[key];
    });
    return Promise.resolve();
  }

  // Auth token methods
  async setAuthToken(token: string): Promise<void> {
    return this.set('formiq_auth_token', token);
  }

  async getAuthToken(): Promise<string | null> {
    return this.get('formiq_auth_token');
  }

  async removeAuthToken(): Promise<void> {
    return this.remove('formiq_auth_token');
  }

  // Refresh token methods
  async setRefreshToken(token: string): Promise<void> {
    return this.set('formiq_refresh_token', token);
  }

  async getRefreshToken(): Promise<string | null> {
    return this.get('formiq_refresh_token');
  }

  async removeRefreshToken(): Promise<void> {
    return this.remove('formiq_refresh_token');
  }

  // User profile methods
  async setUserProfile(profile: any): Promise<void> {
    return this.set('formiq_user_profile', JSON.stringify(profile));
  }

  async getUserProfile(): Promise<any | null> {
    const value = await this.get('formiq_user_profile');
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        return null;
      }
    }
    return null;
  }

  async removeUserProfile(): Promise<void> {
    return this.remove('formiq_user_profile');
  }

  // Form analysis cache methods
  async getFormAnalysisCache(): Promise<Record<string, any>> {
    const value = await this.get('formiq_analysis_cache');
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        return {};
      }
    }
    return {};
  }

  async getFormAnalysis(id: string): Promise<any | null> {
    const cache = await this.getFormAnalysisCache();
    return cache[id] || null;
  }

  async cacheFormAnalysis(id: string, analysis: any): Promise<void> {
    const cache = await this.getFormAnalysisCache();
    cache[id] = {
      ...analysis,
      cachedAt: new Date().toISOString(),
    };
    
    return this.set('formiq_analysis_cache', JSON.stringify(cache));
  }

  // Sync status methods
  async setSyncStatus(status: any): Promise<void> {
    return this.set('formiq_sync_status', JSON.stringify(status));
  }

  async getSyncStatus(): Promise<any | null> {
    const value = await this.get('formiq_sync_status');
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        return null;
      }
    }
    return null;
  }

  // App settings methods
  async setAppSettings(settings: any): Promise<void> {
    return this.set('formiq_settings', JSON.stringify(settings));
  }

  async getAppSettings(): Promise<any | null> {
    const value = await this.get('formiq_settings');
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        return null;
      }
    }
    return null;
  }

  // CSRF token methods
  async setCSRFToken(token: string): Promise<void> {
    return this.set('formiq_csrf_token', token);
  }

  async getCSRFToken(): Promise<string | null> {
    return this.get('formiq_csrf_token');
  }

  async removeCSRFToken(): Promise<void> {
    return this.remove('formiq_csrf_token');
  }

  async clearAll(): Promise<void> {
    return this.clear();
  }
}

export const StorageService = {
  getInstance: () => MockStorageService.getInstance()
};

export default StorageService; 