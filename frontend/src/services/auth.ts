import { apiService } from './api';
import { store } from '../store';
import { setUser, setToken, setError, setLoading } from '../store/slices/authSlice';

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  name: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    name: string;
    role: string;
  };
}

class AuthService {
  async login(credentials: LoginCredentials) {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.post<AuthResponse>('/auth/login', credentials);
      
      store.dispatch(setToken(response.access_token));
      store.dispatch(setUser(response.user));
      
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async register(data: RegisterData) {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.post<AuthResponse>('/auth/register', data);
      
      store.dispatch(setToken(response.access_token));
      store.dispatch(setUser(response.user));
      
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async logout() {
    try {
      store.dispatch(setLoading(true));
      await apiService.post('/auth/logout');
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
      store.dispatch(setToken(null));
      store.dispatch(setUser(null));
    }
  }

  async getCurrentUser() {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.get<AuthResponse['user']>('/auth/me');
      store.dispatch(setUser(response));
      return response;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      throw error;
    } finally {
      store.dispatch(setLoading(false));
    }
  }

  async refreshToken() {
    try {
      store.dispatch(setLoading(true));
      const response = await apiService.post<{ access_token: string }>('/auth/refresh');
      store.dispatch(setToken(response.access_token));
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