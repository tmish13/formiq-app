import { BaseApiService, ApiResponse } from './baseApi';
import { User } from '../../types';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData extends LoginCredentials {
  username: string;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  name: string;
  role: 'user' | 'admin';
  subscription_tier: 'free' | 'premium' | 'enterprise';
  subscription_end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username: string;
}

class AuthService extends BaseApiService {
  private static instance: AuthService;

  private constructor() {
    super();
  }

  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }

  public async login(credentials: LoginCredentials): Promise<ApiResponse<AuthResponse>> {
    const response = await this.post<AuthResponse>('/auth/login', credentials);
    if (response.data.token) {
      localStorage.setItem('auth_token', response.data.token);
    }
    return response;
  }

  public async register(data: RegisterData): Promise<ApiResponse<AuthResponse>> {
    const response = await this.post<AuthResponse>('/auth/register', data);
    if (response.data.token) {
      localStorage.setItem('auth_token', response.data.token);
    }
    return response;
  }

  public async logout(): Promise<void> {
    await this.post('/auth/logout');
    localStorage.removeItem('auth_token');
  }

  public async getCurrentUser(): Promise<ApiResponse<UserProfile>> {
    return this.get<UserProfile>('/auth/me');
  }

  public async updateProfile(data: Partial<UserProfile>): Promise<ApiResponse<UserProfile>> {
    return this.put<UserProfile>('/auth/profile', data);
  }

  public async refreshToken(): Promise<ApiResponse<{ token: string }>> {
    const response = await this.post<{ token: string }>('/auth/refresh');
    if (response.data.token) {
      localStorage.setItem('auth_token', response.data.token);
    }
    return response;
  }

  public async requestPasswordReset(email: string): Promise<ApiResponse<void>> {
    return this.post('/auth/password/reset/request', { email });
  }

  public async resetPassword(token: string, newPassword: string): Promise<ApiResponse<void>> {
    return this.post('/auth/password/reset', { token, newPassword });
  }

  public async changePassword(currentPassword: string, newPassword: string): Promise<ApiResponse<void>> {
    return this.post('/auth/password/change', { currentPassword, newPassword });
  }

  public isAuthenticated(): boolean {
    return !!localStorage.getItem('auth_token');
  }
}

// Export a singleton instance
export const authService = AuthService.getInstance(); 