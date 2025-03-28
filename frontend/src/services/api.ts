import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { store } from '../store';
import { logout, setToken } from '../store/slices/authSlice';
import { ApiError, handleApiError } from '../utils/errorHandling';

interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
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
      baseURL: process.env.REACT_APP_API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        const token = store.getState().auth.token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config;

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
      const response = await this.api.get<ApiResponse<T>>(url, config);
      return response.data.data;
    } catch (error) {
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
      return response.data.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    try {
      const response = await this.api.delete<ApiResponse<T>>(url, config);
      return response.data.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.patch(url, data, config);
    return response.data;
  }
}

export const apiService = new ApiService(); 