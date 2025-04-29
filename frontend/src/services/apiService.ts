import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosProgressEvent, InternalAxiosRequestConfig, AxiosHeaders, AxiosHeaderValue, AxiosResponse } from 'axios';
import type {
  FormAnalysisResponse,
  FormAnalysisResult,
  FormAnalysisHistory,
  PoseAnalysisResult
} from '../types/formAnalysis';
import { ApiResponse, ApiError, QueryParams } from '../types/api';
import { Exercise } from './exerciseLibraryService';
import { redisService } from './redisService';
import { handleApiError } from '../utils/errorHandling';

export interface ErrorResponse {
  message: string;
  code?: string;
  details?: unknown;
  timestamp?: string;
  [key: string]: unknown;
}

interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  retryableStatuses: number[];
}

const defaultRetryConfig: RetryConfig = {
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};

export class ApiService {
  protected client: AxiosInstance = axios.create();
  private csrfToken: string | null = null;
  private retryConfig: RetryConfig;
  private baseUrl: string;
  private requestInterceptors: number[] = [];
  private responseInterceptors: number[] = [];

  // Cache configuration
  private readonly CACHE_TTL = 3600; // 1 hour in seconds
  private readonly CACHE_ENABLED_ENDPOINTS = [
    '/exercises',
    '/form-analysis/history',
    '/profile'
  ];

  constructor(baseUrl: string = process.env.REACT_APP_API_URL || '/api/v1', retryConfig: Partial<RetryConfig> = {}) {
    this.baseUrl = baseUrl;
    this.retryConfig = { ...defaultRetryConfig, ...retryConfig };
    this.initializeClient();
  }

  private initializeClient(): void {
    this.client = this.createAxiosInstance();
    if (!this.client || !this.client.interceptors) {
      throw new Error('Failed to initialize Axios client');
    }
    this.setupInterceptors();
  }

  protected createAxiosInstance(): AxiosInstance {
    const instance = axios.create({
      baseURL: this.baseUrl,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
      timeout: 30000, // 30 seconds timeout
    });

    // Ensure interceptors are available
    if (!instance.interceptors) {
      instance.interceptors = {
        request: {
          use: (onFulfilled?: any, onRejected?: any) => 0,
          eject: (id: number) => {},
          clear: () => {}
        },
        response: {
          use: (onFulfilled?: any, onRejected?: any) => 0,
          eject: (id: number) => {},
          clear: () => {}
        }
      };
    }

    return instance;
  }

  public addRequestInterceptor(onFulfilled?: (config: InternalAxiosRequestConfig) => Promise<InternalAxiosRequestConfig> | InternalAxiosRequestConfig, onRejected?: (error: any) => any): number {
    const interceptorId = this.client.interceptors.request.use(onFulfilled, onRejected);
    this.requestInterceptors.push(interceptorId);
    return interceptorId;
  }

  public addResponseInterceptor(onFulfilled?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>, onRejected?: (error: any) => any): number {
    const interceptorId = this.client.interceptors.response.use(onFulfilled, onRejected);
    this.responseInterceptors.push(interceptorId);
    return interceptorId;
  }

  public removeRequestInterceptor(interceptorId: number): void {
    this.client.interceptors.request.eject(interceptorId);
    this.requestInterceptors = this.requestInterceptors.filter(id => id !== interceptorId);
  }

  public removeResponseInterceptor(interceptorId: number): void {
    this.client.interceptors.response.eject(interceptorId);
    this.responseInterceptors = this.responseInterceptors.filter(id => id !== interceptorId);
  }

  private setupInterceptors(): void {
    this.addRequestInterceptor(
      async (config: InternalAxiosRequestConfig) => {
        return this.addRequestHeaders(config);
      }
    );

    this.addResponseInterceptor(
      (response) => response,
      async (error: AxiosError<ErrorResponse>) => {
        return this.handleResponseError(error);
      }
    );
  }

  private async addRequestHeaders(
    config: InternalAxiosRequestConfig
  ): Promise<InternalAxiosRequestConfig> {
    const token = localStorage.getItem('auth_tokens');
    if (token && config.headers) {
      const tokens = JSON.parse(token);
      config.headers.Authorization = `Bearer ${tokens.accessToken}`;
    }

    if (process.env.NODE_ENV === 'production') {
      const csrfToken = this.getCsrfTokenFromCookie();
      if (!csrfToken) {
        await this.fetchCsrfToken();
      }

      const securityHeaders = {
        'X-CSRF-Token': this.csrfToken || '',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; img-src 'self' data: https://*.s3.amazonaws.com; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self' https://api.stripe.com;"
      };

      config.headers = AxiosHeaders.concat(config.headers, securityHeaders);
    }

    return config;
  }

