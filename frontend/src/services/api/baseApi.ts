import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
}

export class BaseApiService {
  protected api: AxiosInstance;

  protected constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:3000/api',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error) => {
        if (error.response?.status === 401) {
          // Handle token refresh or logout
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  protected async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response: AxiosResponse<T> = await this.api.get(url, config);
      return {
        data: response.data,
        status: response.status,
      };
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  protected async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response: AxiosResponse<T> = await this.api.post(url, data, config);
      return {
        data: response.data,
        status: response.status,
      };
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  protected async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response: AxiosResponse<T> = await this.api.put(url, data, config);
      return {
        data: response.data,
        status: response.status,
      };
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  protected async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    try {
      const response: AxiosResponse<T> = await this.api.delete(url, config);
      return {
        data: response.data,
        status: response.status,
      };
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  private handleError(error: any): never {
    const response = error.response;
    throw {
      status: response?.status || 500,
      message: response?.data?.message || 'An unexpected error occurred',
      data: response?.data || null,
    };
  }
} 