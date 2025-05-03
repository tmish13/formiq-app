import { Preferences } from '@capacitor/preferences';

// Define types
export interface UserProfile {
  id: string;
  name?: string;
  email?: string;
  [key: string]: any;
}

export interface AppSettings {
  theme?: string;
  notifications?: boolean;
  language?: string;
  [key: string]: any;
}

// Storage keys
const KEYS = {
  AUTH_TOKEN: 'formiq_auth_token',
  REFRESH_TOKEN: 'formiq_refresh_token',
  USER_PROFILE: 'formiq_user_profile',
  WORKOUT_QUEUE: 'formiq_workout_queue',
  FORM_ANALYSIS_CACHE: 'formiq_analysis_cache',
  SYNC_STATUS: 'formiq_sync_status',
  APP_SETTINGS: 'formiq_settings',
  TUTORIAL_COMPLETED: 'formiq_tutorial_completed',
  CSRF_TOKEN: 'formiq_csrf_token',
};

export class StorageService {
  private static instance: StorageService;

  private constructor() {}

  public static getInstance(): StorageService {
    if (!StorageService.instance) {
      StorageService.instance = new StorageService();
    }
    return StorageService.instance;
  }

  /**
   * Reset the singleton instance for testing purposes.
   * This should only be used in test environments.
   */
  public static resetInstance(): void {
    if (StorageService.instance) {
      // @ts-ignore - we're explicitly resetting for tests
      StorageService.instance = null;
    }
  }

  private async tryLocalStorage<T>(
    operation: () => T | null,
    fallback: () => Promise<T | null>,
    preferenceKey?: string
  ): Promise<T | null> {
    try {
      const result = operation();
      if (result !== null) {
        // If localStorage succeeds and we have a preference key, sync with Preferences
        if (preferenceKey) {
          await Preferences.set({ 
            key: preferenceKey, 
            value: typeof result === 'string' ? result : JSON.stringify(result)
          });
        }
        return result;
      }
      // If localStorage returns null, try Preferences
      return await fallback();
    } catch (error) {
      console.warn('localStorage operation failed, falling back to Preferences:', error);
      return await fallback();
    }
  }

  public async get(key: string): Promise<string | null> {
    return this.tryLocalStorage(
      () => localStorage.getItem(key),
      async () => {
        const { value } = await Preferences.get({ key });
        return value;
      },
      key
    );
  }

  public async set(key: string, value: string): Promise<void> {
    await this.tryLocalStorage(
      () => {
        localStorage.setItem(key, value);
        return undefined;
      },
      async () => {
        await Preferences.set({ key, value });
        return undefined;
      },
      key
    );
  }

  public async remove(key: string): Promise<void> {
    await this.tryLocalStorage(
      () => {
        localStorage.removeItem(key);
        return undefined;
      },
      async () => {
        await Preferences.remove({ key });
        return undefined;
      }
    );
  }

  public async clear(): Promise<void> {
    await this.tryLocalStorage(
      () => {
        localStorage.clear();
        return undefined;
      },
      async () => {
        await Preferences.clear();
        return undefined;
      }
    );
  }

  // Authentication data
  async setAuthToken(token: string): Promise<void> {
    await this.set(KEYS.AUTH_TOKEN, token);
  }

  async getAuthToken(): Promise<string | null> {
    return this.get(KEYS.AUTH_TOKEN);
  }

  async removeAuthToken(): Promise<void> {
    await this.remove(KEYS.AUTH_TOKEN);
  }

  // Refresh token management
  async setRefreshToken(token: string): Promise<void> {
    await this.set(KEYS.REFRESH_TOKEN, token);
  }

  async getRefreshToken(): Promise<string | null> {
    return this.get(KEYS.REFRESH_TOKEN);
  }

  async removeRefreshToken(): Promise<void> {
    await this.remove(KEYS.REFRESH_TOKEN);
  }

  // User profile
  async setUserProfile(profile: UserProfile): Promise<void> {
    await this.set(KEYS.USER_PROFILE, JSON.stringify(profile));
  }

  async getUserProfile(): Promise<UserProfile | null> {
    const value = await this.get(KEYS.USER_PROFILE);
    if (value) {
      try {
        return JSON.parse(value) as UserProfile;
      } catch (error) {
        console.error('Error parsing user profile:', error);
        return null;
      }
    }
    return null;
  }

