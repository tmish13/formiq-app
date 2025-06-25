import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { Capacitor } from '@capacitor/core';
import { logError, logNetworkError } from '../utils/errorLogging';

// Get the base URL for the API depending on environment
const getBaseUrl = () => {
  // In native mobile platforms
  if (Capacitor.isNativePlatform()) {
    if (Capacitor.getPlatform() === 'android') {
      return 'http://10.0.2.2:8000/api/v1';
    }
    if (Capacitor.getPlatform() === 'ios') {
      return 'http://localhost:8000/api/v1';
    }
  }
  
  // In web browser
  return process.env.REACT_APP_API_URL ? 
    `${process.env.REACT_APP_API_URL}/api/v1` : 
    'http://localhost:8000/api/v1';
};

const API_BASE_URL = getBaseUrl();

// Define API endpoints aligned with backend Phase 1.0-1.1
export const endpoints = {
  auth: {
    login: '/auth/login',
    register: '/auth/register',
    refreshToken: '/auth/refresh',
    logout: '/auth/logout',
  },
  user: {
    profile: '/users/me',
    update: '/users/me',
    subscription: '/users/subscription',
  },
  workouts: {
    list: '/workouts',
    detail: (id: string) => `/workouts/${id}`,
    create: '/workouts',
    update: (id: string) => `/workouts/${id}`,
    delete: (id: string) => `/workouts/${id}`,
  },
  videos: {
    uploadUrl: '/videos/upload-url',
    uploadComplete: '/videos/upload-complete',
    detail: (id: string) => `/videos/${id}`,
    list: '/videos',
    status: (id: string) => `/videos/${id}/status`,
  },
  formChecks: {
    upload: '/form-checks',
    detail: (id: string) => `/form-checks/${id}`,
    list: '/form-checks',
    delete: (id: string) => `/form-checks/${id}`,
    complete: (id: string) => `/form-checks/${id}/complete`,
    feedback: (id: string) => `/form-checks/${id}/feedback`,
    mlAnalysis: (id: string) => `/form-checks/${id}/ml-analysis`,
    history: '/form-checks/history',
  },
  exercises: {
    list: '/exercises',
    detail: (id: string) => `/exercises/${id}`,
    referencePose: (exerciseType: string) => `/exercises/${exerciseType}/reference-pose`,
  },
  exerciseConfigs: {
    list: '/exercise-configs',
    detail: (id: string) => `/exercise-configs/${id}`,
    byExercise: (exerciseId: string) => `/exercise-configs/exercise/${exerciseId}`,
    activeByExercise: (exerciseId: string) => `/exercise-configs/exercise/${exerciseId}/active`,
    create: '/exercise-configs',
    update: (id: string) => `/exercise-configs/${id}`,
    delete: (id: string) => `/exercise-configs/${id}`,
  },
  ml: {
    modelInfo: '/ml/model-info',
    scores: (formCheckId: string) => `/ml/scores/${formCheckId}`,
  },
} as const;

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
      },
      timeout: 15000, // Increase timeout for slower connections
    });

    // Add request interceptor to include JWT token for authentication
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('token');
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
            // Handle token refresh - for now just redirect to login
            // TODO: Implement proper refresh token logic when backend supports it
            localStorage.removeItem('token');
            this.redirectToLogin();
            return Promise.reject(error);
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            return Promise.reject(error);
          }
        }
        
        // Network error handling
        if (!error.response) {
          logNetworkError('network-connectivity', error);
        } else {
          logNetworkError('api-request-failed', error);
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
    
    // Store token in localStorage
    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token);
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
      // Always clear token
      localStorage.removeItem('token');
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

  // ======= Video Upload Methods (Backend Phase 1.0 Integration) =======

  /**
   * Get presigned URL for video upload
   */
  async getVideoUploadUrl(metadata: {
    filename: string;
    contentType: string;
    exerciseId?: string;
    userId?: string;
  }): Promise<{
    uploadUrl: string;
    videoId: string;
    fields?: Record<string, string>;
  }> {
    const response = await this.api.post('/videos/upload-url', metadata);
    return response.data;
  }

  /**
   * Upload video to S3 using presigned URL
   */
  async uploadVideoToS3(uploadUrl: string, file: File, fields?: Record<string, string>): Promise<void> {
    const formData = new FormData();
    
    // Add any required fields first
    if (fields) {
      Object.entries(fields).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }
    
    // Add the file last
    formData.append('file', file);

    // Upload directly to S3 (not through our API)
    await axios.post(uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  /**
   * Confirm video upload completion
   */
  async confirmVideoUpload(videoId: string, metadata?: {
    duration?: number;
    size?: number;
    width?: number;
    height?: number;
  }): Promise<any> {
    const response = await this.api.post('/videos/upload-complete', {
      videoId,
      ...metadata,
    });
    return response.data;
  }

  /**
   * Get video processing status
   */
  async getVideoStatus(videoId: string): Promise<{
    status: string;
    progress?: number;
    error?: string;
    processedUrl?: string;
  }> {
    const response = await this.api.get(`/videos/${videoId}/status`);
    return response.data;
  }

  // ======= Exercise & Exercise Config Methods (Backend Phase 1.1 Integration) =======

  /**
   * Get all exercises
   */
  async getExercises(filters?: {
    type?: string;
    difficulty?: string;
    muscleGroups?: string[];
  }): Promise<any[]> {
    const response = await this.api.get('/exercises', { params: filters });
    return response.data;
  }

  /**
   * Get exercise by ID
   */
  async getExercise(exerciseId: string): Promise<any> {
    const response = await this.api.get(`/exercises/${exerciseId}`);
    return response.data;
  }

  /**
   * Get reference pose data for exercise
   */
  async getReferencePose(exerciseType: string): Promise<any> {
    const response = await this.api.get(`/exercises/${exerciseType}/reference-pose`);
    return response.data;
  }

  // Method to check if user is authenticated
  public isAuthenticated(): boolean {
    return !!localStorage.getItem('token');
  }
}

// Export a singleton instance
const apiService = new ApiService();
export default apiService;