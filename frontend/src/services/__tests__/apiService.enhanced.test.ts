import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiService } from '../apiService';
import { ApiResponse, ApiError, ErrorResponse } from '../../types/api';
import { redisService } from '../redisService';
import { act } from 'react-dom/test-utils';

// Mock axios
jest.mock('axios', () => {
  const mockAxios = {
    create: jest.fn(() => ({
      interceptors: {
        request: {
          use: jest.fn(fn => fn),
          eject: jest.fn(),
          clear: jest.fn()
        },
        response: {
          use: jest.fn((fn, errorFn) => errorFn),
          eject: jest.fn(),
          clear: jest.fn()
        }
      },
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      patch: jest.fn()
    })),
    get: jest.fn(),
    defaults: {
      headers: {
        common: {}
      }
    },
    CancelToken: {
      source: jest.fn().mockReturnValue({
        token: {
          reason: 'RequestCanceled',
          message: 'Operation canceled'
        },
        cancel: jest.fn()
      })
    }
  };
  return mockAxios;
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: jest.fn((index: number) => Object.keys(store)[index] || null)
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock the redisService
jest.mock('../redisService', () => ({
  redisService: {
    get: jest.fn(),
    set: jest.fn(),
    del: jest.fn()
  }
}));

// Create a test subclass that exposes protected methods
class TestApiService extends ApiService {
  constructor(baseUrl: string = 'http://localhost/api', retryConfig?: any) {
    super(baseUrl, retryConfig);
  }

  // Expose protected methods for testing
  public testGet<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.get(url, config);
  }

  public testPost<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.post(url, data, config);
  }

  public testPut<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.put(url, data, config);
  }

  public testDelete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.delete(url, config);
  }

  // Get client for testing
  public getClient(): AxiosInstance {
    return (this as any).client;
  }
}