  private getCsrfTokenFromCookie(): string | null {
    const name = 'csrf_token=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookieArray = decodedCookie.split(';');
    for (let cookie of cookieArray) {
      cookie = cookie.trim();
      if (cookie.indexOf(name) === 0) {
        return cookie.substring(name.length, cookie.length);
      }
    }
    return null;
  }

  private async fetchCsrfToken(): Promise<void> {
    try {
      const response = await axios.get('/api/v1/auth/csrf-token');
      this.csrfToken = response.data.token;
      // Store token in cookie with secure attributes
      document.cookie = `csrf_token=${this.csrfToken}; path=/; secure; samesite=strict`;
    } catch (error) {
      console.error('Failed to fetch CSRF token:', error);
      throw error;
    }
  }

  private async handleResponseError(error: AxiosError<ErrorResponse>): Promise<any> {
    const config = error.config as AxiosRequestConfig & { _retry?: number };

    // Only handle CSRF and auth errors in production
    if (process.env.NODE_ENV === 'production') {
      if (this.isCsrfError(error)) {
        return this.handleCsrfError(config);
      }

      if (this.isAuthError(error)) {
        return this.handleAuthError(error);
      }
    }

    // Handle retries
    if (this.shouldRetryRequest(error, config)) {
      return this.retryRequest(config);
    }

    // Let the error propagate for test scenarios
    return Promise.reject(error);
  }

  private isCsrfError(error: AxiosError<ErrorResponse>): boolean {
    return error.response?.status === 403 && error.response?.data?.message === 'Invalid CSRF token';
  }

  private isAuthError(error: AxiosError<ErrorResponse>): boolean {
    return error.response?.status === 401;
  }

  private shouldRetryRequest(error: AxiosError, config: AxiosRequestConfig & { _retry?: number }): boolean {
    return !!(
      this.retryConfig.retryableStatuses.includes(error.response?.status || 0) &&
      (!config._retry || config._retry < this.retryConfig.maxRetries)
    );
  }

  private async handleCsrfError(config: AxiosRequestConfig): Promise<any> {
    await this.refreshCsrfToken();
    if (this.csrfToken) {
      config.headers = { ...config.headers, 'X-CSRF-Token': this.csrfToken };
    }
    return this.client(config);
  }

  private handleAuthError(error: AxiosError): Promise<never> {
    localStorage.removeItem('auth_tokens');
    window.location.href = '/login';
    return Promise.reject(error);
  }

  private async retryRequest(config: AxiosRequestConfig & { _retry?: number }): Promise<any> {
    config._retry = (config._retry || 0) + 1;
    const delay = this.retryConfig.retryDelay * config._retry;
    
    await new Promise(resolve => setTimeout(resolve, delay));
    return this.client(config);
  }

  private async refreshCsrfToken(): Promise<void> {
    try {
      const response = await this.client.get('/csrf-token');
      this.csrfToken = response.data.token;
    } catch (error) {
      console.error('Failed to refresh CSRF token:', error);
      // If we can't refresh the CSRF token, we should redirect to login
      localStorage.removeItem('auth_tokens');
      window.location.href = '/login';
    }
  }

  private handleError(error: AxiosError<ErrorResponse>): ApiError {
    if (error.response) {
      return {
        name: 'ApiError',
        status: error.response.status,
        message: error.response.data?.message || 'An error occurred',
        data: error.response.data,
      };
    }
    if (error.request) {
      return {
        name: 'ApiError',
        status: 0,
        message: 'No response received from server',
      };
    }
    return {
      name: 'ApiError',
      status: 0,
      message: error.message || 'Unknown error occurred',
    };
  }

  protected async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    // Check if endpoint should be cached
    const shouldCache = this.CACHE_ENABLED_ENDPOINTS.some(endpoint => url.includes(endpoint));
    
