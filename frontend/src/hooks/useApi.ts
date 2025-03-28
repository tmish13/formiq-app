import { useState, useCallback } from 'react';
import api from '../config/api';
import { AxiosRequestConfig, AxiosProgressEvent, AxiosError } from 'axios';
import { apiCache } from '../utils/cache';

interface ApiConfig extends AxiosRequestConfig {
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
  skipCache?: boolean;
}

interface ApiErrorResponse {
  detail: string;
}

interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (config?: ApiConfig) => Promise<T | null>;
  reset: () => void;
}

export function useApi<T>(endpoint: string, method: 'get' | 'post' | 'put' | 'delete' = 'get'): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  const execute = useCallback(async (config?: ApiConfig): Promise<T | null> => {
    try {
      setLoading(true);
      setError(null);

      // Check cache for GET requests if not explicitly skipped
      if (method === 'get' && !config?.skipCache) {
        const cacheKey = `${method}:${endpoint}`;
        const cachedData = apiCache.get<T>(cacheKey);
        if (cachedData) {
          setData(cachedData);
          setLoading(false);
          return cachedData;
        }
      }

      const response = await api.request<T>({
        method,
        url: endpoint,
        ...config,
        headers: {
          ...config?.headers,
          'Accept': 'application/json',
        },
      });

      const responseData = response.data;
      setData(responseData);

      // Cache successful GET responses
      if (method === 'get' && !config?.skipCache) {
        const cacheKey = `${method}:${endpoint}`;
        apiCache.set(cacheKey, responseData);
      }

      return responseData;
    } catch (err) {
      const axiosError = err as AxiosError<ApiErrorResponse>;
      const errorMessage = axiosError.response?.data?.detail || 
                         axiosError.message || 
                         'An error occurred';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [endpoint, method]);

  return { data, loading, error, execute, reset };
}

export default useApi; 