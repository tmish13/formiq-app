import { apiService } from './api';
import { store } from '../store';
import { setUser, setToken, setError, setLoading } from '../store/slices/authSlice';
import type { User, AuthResponse, LoginCredentials, RegisterData } from '../types';

class AuthService {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.post<AuthResponse>('/auth/login', credentials);
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.post<AuthResponse>('/auth/register', data);
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async logout(): Promise<void> {
    try {
      store.dispatch(setLoading(true));
      await apiService.post('/auth/logout');
      localStorage.removeItem('token');
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.get<User>('/users/me');
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.patch<User>('/users/me', data);
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async refreshToken(): Promise<{ access_token: string }> {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.post<{ access_token: string }>('/auth/refresh');
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }
}

export const authService = new AuthService(); 