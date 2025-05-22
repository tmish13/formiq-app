import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// Define API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

// Define API error interface
export interface ApiError {
  message: string;
  code?: string;
  status: number;
  details?: unknown;
}

/**
 * Service for making API requests with JWT authentication
 */
class ApiService {
  private api: AxiosInstance;

  constructor() {
    // Create axios instance
    this.api = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      }
    });

    // Add request interceptor to include JWT token for authentication
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }
      return config;
    });

    // Add response interceptor for automatic token refresh
    this.api.interceptors.response.use(
      response => response,
      async (error) => {
        const originalRequest = error.config;
        
        // If error is 401 (Unauthorized) and we haven't already tried to refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            // Try to refresh the token
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
              // No refresh token available, redirect to login
              this.redirectToLogin();
              return Promise.reject(error);
            }
            
            // Call token refresh endpoint
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, { 
              refresh_token: refreshToken 
            });
            
            // Update stored tokens
            localStorage.setItem('access_token', response.data.access_token);
            if (response.data.refresh_token) {
              localStorage.setItem('refresh_token', response.data.refresh_token);
            }
            
            // Retry original request with new token
            originalRequest.headers['Authorization'] = `Bearer ${response.data.access_token}`;
            return axios(originalRequest);
          } catch (refreshError) {
            // If refresh fails, clear tokens and redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            this.redirectToLogin();
            return Promise.reject(refreshError);
          }
        }
        
        return this.handleApiError(error);
      }
    );
  }

  // Helper method to redirect to login page
  private redirectToLogin() {
    window.location.href = '/login';
  }

  /**
   * Handle API errors
   */
  private handleApiError(error: AxiosError): Promise<never> {
    // Format error for consistent handling
    const apiError: ApiError = {
      message: (error.response?.data as any)?.message || error.message || 'An unknown error occurred',
      status: error.response?.status || 500,
      code: (error.response?.data as any)?.code,
      details: (error.response?.data as any)?.details
    };

    return Promise.reject(apiError);
  }

  // ======= Authentication Methods =======

  /**
   * Log in a user
   */
  async login(email: string, password: string): Promise<AxiosResponse> {
    const response = await this.api.post('/auth/login', { email, password });
    
    // Store tokens in localStorage
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    if (response.data.refresh_token) {
      localStorage.setItem('refresh_token', response.data.refresh_token);
    }
    
    return response;
  }

  /**
   * Register a new user
   */
  async register(userData: any): Promise<AxiosResponse<any>> {
    return this.api.post('/auth/register', userData);
  }

  /**
   * Validate the current session
   */
  async validateSession(): Promise<AxiosResponse<any>> {
    return this.api.get('/auth/validate-session');
  }

  /**
   * Log out the current user
   */
  async logout(): Promise<void> {
    try {
      await this.api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear tokens
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  /**
   * Request a password reset
   */
  async requestPasswordReset(email: string): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/password-reset-request', { email });
  }

  /**
   * Confirm a password reset
   */
  async confirmPasswordReset(data: any): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/password-reset-confirm', data);
  }

  /**
   * Verify email with token
   */
  async verifyEmail(token: string): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/verify-email', { token });
  }

  // ======= User Profile Methods =======

  /**
   * Get the current user's profile
   */
  async getCurrentUser(): Promise<AxiosResponse<any>> {
    return this.api.get('/users/me');
  }

  /**
   * Update the current user's profile
   */
  async updateProfile(userData: any): Promise<AxiosResponse<any>> {
    return this.api.patch('/users/me', userData);
  }

  /**
   * Update the user's avatar
   */
  async updateAvatar(formData: FormData): Promise<AxiosResponse<any>> {
    return this.api.post('/users/me/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }

  // ======= Generic Request Methods =======

  /**
   * Make a GET request
   */
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<AxiosResponse<T>> {
    return this.api.get<T>(endpoint, { params });
  }

  /**
   * Make a POST request
   */
  async post<T>(endpoint: string, data?: any): Promise<AxiosResponse<T>> {
    return this.api.post<T>(endpoint, data);
  }

  /**
   * Make a PUT request
   */
  async put<T>(endpoint: string, data?: any): Promise<AxiosResponse<T>> {
    return this.api.put<T>(endpoint, data);
  }

  /**
   * Make a PATCH request
   */
  async patch<T>(endpoint: string, data?: any): Promise<AxiosResponse<T>> {
    return this.api.patch<T>(endpoint, data);
  }

  /**
   * Make a DELETE request
   */
  async delete<T>(endpoint: string): Promise<AxiosResponse<T>> {
    return this.api.delete<T>(endpoint);
  }

  // Method to check if user is authenticated
  public isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

// Export a singleton instance
const apiService = new ApiService();
export default apiService;