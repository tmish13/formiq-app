import { createContext, useContext } from 'react';
import apiService from './apiService';
import { LoginCredentials, RegisterData, User, AuthResponse } from '../types/auth';

/**
 * Service for handling authentication logic.
 * Uses JWT tokens stored in localStorage.
 */
class AuthService {
  /**
   * Login a user with email and password
   */
  async login(credentials: LoginCredentials): Promise<User> {
    try {
      const response = await apiService.login(credentials.email, credentials.password);
      
      // Tokens are stored in localStorage by the apiService
      // TypeScript assertion since we know the structure
      const authResponse = response.data as AuthResponse;
      return authResponse.user;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  }

  /**
   * Register a new user
   */
  async register(data: RegisterData): Promise<User> {
    try {
      const response = await apiService.post('/auth/register', data);
      const responseData = response.data as AuthResponse;
      
      // Store token if it's returned with registration
      if (responseData.access_token) {
        localStorage.setItem('token', responseData.access_token);
      }
      
      return responseData.user || response.data as User;
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  }

  /**
   * Logout the current user
   */
  async logout(): Promise<void> {
    try {
      await apiService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear token on logout
      localStorage.removeItem('token');
    }
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }

  /**
   * Get current user data
   */
  async getCurrentUser(): Promise<User | null> {
    if (!this.isAuthenticated()) {
      return null;
    }
    
    try {
      const response = await apiService.get('/users/me');
      return response.data as User;
    } catch (error) {
      console.error('Error getting current user:', error);
      return null;
    }
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    await apiService.post('/auth/request-password-reset', { email });
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await apiService.post('/auth/reset-password', { 
      token, 
      new_password: newPassword 
    });
  }
}

// Create auth context for React components
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  checkAuthStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  checkAuthStatus: async () => {}
});

// Auth service singleton instance
const authService = new AuthService();

export { authService, AuthContext };

// Hook for using auth in components
export const useAuth = () => useContext(AuthContext); 