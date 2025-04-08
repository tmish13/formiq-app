import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { store } from '../store';
import { logout, setToken } from '../store/slices/authSlice';
import { ApiError, handleApiError } from '../utils/errorHandling';
import { apiCache } from '../utils/cache';
import { networkService } from './networkService';
import { storageService } from './storageService';
import { Capacitor } from '@capacitor/core';

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

// Extend AxiosRequestConfig to include metadata
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  metadata?: {
    startTime: Date;
    offlineQueueable?: boolean;
  };
}

// Extend AxiosError to include cache property
interface ExtendedAxiosError extends AxiosError {
  isCache?: boolean;
  isOffline?: boolean;
  queuedRequestId?: string;
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

interface QueuedRequest {
  id: string;
  method: string;
  url: string;
  data?: any;
  config?: AxiosRequestConfig;
  timestamp: number;
}

// interface RetryConfig {
//   retries: number;
//   retryDelay: number;
//   retryStatusCodes: number[];
// }

class ApiService {
  private api: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: ApiError) => void;
  }> = [];
  private offlineQueue: QueuedRequest[] = [];
  private isProcessingQueue = false;
  private networkListener: (() => void) | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: getBaseUrl(),
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 15000, // 15 seconds timeout
    });

    // Configure retry logic
    this.setupRetry();
    this.setupInterceptors();
    this.setupOfflineHandling();
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

  private setupOfflineHandling() {
    // Load previously queued requests from storage
    this.loadOfflineQueue();

    // Listen for network status changes
    this.networkListener = networkService.subscribe(async (status) => {
      if (status.connected && this.offlineQueue.length > 0 && !this.isProcessingQueue) {
        await this.processOfflineQueue();
      }
    });

    // Process offline queue immediately if we're online and have queued requests
    networkService.getStatus().then(status => {
      if (status.connected && this.offlineQueue.length > 0) {
        this.processOfflineQueue();
      }
    });
  }

  private async loadOfflineQueue() {
    try {
      const queue = await storageService.getWorkoutQueue();
      this.offlineQueue = queue.map(item => ({
        id: item.queueId,
        method: item.method,
        url: item.url,
        data: item.data,
        config: item.config,
        timestamp: new Date(item.queuedAt).getTime()
      }));
    } catch (error) {
      console.error('Failed to load offline queue', error);
      this.offlineQueue = [];
    }
  }

  private async saveOfflineQueue() {
    try {
      // Create a snapshot of the queue to avoid race conditions
      const queueSnapshot = [...this.offlineQueue];
      
      // First remove all existing entries to prevent duplicates
      await storageService.clearWorkoutQueue();
      
      // Then save all current entries
      if (queueSnapshot.length > 0) {
        await Promise.all(
          queueSnapshot.map(request => 
            storageService.addToWorkoutQueue({
              method: request.method,
              url: request.url,
              data: request.data,
              config: request.config,
              queueId: request.id,
              queuedAt: new Date(request.timestamp).toISOString()
            })
          )
        );
        console.info(`Saved ${queueSnapshot.length} requests to offline queue`);
      }
    } catch (error) {
      console.error('Failed to save offline queue', error);
      // Implement retry logic with exponential backoff
      setTimeout(() => {
        this.saveOfflineQueue();
      }, 5000); // Retry after 5 seconds
    }
  }

  private async processOfflineQueue() {
    if (this.isProcessingQueue || this.offlineQueue.length === 0) {
      return;
    }

    this.isProcessingQueue = true;

    const isOnline = await networkService.isOnline();
    if (!isOnline) {
      this.isProcessingQueue = false;
      return;
    }

    try {
      // Process queue in order (FIFO)
      const queue = [...this.offlineQueue];
      this.offlineQueue = [];

      for (const request of queue) {
        try {
          const { method, url, data, config } = request;
          
          switch (method.toLowerCase()) {
            case 'post':
              await this.post(url, data, config);
              break;
            case 'put':
              await this.put(url, data, config);
              break;
            case 'patch':
              await this.patch(url, data, config);
              break;
            case 'delete':
              await this.delete(url, config);
              break;
            default:
              console.warn(`Unsupported method ${method} in offline queue`);
          }
          
          // Remove from storage after successful processing
          await storageService.removeFromWorkoutQueue(request.id);
        } catch (error) {
          console.error('Failed to process queued request', error);
          // Add back to queue if it's not a 4xx error (except for 408 Request Timeout)
          const status = (error as AxiosError)?.response?.status;
          if (!status || status >= 500 || status === 408) {
            this.offlineQueue.push(request);
          } else {
            // For 4xx errors, remove from storage as they won't succeed on retry
            await storageService.removeFromWorkoutQueue(request.id);
          }
        }
      }
    } finally {
      this.isProcessingQueue = false;
      
      // If there are still items in the queue, save them
      if (this.offlineQueue.length > 0) {
        this.saveOfflineQueue();
      }
    }
  }

  private addToOfflineQueue(
    method: string, 
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig
  ): string {
    const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const queuedRequest: QueuedRequest = {
      id,
      method,
      url,
      data,
      config,
      timestamp: Date.now()
    };
    
    this.offlineQueue.push(queuedRequest);
    this.saveOfflineQueue();
    
    return id;
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
        config.metadata = { 
          startTime: new Date(),
          ...(config.metadata || {})
        };
        
        // Add CSRF token for all non-GET requests
        const csrfToken = localStorage.getItem('csrf_token');
        if (csrfToken && config.method && config.method.toLowerCase() !== 'get') {
          config.headers['X-CSRF-Token'] = csrfToken;
        }
        
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

            const response = await this.api.post<ApiResponse<{ token: string; refreshToken: string; csrf_token?: string }>>('/auth/refresh', {
              refreshToken,
            });

            const { token } = response.data.data;
            store.dispatch(setToken(token));
            localStorage.setItem('refreshToken', response.data.data.refreshToken);
            
            // Store CSRF token if provided
            if (response.data.data.csrf_token) {
              localStorage.setItem('csrf_token', response.data.data.csrf_token);
            }

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
    this.failedQueue.forEach(request => {
      if (error) {
        request.reject(error);
      } else if (token) {
        request.resolve(token);
      }
    });

    this.failedQueue = [];
  }

  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.get<ApiResponse<T>>(url, config);
      return response.data.data;
    } catch (error) {
      if ((error as ExtendedAxiosError).isCache) {
        return ((error as ExtendedAxiosError).response?.data as ApiResponse<T>).data;
      }

      // For offline GET requests, try to get from cache first
      if (!(await networkService.isOnline())) {
        const cachedData = apiCache.get(url);
        if (cachedData) {
          return (cachedData as ApiResponse<T>).data;
        }
      }

      throw error;
    }
  }

  public async post<T>(
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig & { offlineQueueable?: boolean }
  ): Promise<T> {
    try {
      // Check if we're offline and this is an offline-queueable request
      if (config?.offlineQueueable && !(await networkService.isOnline())) {
        const requestId = this.addToOfflineQueue('post', url, data, config);
        return { queued: true, queuedRequestId: requestId } as any;
      }
      
      const response = await this.api.post<ApiResponse<T>>(url, data, config);
      return response.data.data;
    } catch (error) {
      if ((error as ExtendedAxiosError).isOffline) {
        return { queued: true } as any;
      }
      throw error;
    }
  }

  public async put<T>(
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig & { offlineQueueable?: boolean }
  ): Promise<T> {
    try {
      // Check if we're offline and this is an offline-queueable request
      if (config?.offlineQueueable && !(await networkService.isOnline())) {
        const requestId = this.addToOfflineQueue('put', url, data, config);
        return { queued: true, queuedRequestId: requestId } as any;
      }
      
      const response = await this.api.put<ApiResponse<T>>(url, data, config);
      return response.data.data;
    } catch (error) {
      if ((error as ExtendedAxiosError).isOffline) {
        return { queued: true } as any;
      }
      throw error;
    }
  }

  public async delete<T>(
    url: string, 
    config?: AxiosRequestConfig & { offlineQueueable?: boolean }
  ): Promise<T> {
    try {
      // Check if we're offline and this is an offline-queueable request
      if (config?.offlineQueueable && !(await networkService.isOnline())) {
        const requestId = this.addToOfflineQueue('delete', url, undefined, config);
        return { queued: true, queuedRequestId: requestId } as any;
      }
      
      const response = await this.api.delete<ApiResponse<T>>(url, config);
      return response.data.data;
    } catch (error) {
      if ((error as ExtendedAxiosError).isOffline) {
        return { queued: true } as any;
      }
      throw error;
    }
  }

  public async patch<T>(
    url: string, 
    data?: any, 
    config?: AxiosRequestConfig & { offlineQueueable?: boolean }
  ): Promise<T> {
    try {
      // Check if we're offline and this is an offline-queueable request
      if (config?.offlineQueueable && !(await networkService.isOnline())) {
        const requestId = this.addToOfflineQueue('patch', url, data, config);
        return { queued: true, queuedRequestId: requestId } as any;
      }
      
      const response = await this.api.patch<ApiResponse<T>>(url, data, config);
      return response.data.data;
    } catch (error) {
      if ((error as ExtendedAxiosError).isOffline) {
        return { queued: true } as any;
      }
      throw error;
    }
  }
}

export const apiService = new ApiService(); 