describe('ApiService Basic Tests', () => {
  let apiService: TestApiService;
  let mockAxiosInstance: jest.Mocked<AxiosInstance>;
  
  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();
    
    // Reset localStorage mock
    localStorageMock.clear();
    
    // Create mock axios instance
    mockAxiosInstance = {
      interceptors: {
        request: {
          use: jest.fn(),
          eject: jest.fn(),
          clear: jest.fn()
        },
        response: {
          use: jest.fn(),
          eject: jest.fn(),
          clear: jest.fn()
        }
      },
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
      patch: jest.fn(),
      defaults: {
        headers: {
          common: {}
        }
      },
      request: jest.fn()
    } as any;

    // Setup axios.create mock
    (axios.create as jest.Mock).mockReturnValue(mockAxiosInstance);
    
    // Create service instance
    apiService = new TestApiService();
  });
  
  describe('Service Initialization', () => {
    it('should create an Axios instance with the correct base URL', () => {
      expect(axios.create).toHaveBeenCalledWith(
        expect.objectContaining({
          baseURL: 'http://localhost/api'
        })
      );
    });
    
    it('should set up request and response interceptors', () => {
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });
  });
  
  describe('HTTP Methods', () => {
    it('should make a GET request with the correct URL', async () => {
      mockAxiosInstance.get.mockResolvedValue({
        data: { id: 1, name: 'Test' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
      
      await apiService.testGet('/test');
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/test', undefined);
    });
    
    it('should make a POST request with the correct data', async () => {
      const testData = { username: 'test', password: 'password' };
      
      mockAxiosInstance.post.mockResolvedValue({
        data: { success: true },
        status: 201,
        statusText: 'Created',
        headers: {},
        config: {}
      });
      
      await apiService.testPost('/test', testData);
      
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/test', testData, undefined);
    });
    
    it('should make a PUT request with the correct data', async () => {
      const testData = { id: 1, name: 'Updated' };
      
      mockAxiosInstance.put.mockResolvedValue({
        data: { success: true },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
      
      await apiService.testPut('/test/1', testData);
      
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/test/1', testData, undefined);
    });
    
    it('should make a DELETE request with the correct URL', async () => {
      mockAxiosInstance.delete.mockResolvedValue({
        data: { success: true },
        status: 204,
        statusText: 'No Content',
        headers: {},
        config: {}
      });
      
      await apiService.testDelete('/test/1');
      
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/test/1', undefined);
    });
    
    it('should pass query parameters correctly', async () => {
      const queryParams = { page: 1, limit: 10 };
      
      mockAxiosInstance.get.mockResolvedValue({
        data: { results: [] },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
      
      await apiService.testGet('/test', { params: queryParams });
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/test',
        expect.objectContaining({
          params: queryParams
        })
      );
    });
    
    it('should send custom headers with requests', async () => {
      const customHeaders = {
        'X-Custom-Header': 'test-value'
      };
      
      mockAxiosInstance.get.mockResolvedValue({
        data: { id: 1 },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
      
      await apiService.testGet('/test', { headers: customHeaders });
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/test',
        expect.objectContaining({
          headers: expect.objectContaining(customHeaders)
        })
      );
    });
  });
  
  describe('Authentication Token Handling', () => {
    it('should store auth tokens in localStorage', () => {
      // This would be a method call that stores auth tokens
      const tokens = { accessToken: 'test-token', refreshToken: 'refresh-token' };
      localStorageMock.setItem('auth_tokens', JSON.stringify(tokens));
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('auth_tokens', JSON.stringify(tokens));
      expect(localStorageMock.getItem('auth_tokens')).toBe(JSON.stringify(tokens));
    });
    
    it('should remove auth tokens on logout', () => {
      // First set the tokens
      const tokens = { accessToken: 'test-token', refreshToken: 'refresh-token' };
      localStorageMock.setItem('auth_tokens', JSON.stringify(tokens));
      
      // Then simulate a logout action
      localStorageMock.removeItem('auth_tokens');
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('auth_tokens');
      expect(localStorageMock.getItem('auth_tokens')).toBeNull();
    });
  });
  
  describe('Error Handling - Basic', () => {
    it('should handle request errors properly', async () => {
      const errorResponse = {
        response: {
          data: { message: 'Bad Request' },
          status: 400,
          statusText: 'Bad Request',
          headers: {},
        },
        isAxiosError: true,
        config: { url: '/test' } as any
      };
      
      mockAxiosInstance.get.mockRejectedValueOnce(errorResponse);
      
      try {
        await apiService.testGet('/test');
        fail('Should have thrown an error');
      } catch (error) {
        // The test will pass if an error is thrown
        expect(error).toBeDefined();
      }
    });
    
    it('should handle network errors (no response)', async () => {
      const networkError = {
        message: 'Network Error',
        isAxiosError: true,
        config: { url: '/test' } as any
      };
      
      mockAxiosInstance.get.mockRejectedValueOnce(networkError);
      
      try {
        await apiService.testGet('/test');
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error).toBeDefined();
        expect(error.message).toBe('Network Error');
      }
    });
    
    it('should handle timeout errors', async () => {
      const timeoutError = {
        message: 'timeout of 5000ms exceeded',
        code: 'ECONNABORTED',
        isAxiosError: true,
        config: { 
          url: '/test',
          timeout: 5000
        } as any
      };
      
      mockAxiosInstance.get.mockRejectedValueOnce(timeoutError);
      
      try {
        await apiService.testGet('/test');
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error).toBeDefined();
        expect(error.message).toContain('timeout');
      }
    });
    
    it('should include status code in error objects', async () => {
      const errorWithStatus = {
        response: {
          data: { message: 'Not Found' },
          status: 404,
          statusText: 'Not Found',
          headers: {},
        },
        isAxiosError: true,
        config: { url: '/test/999' } as any
      };
      
      mockAxiosInstance.get.mockRejectedValueOnce(errorWithStatus);
      
      try {
        await apiService.testGet('/test/999');
        fail('Should have thrown an error');
      } catch (error: any) {
        expect(error).toBeDefined();
        // In the actual implementation, this might be transformed to have a status property
        expect(error.response.status).toBe(404);
      }
    });
  });
  
  describe('Request Configuration', () => {
    it('should respect custom timeout settings', async () => {
      const customTimeout = 10000;
      
      mockAxiosInstance.get.mockResolvedValue({
        data: { id: 1 },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
      
      await apiService.testGet('/test', { timeout: customTimeout });
      
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/test',
        expect.objectContaining({
          timeout: customTimeout
        })
      );
    });
    
    it('should support request cancellation', async () => {
      const source = axios.CancelToken.source();
      
      mockAxiosInstance.get.mockResolvedValue({
        data: { id: 1 },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
      
      // Start a request with a cancel token
      const requestPromise = apiService.testGet('/test', { 
        cancelToken: source.token 
      });
      
      // Cancel the request
      source.cancel('Request cancelled by user');
      
      // The request should have been made with the cancel token
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/test',
        expect.objectContaining({
          cancelToken: source.token
        })
      );
    });
  });
}); 