    if (shouldCache) {
      // Generate cache key based on URL and query params
      const cacheKey = redisService.generateKey(url, config?.params);
      
      // Try to get from cache first
      const cachedData = await redisService.get<ApiResponse<T>>(cacheKey);
      if (cachedData) {
        return cachedData;
      }
      
      // If not in cache, make the request
      const response = await this.client.get<ApiResponse<T>>(url, config);
      
      // Cache the response
      await redisService.set(cacheKey, response.data, this.CACHE_TTL);
      
      return response.data;
    }
    
    // For non-cached endpoints, just make the request
    const response = await this.client.get<ApiResponse<T>>(url, config);
    return response.data;
  }

  public async post<T>(endpoint: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.post<ApiResponse<T>>(endpoint, data, config);
    return response.data;
  }

  protected async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.put<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  protected async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.client.delete<ApiResponse<T>>(url, config);
    return response.data;
  }

  // Form Analysis Endpoints
  public formAnalysis = {
    analyze: async (formData: FormData) =>
      this.post<FormAnalysisResult>('/form-analysis/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }),

    getHistory: async (params?: QueryParams) =>
      this.get<FormAnalysisResult[]>('/form-analysis/history', { params }),

    getAnalysis: async (id: string) =>
      this.get<FormAnalysisResult>(`/form-analysis/${id}`),

    save: async (result: FormAnalysisResult) =>
      this.post<FormAnalysisResult>('/form-analysis/save', result),

    export: async (id: string, format: 'pdf' | 'json') =>
      this.get<Blob>(`/form-analysis/${id}/export`, {
        params: { format },
        responseType: 'blob'
      })
  };

  // User Profile Endpoints
  public profile = {
    get: async () => 
      this.get<any>('/profile'),

    update: async (data: any) =>
      this.put<any>('/profile', data),

    updateAvatar: async (formData: FormData) =>
      this.post<{ avatarUrl: string }>('/profile/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
  };

  // Authentication Endpoints
  public auth = {
    login: async (email: string, password: string) => 
      this.post<{ user: any; tokens: any }>('/auth/login', { email, password }),

    register: async (data: { email: string; password: string; username: string }) =>
      this.post<{ user: any; tokens: any }>('/auth/register', data),

    logout: async () => {
      await this.post<void>('/auth/logout');
      localStorage.removeItem('auth_tokens');
    },

    validate: async () => 
      this.get<any>('/auth/validate'),

    refreshToken: async (refreshToken: string) =>
      this.post<{ tokens: any }>('/auth/refresh', { refreshToken })
  };

  // Form Check Endpoints
  public formChecks = {
    upload: (formData: FormData, options?: { onUploadProgress?: (progressEvent: AxiosProgressEvent) => void }) =>
      this.client.post<ApiResponse<any>>('/form-checks/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        ...options,
      }),
    getAll: () => this.client.get<ApiResponse<any>>('/form-checks'),
    getById: (id: string) => this.client.get<ApiResponse<any>>(`/form-checks/${id}`),
    delete: (id: number) => this.client.delete<ApiResponse<void>>(`/form-checks/${id}`),
  };

  public exercises = {
    getAll: (): Promise<ApiResponse<Exercise[]>> => {
      return this.get('/exercises');
    },

    get: (id: string): Promise<ApiResponse<Exercise>> => {
      return this.get(`/exercises/${id}`);
    },

    create: (exercise: Omit<Exercise, 'id'>): Promise<ApiResponse<Exercise>> => {
      return this.post('/exercises', exercise);
    },

    update: (id: string, exercise: Partial<Exercise>): Promise<ApiResponse<Exercise>> => {
      return this.put(`/exercises/${id}`, exercise);
    },

    delete: (id: string): Promise<ApiResponse<void>> => {
      return this.delete(`/exercises/${id}`);
    },

    search: (query: string): Promise<ApiResponse<Exercise[]>> => {
      return this.get('/exercises/search', { params: { query } });
    },

    filter: (filters: {
      type?: string;
      difficulty?: string;
      equipment?: string[];
      targetMuscles?: string[];
    }): Promise<ApiResponse<Exercise[]>> => {
      return this.get('/exercises/filter', { params: filters });
    }
  };

  public poseAnalysis = {
    analyze: (data: { keypoints: any[] }) =>
      this.post<PoseAnalysisResult>('/api/pose-analysis/analyze', data),
    detect: (data: { videoUrl: string }) =>
      this.post<{ keypoints: any[] }>('/api/pose-analysis/detect', data),
  };
}

export const apiService = new ApiService();