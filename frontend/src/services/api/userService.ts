import { BaseApiService, ApiResponse } from './baseApi';
import { User } from '../../types/auth';

export interface UserPreferences {
  theme?: 'light' | 'dark';
  notifications?: boolean;
  language?: string;
}

export interface UserStats {
  totalWorkouts: number;
  completedExercises: number;
  averageScore: number;
  streakDays: number;
}

export interface UserActivity {
  id: string;
  type: string;
  timestamp: string;
  details: any;
}

class UserService extends BaseApiService {
  private static instance: UserService | null = null;

  private constructor() {
    super();
  }

  public static getInstance(): UserService {
    if (!UserService.instance) {
      UserService.instance = new UserService();
    }
    return UserService.instance;
  }

  public async getProfile(): Promise<ApiResponse<User>> {
    return this.get<User>('/users/profile');
  }

  public async updateProfile(data: Partial<User>): Promise<ApiResponse<User>> {
    return this.put<User>('/users/profile', data);
  }

  public async updatePreferences(preferences: UserPreferences): Promise<ApiResponse<UserPreferences>> {
    return this.put<UserPreferences>('/users/preferences', preferences);
  }

  public async getUserStats(): Promise<ApiResponse<UserStats>> {
    return this.get<UserStats>('/users/stats');
  }

  public async getActivityHistory(page: number = 1, limit: number = 10): Promise<ApiResponse<UserActivity[]>> {
    return this.get<UserActivity[]>(`/users/activity?page=${page}&limit=${limit}`);
  }

  public async deleteAccount(): Promise<ApiResponse<void>> {
    return this.delete<void>('/users/account');
  }

  public async exportUserData(): Promise<ApiResponse<Blob>> {
    return this.get<Blob>('/users/export', {
      responseType: 'blob',
    });
  }

  public async updateNotificationSettings(settings: { [key: string]: boolean }): Promise<ApiResponse<void>> {
    return this.put<void>('/users/notifications/settings', settings);
  }
}

export const userService = UserService.getInstance();
export default userService; 