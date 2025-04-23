import { useState, useCallback, useEffect } from 'react';
import api from '../config/api';
import { AxiosRequestConfig, AxiosProgressEvent, AxiosError } from 'axios';
import { handleApiError, AppError, ErrorCode } from '../utils/errorHandling';
import { useNavigate, useLocation } from 'react-router-dom';

/**
 * Custom hook for making API requests
 * @param endpoint - API endpoint
 * @param method - HTTP method (get, post, put, delete)
 * @param immediateExecution - Whether to execute the request immediately
 * @param cacheTimeout - Time in milliseconds to cache GET requests
 * @returns - Object with loading, error, data states and execute/reset functions
 */
export function useApi<T>(
  endpoint: string,
  method: 'get' | 'post' | 'put' | 'delete' = 'get',
  immediateExecution = false,
  cacheTimeout = 300000 // 5 minutes
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const checkCache = useCallback((endpoint: string): T | null => {
    if (method.toLowerCase() !== 'get') return null;

    try {
      const cachedData = localStorage.getItem(`api_cache_${endpoint}`);
      if (cachedData) {
        const { data, timestamp } = JSON.parse(cachedData);
        const isExpired = Date.now() - timestamp > cacheTimeout;
        if (!isExpired) {
          return data;
        }
      }
    } catch (err) {
      // If there's an error reading from cache, just ignore and proceed with the request
      console.error('Cache read error:', err);
    }
    return null;
  }, [cacheTimeout, method]);

  const updateCache = useCallback((endpoint: string, data: T) => {
    if (method.toLowerCase() !== 'get') return;

    try {
      localStorage.setItem(
        `api_cache_${endpoint}`,
        JSON.stringify({
          data,
          timestamp: Date.now()
        })
      );
    } catch (err) {
      // If there's an error writing to cache, just log it and continue
      console.error('Cache write error:', err);
    }
  }, [method]);

  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  const execute = useCallback(async (config: AxiosRequestConfig = {}) => {
    setLoading(true);
    setError(null);

    // Check cache first for GET requests
    const cachedData = checkCache(endpoint);
    if (cachedData) {
      setData(cachedData);
      setLoading(false);
      return cachedData;
    }

    try {
      const response = await api.request({
        url: endpoint,
        method,
        ...config,
        headers: {
          'Accept': 'application/json',
          ...(config.headers || {})
        }
      });

      const responseData = response.data;
      setData(responseData);
      setLoading(false);

      // Update cache for GET requests
      if (method.toLowerCase() === 'get') {
        updateCache(endpoint, responseData);
      }

      return responseData;
    } catch (err) {
      setLoading(false);
      
      // Handle the error using handleApiError
      const appError = handleApiError(err);
      
      // Set the error message
      setError(appError.message);
      
      // Handle authentication errors by redirecting to login
      if (appError.code === ErrorCode.UNAUTHORIZED) {
        // Store the current location to redirect back after login
        navigate('/login', { state: { from: location.pathname } });
      }
      
      return null;
    }
  }, [endpoint, method, navigate, location.pathname, checkCache, updateCache]);

  // Execute immediately if specified
  useEffect(() => {
    if (immediateExecution) {
      execute();
    }
    // Since execute changes on every render (because of useCallback),
    // we only want to run this effect when immediateExecution changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [immediateExecution]);

  return { data, loading, error, execute, reset };
}

export default useApi; 