  async removeUserProfile(): Promise<void> {
    await this.remove(KEYS.USER_PROFILE);
  }

  // Workout queue for offline operations
  async addToWorkoutQueue(workout: any): Promise<void> {
    const queue = await this.getWorkoutQueue();
    queue.push({ 
      ...workout, 
      queueId: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      queuedAt: new Date().toISOString() 
    });
    
    await this.set(KEYS.WORKOUT_QUEUE, JSON.stringify(queue));
  }

  async getWorkoutQueue(): Promise<any[]> {
    const value = await this.get(KEYS.WORKOUT_QUEUE);
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        console.error('Error parsing workout queue:', error);
        return [];
      }
    }
    return [];
  }

  async removeFromWorkoutQueue(queueId: string): Promise<void> {
    const queue = await this.getWorkoutQueue();
    const updatedQueue = queue.filter(item => item.queueId !== queueId);
    await this.set(KEYS.WORKOUT_QUEUE, JSON.stringify(updatedQueue));
  }

  async clearWorkoutQueue(): Promise<void> {
    await this.remove(KEYS.WORKOUT_QUEUE);
  }

  // Form analysis cache
  async cacheFormAnalysis(id: string, analysis: any): Promise<void> {
    const cache = await this.getFormAnalysisCache();
    cache[id] = {
      ...analysis,
      cachedAt: new Date().toISOString(),
    };
    
    await this.set(KEYS.FORM_ANALYSIS_CACHE, JSON.stringify(cache));
  }

  async getFormAnalysisCache(): Promise<Record<string, any>> {
    const value = await this.get(KEYS.FORM_ANALYSIS_CACHE);
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        console.error('Error parsing form analysis cache:', error);
        return {};
      }
    }
    return {};
  }

  async getFormAnalysis(id: string): Promise<any | null> {
    const cache = await this.getFormAnalysisCache();
    return cache[id] || null;
  }

  async clearFormAnalysisCache(): Promise<void> {
    await this.remove(KEYS.FORM_ANALYSIS_CACHE);
  }

  // Sync status
  async setSyncStatus(status: { lastSync: string; pending: number }): Promise<void> {
    await this.set(KEYS.SYNC_STATUS, JSON.stringify(status));
  }

  async getSyncStatus(): Promise<{ lastSync: string; pending: number } | null> {
    const value = await this.get(KEYS.SYNC_STATUS);
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        console.error('Error parsing sync status:', error);
        return null;
      }
    }
    return null;
  }

  // App settings
  async setAppSettings(settings: AppSettings): Promise<void> {
    await this.set(KEYS.APP_SETTINGS, JSON.stringify(settings));
  }

  async getAppSettings(): Promise<AppSettings | null> {
    const value = await this.get(KEYS.APP_SETTINGS);
    if (value) {
      try {
        return JSON.parse(value) as AppSettings;
      } catch (error) {
        console.error('Error parsing app settings:', error);
        return null;
      }
    }
    return null;
  }

  async removeAppSettings(): Promise<void> {
    await this.remove(KEYS.APP_SETTINGS);
  }

  // Tutorial completion status
  async setTutorialCompleted(completed: boolean): Promise<void> {
    await this.set(KEYS.TUTORIAL_COMPLETED, JSON.stringify(completed));
  }

  async getTutorialCompleted(): Promise<boolean> {
    const value = await this.get(KEYS.TUTORIAL_COMPLETED);
    if (value) {
      try {
        return JSON.parse(value);
      } catch (error) {
        console.error('Error parsing tutorial completion status:', error);
        return false;
      }
    }
    return false;
  }

  // CSRF token management
  async setCSRFToken(token: string): Promise<void> {
    await this.set(KEYS.CSRF_TOKEN, token);
  }

  async getCSRFToken(): Promise<string | null> {
    return this.get(KEYS.CSRF_TOKEN);
  }

  async removeCSRFToken(): Promise<void> {
    await this.remove(KEYS.CSRF_TOKEN);
  }

  // Clear all data
  async clearAll(): Promise<void> {
    await this.clear();
  }
}

export const storageService = StorageService.getInstance(); 