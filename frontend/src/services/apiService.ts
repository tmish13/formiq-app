import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { Capacitor } from '@capacitor/core';
import { logError, logNetworkError } from '../utils/errorLogging';
import { storageService } from './storageService';
import { mockAuthService } from './mockAuthService';

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
    statistics: '/videos/statistics',
    metrics: '/videos/metrics',
    processingStats: '/videos/processing-stats',
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
  analytics: {
    overview: '/analytics/overview',
    performance: '/analytics/performance',
    exerciseStats: '/analytics/exercise-stats',
    timeSeriesData: '/analytics/time-series',
    export: '/analytics/export',
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
    this.api.interceptors.request.use(async (config) => {
      const token = await storageService.getAuthToken();
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
            // Attempt to refresh the token
            const refreshToken = await storageService.getRefreshToken();
            if (refreshToken) {
              const response = await this.refreshToken(refreshToken);
              if (response.access_token) {
                await storageService.setAuthToken(response.access_token);
                // Retry the original request with new token
                originalRequest.headers['Authorization'] = `Bearer ${response.access_token}`;
                return this.api(originalRequest);
              }
            }
            
            // If refresh fails or no refresh token, redirect to login
            await storageService.removeAuthToken();
            await storageService.removeRefreshToken();
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

  // Helper method to determine if we should use mock service
  private shouldUseMock(): boolean {
    return process.env.NODE_ENV === 'development' || 
           process.env.REACT_APP_USE_MOCK_AUTH === 'true' ||
           !process.env.REACT_APP_API_URL;
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
    // Use mock service if backend is not available or in development
    if (this.shouldUseMock()) {
      const authResponse = await mockAuthService.login(email, password);
      
      // Store tokens in storageService
      await storageService.setAuthToken(authResponse.access_token);
      await storageService.setRefreshToken(authResponse.refresh_token);
      
      return { data: authResponse } as AxiosResponse;
    }

    const response = await this.api.post('/auth/login', { email, password });
    
    // Store tokens in storageService
    if (response.data.access_token) {
      await storageService.setAuthToken(response.data.access_token);
    }
    if (response.data.refresh_token) {
      await storageService.setRefreshToken(response.data.refresh_token);
    }
    
    return response;
  }

  /**
   * Register a new user
   */
  async register(userData: any): Promise<AxiosResponse<any>> {
    // Use mock service if backend is not available or in development
    if (this.shouldUseMock()) {
      const authResponse = await mockAuthService.register(userData);
      
      // Store tokens in storageService
      await storageService.setAuthToken(authResponse.access_token);
      await storageService.setRefreshToken(authResponse.refresh_token);
      
      return { data: authResponse } as AxiosResponse;
    }

    return this.api.post('/auth/register', userData);
  }

  /**
   * Complete user onboarding
   */
  async completeOnboarding(): Promise<AxiosResponse<any>> {
    // Use mock service if backend is not available or in development
    if (this.shouldUseMock()) {
      return await mockAuthService.completeOnboarding() as AxiosResponse;
    }

    return this.api.post('/auth/complete-onboarding');
  }

  /**
   * Validate the current session
   */
  async validateSession(): Promise<AxiosResponse<any>> {
    // Use mock service if backend is not available or in development
    if (this.shouldUseMock()) {
      return await mockAuthService.validateSession() as AxiosResponse;
    }

    return this.api.post('/auth/test-token');
  }

  /**
   * Log out the current user
   */
  async logout(): Promise<void> {
    try {
      // Use mock service if backend is not available or in development
      if (this.shouldUseMock()) {
        await mockAuthService.logout();
      } else {
        await this.api.post('/auth/logout');
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear tokens
      await storageService.removeAuthToken();
      await storageService.removeRefreshToken();
    }
  }

  /**
   * Request a password reset
   */
  async requestPasswordReset(email: string): Promise<AxiosResponse<void>> {
    if (this.shouldUseMock()) {
      await mockAuthService.requestPasswordReset(email);
      return { data: undefined } as AxiosResponse<void>;
    }
    
    return this.api.post('/auth/reset-password/request', { email });
  }

  /**
   * Confirm a password reset
   */
  async confirmPasswordReset(data: any): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/reset-password/confirm', data);
  }

  /**
   * Verify email with token
   */
  async verifyEmail(token: string): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/verify-email/confirm', { token });
  }

  /**
   * Request email verification
   */
  async requestEmailVerification(email: string): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/verify-email/request', { email });
  }

  /**
   * Confirm email verification
   */
  async confirmEmailVerification(token: string): Promise<AxiosResponse<void>> {
    return this.api.post('/auth/verify-email/confirm', { token });
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<AxiosResponse<void>> {
    if (this.shouldUseMock()) {
      await mockAuthService.resetPassword(token, newPassword);
      return { data: undefined } as AxiosResponse<void>;
    }
    
    return this.api.post('/auth/reset-password/confirm', { 
      token, 
      new_password: newPassword 
    });
  }

  /**
   * Change password for authenticated user
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<AxiosResponse<void>> {
    return this.api.post('/users/me/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    });
  }

  // ======= Social Authentication Methods =======

  /**
   * Authenticate with Google
   */
  async googleAuth(token: string): Promise<AxiosResponse<any>> {
    if (this.shouldUseMock()) {
      const authResponse = await mockAuthService.socialLogin('google', token);
      
      // Store tokens in storageService
      await storageService.setAuthToken(authResponse.access_token);
      await storageService.setRefreshToken(authResponse.refresh_token);
      
      return { data: authResponse } as AxiosResponse;
    }
    
    const response = await this.api.post('/auth/social/google', { token });
    
    // Store tokens if successful
    if (response.data.access_token) {
      await storageService.setAuthToken(response.data.access_token);
    }
    if (response.data.refresh_token) {
      await storageService.setRefreshToken(response.data.refresh_token);
    }
    
    return response;
  }

  /**
   * Authenticate with Apple
   */
  async appleAuth(token: string): Promise<AxiosResponse<any>> {
    if (this.shouldUseMock()) {
      const authResponse = await mockAuthService.socialLogin('apple', token);
      
      // Store tokens in storageService
      await storageService.setAuthToken(authResponse.access_token);
      await storageService.setRefreshToken(authResponse.refresh_token);
      
      return { data: authResponse } as AxiosResponse;
    }
    
    const response = await this.api.post('/auth/social/apple', { token });
    
    // Store tokens if successful
    if (response.data.access_token) {
      await storageService.setAuthToken(response.data.access_token);
    }
    if (response.data.refresh_token) {
      await storageService.setRefreshToken(response.data.refresh_token);
    }
    
    return response;
  }

  /**
   * Get Google OAuth redirect URL
   */
  getGoogleOAuthUrl(): string {
    if (this.shouldUseMock()) {
      // Return a mock URL that will be handled by the callback component
      return `/auth/google/callback?code=mock_google_code&state=mock_state`;
    }
    return `${API_BASE_URL}/auth/social/google/redirect`;
  }

  /**
   * Get Apple OAuth redirect URL
   */
  getAppleOAuthUrl(): string {
    if (this.shouldUseMock()) {
      // Return a mock URL that will be handled by the callback component
      return `/auth/apple/callback?code=mock_apple_code&state=mock_state`;
    }
    return `${API_BASE_URL}/auth/social/apple/redirect`;
  }

  /**
   * Refresh the access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<{access_token: string; refresh_token?: string}> {
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken
    });
    return response.data;
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

  // ======= Analytics Methods =======

  /**
   * Get analytics overview data
   */
  async getAnalyticsOverview(timeRange?: string): Promise<{
    totalSessions: number;
    averageScore: number;
    bestExercise: string | null;
    weeklyProgress: number;
    improvementRate: number;
  }> {
    const response = await this.api.get('/analytics/overview', {
      params: { timeRange }
    });
    return response.data;
  }

  /**
   * Get exercise-specific statistics
   */
  async getExerciseStats(timeRange?: string): Promise<Array<{
    exercise_type: string;
    count: number;
    avg_score: number;
    best_score: number;
    improvement: number;
    trend: 'up' | 'down' | 'stable';
  }>> {
    const response = await this.api.get('/analytics/exercise-stats', {
      params: { timeRange }
    });
    return response.data;
  }

  /**
   * Get time series data for charts
   */
  async getTimeSeriesData(timeRange?: string): Promise<Array<{
    date: string;
    overall_score: number;
    posture_score: number;
    stability_score: number;
    depth_score: number;
    session_count: number;
  }>> {
    const response = await this.api.get('/analytics/time-series', {
      params: { timeRange }
    });
    return response.data;
  }

  /**
   * Get performance metrics summary
   */
  async getPerformanceMetrics(timeRange?: string): Promise<{
    consistency: number;
    weakestArea: 'posture' | 'stability' | 'depth' | null;
    strongestArea: 'posture' | 'stability' | 'depth' | null;
    targetRecommendations: string[];
  }> {
    const response = await this.api.get('/analytics/performance', {
      params: { timeRange }
    });
    return response.data;
  }

  /**
   * Export analytics data
   */
  async exportAnalyticsData(format: 'csv' | 'json' | 'pdf', timeRange?: string): Promise<Blob> {
    const response = await this.api.get('/analytics/export', {
      params: { format, timeRange },
      responseType: 'blob'
    });
    return response.data;
  }

  // ======= Video Statistics Methods =======

  /**
   * Get comprehensive video statistics
   */
  async getVideoStatistics(timeRange?: string): Promise<{
    totalVideos: number;
    processedVideos: number;
    failedVideos: number;
    processingVideos: number;
    averageProcessingTime: number;
    totalStorageUsed: number;
    uploadsByExerciseType: Record<string, number>;
    dailyUploads: Array<{ date: string; count: number }>;
    successRate: number;
  }> {
    const response = await this.api.get('/videos/statistics', {
      params: { timeRange }
    });
    return response.data;
  }

  /**
   * Get video processing performance metrics
   */
  async getVideoProcessingMetrics(): Promise<{
    averageProcessingTime: number;
    processingSuccess: number;
    processingFailure: number;
    queueLength: number;
    processedToday: number;
    processingErrors: Array<{ error: string; count: number }>;
    processingTimeByExercise: Record<string, number>;
  }> {
    const response = await this.api.get('/videos/processing-stats');
    return response.data;
  }

  /**
   * Get video-to-form-check conversion metrics
   */
  async getVideoConversionMetrics(timeRange?: string): Promise<{
    videosUploaded: number;
    formChecksCreated: number;
    conversionRate: number;
    averageTimeToCompletion: number;
    successfulAnalyses: number;
    failedAnalyses: number;
  }> {
    const response = await this.api.get('/videos/conversion-metrics', {
      params: { timeRange }
    });
    return response.data;
  }

  /**
   * Get video storage and quality metrics
   */
  async getVideoQualityMetrics(): Promise<{
    averageFileSize: number;
    averageDuration: number;
    resolutionDistribution: Record<string, number>;
    formatDistribution: Record<string, number>;
    qualityScores: Array<{ quality: string; count: number }>;
    compressionRates: Array<{ original: number; compressed: number; ratio: number }>;
  }> {
    const response = await this.api.get('/videos/quality-metrics');
    return response.data;
  }

  // Method to check if user is authenticated
  public async isAuthenticated(): Promise<boolean> {
    const token = await storageService.getAuthToken();
    return !!token;
  }
}

// Export a singleton instance
const apiService = new ApiService();
export default apiService;