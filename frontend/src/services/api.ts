import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { store } from '../store';
import { logout, setToken } from '../store/slices/authSlice';
import { ApiError, handleApiError } from '../utils/errorHandling';
import { apiCache } from '../utils/cache';

// Extend AxiosRequestConfig to include metadata
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  metadata?: {
    startTime: Date;
  };
}

// Extend AxiosError to include cache property
interface ExtendedAxiosError extends AxiosError {
  isCache?: boolean;
  response?: AxiosResponse & {
    data: any;
    status: number;
  };
}

interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

interface RetryConfig {
  retries: number;
  retryDelay: number;
  retryCondition: (error: AxiosError) => boolean;
}

class ApiService {
  private api: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: ApiError) => void;
  }> = [];

  constructor() {
    this.api = axios.create({
      baseURL: (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 10000, // 10 seconds timeout
    });

    // Configure retry logic
    this.setupRetry();
    this.setupInterceptors();
  }

  private setupRetry() {
    let retryCount = 0;
    const maxRetries = 3;

    this.api.interceptors.response.use(
      response => response,
      async error => {
        const config = error.config as ExtendedAxiosRequestConfig;
        
        if (!config || retryCount >= maxRetries || error.response?.status === 401) {
          return Promise.reject(error);
        }

        if (error.response?.status === 429 || !error.response) {
          retryCount += 1;
          const delay = error.response?.headers['retry-after'] 
            ? parseInt(error.response.headers['retry-after']) * 1000
            : Math.min(1000 * Math.pow(2, retryCount), 10000);

          await new Promise(resolve => setTimeout(resolve, delay));
          return this.api(config);
        }

        return Promise.reject(error);
      }
    );
  }

  private setupInterceptors() {
    // Request interceptor
    this.api.interceptors.request.use(
      async (config: ExtendedAxiosRequestConfig) => {
        // Check cache for GET requests
        if (config.method?.toLowerCase() === 'get' && config.url) {
          const cachedData = apiCache.get(config.url);
          if (cachedData) {
            return Promise.reject({
              config,
              response: { data: cachedData, status: 304 },
              isCache: true,
            } as ExtendedAxiosError);
          }
        }

        const token = store.getState().auth.token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add request timestamp for performance monitoring
        config.metadata = { startTime: new Date() };
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.api.interceptors.response.use(
      async (response) => {
        // Cache successful GET requests
        if (response.config.method?.toLowerCase() === 'get' && response.config.url) {
          apiCache.set(response.config.url, response.data);
        }

        // Log request duration
        const config = response.config as ExtendedAxiosRequestConfig;
        if (config.metadata?.startTime) {
          const duration = new Date().getTime() - config.metadata.startTime.getTime();
          console.debug(`Request to ${config.url} took ${duration}ms`);
        }

        return response;
      },
      async (error: ExtendedAxiosError) => {
        // Handle cached responses
        if (error.isCache) {
          return Promise.resolve(error.response);
        }

        const originalRequest = error.config as ExtendedAxiosRequestConfig;

        if (!originalRequest) {
          return Promise.reject(error);
        }

        // Handle 401 errors
        if (error.response?.status === 401) {
          if (this.isRefreshing) {
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            })
              .then((token) => {
                originalRequest.headers.Authorization = `Bearer ${token}`;
                return this.api(originalRequest);
              })
              .catch((err) => Promise.reject(err));
          }

          this.isRefreshing = true;

          try {
            const refreshToken = localStorage.getItem('refreshToken');
            if (!refreshToken) {
              throw new Error('No refresh token available');
            }

            const response = await this.api.post<ApiResponse<{ token: string; refreshToken: string }>>('/auth/refresh', {
              refreshToken,
            });

            const { token } = response.data.data;
            store.dispatch(setToken(token));
            localStorage.setItem('refreshToken', response.data.data.refreshToken);

            this.processQueue(null, token);
            this.isRefreshing = false;

            originalRequest.headers.Authorization = `Bearer ${token}`;
            return this.api(originalRequest);
          } catch (refreshError) {
            this.processQueue(refreshError as ApiError, null);
            this.isRefreshing = false;
            store.dispatch(logout());
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(handleApiError(error));
      }
    );
  }

  private processQueue(error: ApiError | null, token: string | null) {
    this.failedQueue.forEach((prom) => {
      if (error) {
        prom.reject(error);
      } else {
        prom.resolve(token!);
      }
    });
    this.failedQueue = [];
  }

  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.get<ApiResponse<T>>(url, {
        ...config,
        headers: {
          ...config?.headers,
          'Cache-Control': config?.headers?.['Cache-Control'] || 'no-cache',
        },
      });
      return response.data.data;
    } catch (error) {
      const axiosError = error as ExtendedAxiosError;
      if (axiosError.isCache && axiosError.response) {
        return axiosError.response.data;
      }
      throw handleApiError(error);
    }
  }

  public async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.post<ApiResponse<T>>(url, data, config);
      return response.data.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  public async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.put<ApiResponse<T>>(url, data, config);
      // Invalidate cache for the updated resource
      if (response.status === 200 || response.status === 204) {
        apiCache.delete(url);
      }
      return response.data.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.delete<ApiResponse<T>>(url, config);
      // Invalidate cache for the deleted resource
      if (response.status === 200 || response.status === 204) {
        apiCache.delete(url);
      }
      return response.data.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  public async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.patch<ApiResponse<T>>(url, data, config);
      // Invalidate cache for the patched resource
      if (response.status === 200 || response.status === 204) {
        apiCache.delete(url);
      }
      return response.data.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

export const apiService = new ApiService(); 