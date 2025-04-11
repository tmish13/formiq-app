import { apiService } from './apiService';
import { store } from '../store';
import { setLoading, setError, setUser } from '../store/slices/authSlice';
import type { User, AuthResponse, LoginCredentials, RegisterData } from '../types';
import { ApiError } from './apiService';

const SESSION_KEY = 'formiq_session';
const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000; // 5 minutes in milliseconds
const MAX_REFRESH_RETRIES = 3;
const REFRESH_RETRY_DELAY = 1000; // 1 second

interface SessionData extends AuthResponse {
  refreshCount: number;
  lastRefresh: number;
}

export class AuthService {
  private refreshTimeout: ReturnType<typeof setTimeout> | null = null;
  private sessionData: SessionData | null = null;
  private refreshing: boolean = false;
  private refreshPromise: Promise<AuthResponse> | null = null;

  constructor() {
    this.initializeSession();
    window.addEventListener('storage', this.handleStorageChange);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  }

  private handleStorageChange = (event: StorageEvent) => {
    if (event.key === SESSION_KEY) {
      if (!event.newValue) {
        this.clearSession();
      } else if (event.newValue !== JSON.stringify(this.sessionData)) {
        this.initializeSession();
      }
    }
  };

  private handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      this.validateSession();
    }
  };

  private async validateSession() {
    if (this.sessionData) {
      try {
        await this.validateToken();
      } catch (error) {
        this.clearSession();
      }
    }
  }

  private initializeSession() {
    const savedSession = localStorage.getItem(SESSION_KEY);
    if (savedSession) {
      try {
        const session = JSON.parse(savedSession);
        this.sessionData = {
          ...session,
          refreshCount: 0,
          lastRefresh: Date.now()
        };
        this.scheduleTokenRefresh();
        this.validateToken().catch(() => this.clearSession());
      } catch (error) {
        this.clearSession();
      }
    }
  }

  private saveSession(session: AuthResponse) {
    this.sessionData = {
      ...session,
      refreshCount: 0,
      lastRefresh: Date.now()
    };
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    store.dispatch(setUser(session.user));
    this.scheduleTokenRefresh();
  }

  private clearSession() {
    this.sessionData = null;
    localStorage.removeItem(SESSION_KEY);
    store.dispatch(setUser(null));
    if (this.refreshTimeout) {
      clearTimeout(this.refreshTimeout);
      this.refreshTimeout = null;
    }
    this.refreshing = false;
    this.refreshPromise = null;
  }

  private scheduleTokenRefresh() {
    if (this.refreshTimeout) {
      clearTimeout(this.refreshTimeout);
    }

    if (!this.sessionData?.access_token) return;

    try {
      const payload = this.parseJwt(this.sessionData.access_token);
      const expiresIn = payload.exp * 1000 - Date.now() - TOKEN_REFRESH_THRESHOLD;
      
      if (expiresIn > 0) {
        this.refreshTimeout = setTimeout(() => this.refreshToken(), expiresIn);
      } else {
        this.refreshToken();
      }
    } catch (error) {
      console.error('Error scheduling token refresh:', error);
      this.clearSession();
    }
  }

  private parseJwt(token: string): { exp: number; [key: string]: any } {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(window.atob(base64));
    } catch (error) {
      throw new Error('Invalid token format');
    }
  }

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    store.dispatch(setLoading(true));
    try {
      const response = await apiService.auth.login(credentials.email, credentials.password);
      const session = {
        access_token: response.data.access_token,
        user: response.data.user
      };
      this.saveSession(session);
      store.dispatch(setLoading(false));
      return session;
    } catch (error) {
      const apiError = error as ApiError;
      store.dispatch(setError(apiError.message));
      store.dispatch(setLoading(false));
      throw apiError;
    }
  }

  async register(data: RegisterData): Promise<AuthResponse> {
    store.dispatch(setLoading(true));
    try {
      const response = await apiService.auth.register({
        email: data.email,
        password: data.password,
        username: data.email.split('@')[0]
      });
      const session = {
        access_token: response.data.access_token,
        user: response.data.user
      };
      this.saveSession(session);
      store.dispatch(setLoading(false));
      return session;
    } catch (error) {
      const apiError = error as ApiError;
      store.dispatch(setError(apiError.message));
      store.dispatch(setLoading(false));
      throw apiError;
    }
  }

  async logout(): Promise<void> {
    store.dispatch(setLoading(true));
    try {
      await apiService.auth.logout();
      this.clearSession();
      store.dispatch(setLoading(false));
    } catch (error: any) {
      store.dispatch(setError(error.message));
      store.dispatch(setLoading(false));
      throw error;
    }
  }

  async validateToken(): Promise<User> {
    if (!this.sessionData?.access_token) {
      throw new Error('No active session');
    }

    store.dispatch(setLoading(true));
    try {
      const response = await apiService.auth.validate();
      store.dispatch(setLoading(false));
      return response.data;
    } catch (error: any) {
      this.clearSession();
      store.dispatch(setError(error.message));
      store.dispatch(setLoading(false));
      throw error;
    }
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    store.dispatch(setLoading(true));
    try {
      const response = await apiService.profile.update(data);
      store.dispatch(setLoading(false));
      return response.data;
    } catch (error: any) {
      store.dispatch(setError(error.message));
      store.dispatch(setLoading(false));
      throw error;
    }
  }

  async refreshToken(): Promise<AuthResponse> {
    if (!this.sessionData?.access_token) {
      throw new Error('No active session');
    }

    // Return existing refresh promise if one is in progress
    if (this.refreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    // Check refresh count
    if (this.sessionData.refreshCount >= MAX_REFRESH_RETRIES) {
      this.clearSession();
      throw new Error('Maximum token refresh attempts exceeded');
    }

    this.refreshing = true;
    store.dispatch(setLoading(true));

    this.refreshPromise = (async () => {
      try {
        await new Promise(resolve => setTimeout(resolve, REFRESH_RETRY_DELAY));
        const response = await apiService.auth.validate();
        const session = {
          access_token: response.data.access_token,
          user: response.data.user
        };
        this.saveSession(session);
        return session;
      } catch (error) {
        const apiError = error as ApiError;
        if (this.sessionData) {
          this.sessionData.refreshCount++;
        }
        throw apiError;
      } finally {
        this.refreshing = false;
        this.refreshPromise = null;
        store.dispatch(setLoading(false));
      }
    })();

    return this.refreshPromise;
  }

  isAuthenticated(): boolean {
    return !!this.sessionData?.access_token;
  }

  getCurrentUser(): User | null {
    return this.sessionData?.user || null;
  }

  getAccessToken(): string | null {
    return this.sessionData?.access_token || null;
  }

  cleanup() {
    window.removeEventListener('storage', this.handleStorageChange);
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    this.clearSession();
  }
}

export const authService = new AuthService(); 