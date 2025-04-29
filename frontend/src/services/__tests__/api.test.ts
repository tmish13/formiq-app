import { ApiService } from '../../services/apiService';
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { rest } from 'msw';
import { server } from '../../../tests/utils/testServer';
import { ApiResponse } from '../../types/api';
import { DefaultBodyType, PathParams, ResponseResolver, RestContext, RestRequest } from 'msw';

// Mock axios
jest.mock('axios', () => {
  const mockAxios = {
    create: jest.fn(() => ({
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
      patch: jest.fn()
    })),
    defaults: {
      headers: {
        common: {}
      }
    }
  };
  return mockAxios;
});

// Create a test subclass that exposes protected methods
class TestApiService extends ApiService {
  constructor() {
    super('http://localhost/api');
  }

  // Expose protected methods for testing
  public get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.get(url, config);
  }

  public put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.put(url, data, config);
  }

  public delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    return super.delete(url, config);
  }

  // Expose client for testing
  public getClient(): AxiosInstance {
    return this.client;
  }
}

describe('ApiService', () => {
  let apiService: TestApiService;
  let mockAxiosInstance: jest.Mocked<AxiosInstance>;

  beforeEach(() => {
    // Clear all mocks
    jest.clearAllMocks();

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
      }
    } as any;

    // Setup axios.create mock
    (axios.create as jest.Mock).mockReturnValue(mockAxiosInstance);

    // Create service instance
    apiService = new TestApiService();
  });

  describe('initialization', () => {
    it('should create axios instance with correct base URL', () => {
      expect(axios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost/api',
        headers: expect.any(Object)
      });
    });

    it('should setup request interceptors', () => {
      expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
    });

    it('should setup response interceptors', () => {
      expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
    });
  });

  describe('request methods', () => {
    const mockResponse = {
      data: { test: 'data' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {} as AxiosRequestConfig
    };

    beforeEach(() => {
      mockAxiosInstance.get.mockResolvedValue(mockResponse);
      mockAxiosInstance.post.mockResolvedValue(mockResponse);
      mockAxiosInstance.put.mockResolvedValue(mockResponse);
      mockAxiosInstance.delete.mockResolvedValue(mockResponse);
    });

    it('should make GET request', async () => {
      await apiService.get('/test');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/test', undefined);
    });

    it('should make POST request', async () => {
      const data = { test: 'data' };
      await apiService.post('/test', data);
      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/test', data, undefined);
    });

    it('should make PUT request', async () => {
      const data = { test: 'data' };
      await apiService.put('/test', data);
      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/test', data, undefined);
    });

    it('should make DELETE request', async () => {
      await apiService.delete('/test');
      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/test', undefined);
    });
  });

  describe('error handling', () => {
    const mockError = {
      response: {
        data: { message: 'Test error' },
        status: 400,
        statusText: 'Bad Request',
        headers: {},
        config: {} as AxiosRequestConfig
      }
    };

    beforeEach(() => {
      mockAxiosInstance.get.mockRejectedValue(mockError);
    });

    it('should handle API errors', async () => {
      try {
        await apiService.get('/test');
      } catch (error) {
        expect(error).toEqual({
          message: 'Test error',
          status: 400
        });
      }
    });
  });
}); 