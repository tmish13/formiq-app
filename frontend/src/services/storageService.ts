import { Preferences } from '@capacitor/preferences';

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

  public async get(key: string): Promise<string | null> {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.error('Error reading from storage:', error);
      return null;
    }
  }

  public async set(key: string, value: string): Promise<void> {
    try {
      localStorage.setItem(key, value);
    } catch (error) {
      console.error('Error writing to storage:', error);
    }
  }

  public async remove(key: string): Promise<void> {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from storage:', error);
    }
  }

  public async clear(): Promise<void> {
    try {
      localStorage.clear();
    } catch (error) {
      console.error('Error clearing storage:', error);
    }
  }

  // Authentication data
  async setAuthToken(token: string): Promise<void> {
    await Preferences.set({
      key: KEYS.AUTH_TOKEN,
      value: token,
    });
  }

  async getAuthToken(): Promise<string | null> {
    const { value } = await Preferences.get({ key: KEYS.AUTH_TOKEN });
    return value;
  }

  async removeAuthToken(): Promise<void> {
    await Preferences.remove({ key: KEYS.AUTH_TOKEN });
  }

  // Refresh token management
  async setRefreshToken(token: string): Promise<void> {
    await Preferences.set({
      key: KEYS.REFRESH_TOKEN,
      value: token,
    });
  }

  async getRefreshToken(): Promise<string | null> {
    const { value } = await Preferences.get({ key: KEYS.REFRESH_TOKEN });
    return value;
  }

  async removeRefreshToken(): Promise<void> {
    await Preferences.remove({ key: KEYS.REFRESH_TOKEN });
  }

  // User profile
  async setUserProfile(profile: any): Promise<void> {
    await Preferences.set({
      key: KEYS.USER_PROFILE,
      value: JSON.stringify(profile),
    });
  }

  async getUserProfile(): Promise<any | null> {
    const { value } = await Preferences.get({ key: KEYS.USER_PROFILE });
    if (value) {
      return JSON.parse(value);
    }
    return null;
  }

  // Workout queue for offline operations
  async addToWorkoutQueue(workout: any): Promise<void> {
    const queue = await this.getWorkoutQueue();
    queue.push({ 
      ...workout, 
      queueId: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      queuedAt: new Date().toISOString() 
    });
    
    await Preferences.set({
      key: KEYS.WORKOUT_QUEUE,
      value: JSON.stringify(queue),
    });
  }

  async getWorkoutQueue(): Promise<any[]> {
    const { value } = await Preferences.get({ key: KEYS.WORKOUT_QUEUE });
    if (value) {
      return JSON.parse(value);
    }
    return [];
  }

  async removeFromWorkoutQueue(queueId: string): Promise<void> {
    const queue = await this.getWorkoutQueue();
    const updatedQueue = queue.filter(item => item.queueId !== queueId);
    
    await Preferences.set({
      key: KEYS.WORKOUT_QUEUE,
      value: JSON.stringify(updatedQueue),
    });
  }

  async clearWorkoutQueue(): Promise<void> {
    await Preferences.remove({ key: KEYS.WORKOUT_QUEUE });
  }

  // Form analysis cache
  async cacheFormAnalysis(id: string, analysis: any): Promise<void> {
    const cache = await this.getFormAnalysisCache();
    cache[id] = {
      ...analysis,
      cachedAt: new Date().toISOString(),
    };
    
    await Preferences.set({
      key: KEYS.FORM_ANALYSIS_CACHE,
      value: JSON.stringify(cache),
    });
  }

  async getFormAnalysisCache(): Promise<Record<string, any>> {
    const { value } = await Preferences.get({ key: KEYS.FORM_ANALYSIS_CACHE });
    if (value) {
      return JSON.parse(value);
    }
    return {};
  }

  async getFormAnalysis(id: string): Promise<any | null> {
    const cache = await this.getFormAnalysisCache();
    return cache[id] || null;
  }

  async clearFormAnalysisCache(): Promise<void> {
    await Preferences.remove({ key: KEYS.FORM_ANALYSIS_CACHE });
  }

  // Sync status
  async setSyncStatus(status: { lastSync: string; pending: number }): Promise<void> {
    await Preferences.set({
      key: KEYS.SYNC_STATUS,
      value: JSON.stringify(status),
    });
  }

  async getSyncStatus(): Promise<{ lastSync: string; pending: number } | null> {
    const { value } = await Preferences.get({ key: KEYS.SYNC_STATUS });
    if (value) {
      return JSON.parse(value);
    }
    return null;
  }

  // App settings
  async setAppSettings(settings: any): Promise<void> {
    await Preferences.set({
      key: KEYS.APP_SETTINGS,
      value: JSON.stringify(settings),
    });
  }

  async getAppSettings(): Promise<any | null> {
    const { value } = await Preferences.get({ key: KEYS.APP_SETTINGS });
    if (value) {
      return JSON.parse(value);
    }
    return null;
  }

  // Tutorial status
  async setTutorialCompleted(completed: boolean): Promise<void> {
    await Preferences.set({
      key: KEYS.TUTORIAL_COMPLETED,
      value: JSON.stringify(completed),
    });
  }

  async getTutorialCompleted(): Promise<boolean> {
    const { value } = await Preferences.get({ key: KEYS.TUTORIAL_COMPLETED });
    if (value) {
      return JSON.parse(value);
    }
    return false;
  }

  // CSRF token handling
  async setCSRFToken(token: string): Promise<void> {
    await Preferences.set({
      key: KEYS.CSRF_TOKEN,
      value: token,
    });
  }

  async getCSRFToken(): Promise<string | null> {
    const { value } = await Preferences.get({ key: KEYS.CSRF_TOKEN });
    return value;
  }

  async removeCSRFToken(): Promise<void> {
    await Preferences.remove({ key: KEYS.CSRF_TOKEN });
  }

  // Clear all data
  async clearAll(): Promise<void> {
    await Preferences.clear();
  }
}

export const storageService = StorageService.getInstance(); 