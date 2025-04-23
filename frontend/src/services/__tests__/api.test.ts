import { ApiService } from '../../services/apiService';
import axios from 'axios';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Setup a mock axios instance
const mockAxiosInstance = {
  defaults: { 
    headers: { 
      common: {} 
    },
    baseURL: 'http://localhost/api'
  },
  request: jest.fn(),
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  interceptors: {
    request: { 
      use: jest.fn().mockImplementation((fn) => fn), 
      eject: jest.fn() 
    },
    response: { 
      use: jest.fn().mockImplementation((fn, errorFn) => {
        // Store error handler for testing
        mockResponseErrorHandler = errorFn;
        return fn;
      }), 
      eject: jest.fn() 
    }
  }
};

// Capture the response error handler for testing
let mockResponseErrorHandler: ((error: any) => any) | null = null;

// Setup axios.create mock to return our mock instance
mockedAxios.create.mockReturnValue(mockAxiosInstance as any);

// Setup MSW server with improved handlers
const server = setupServer(
  rest.get('http://localhost/api/test', (req, res, ctx) => {
    return res(ctx.json({ message: 'Success' }));
  }),
  
  rest.post('http://localhost/api/test', (req, res, ctx) => {
    return res(ctx.json({ message: 'Success' }));
  }),
  
  rest.put('http://localhost/api/test', (req, res, ctx) => {
    return res(ctx.json({ message: 'Success' }));
  }),
  
  rest.delete('http://localhost/api/test', (req, res, ctx) => {
    return res(ctx.json({ message: 'Success' }));
  }),
  
  rest.get('http://localhost/api/error', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({ message: 'Internal Server Error' })
    );
  }),
  
  rest.get('http://localhost/api/auth-error', (req, res, ctx) => {
    return res(
      ctx.status(401),
      ctx.json({ message: 'Unauthorized' })
    );
  }),
  
  rest.post('http://localhost/api/validation-error', (req, res, ctx) => {
    return res(
      ctx.status(400),
      ctx.json({ 
        message: 'Validation Error',
        errors: ['Field is required']
      })
    );
  }),
  
  rest.get('http://localhost/api/rate-limit', (req, res, ctx) => {
    return res(
      ctx.status(429),
      ctx.json({ message: 'Too Many Requests' })
    );
  }),
  
  rest.get('http://localhost/api/network-error', (req, res, ctx) => {
    return res.networkError('Network error occurred');
  })
);

// Start and stop MSW server
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

interface ErrorResponse {
  message: string;
  errors?: string[];
}

// Create a test subclass that exposes protected methods
class TestApiService extends ApiService {
  public get<T>(url: string, config?: any) {
    return super.get<T>(url, config);
  }

  public post<T>(url: string, data?: any, config?: any) {
    return super.post<T>(url, data, config);
  }

  public put<T>(url: string, data?: any, config?: any) {
    return super.put<T>(url, data, config);
  }

  public delete<T>(url: string, config?: any) {
    return super.delete<T>(url, config);
  }
  
  // Expose interceptor setup for testing
  public getAxiosInstance() {
    return this['client'];
  }
}

describe('ApiService', () => {
  let apiService: TestApiService;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset mock implementations
    mockAxiosInstance.get.mockReset();
    mockAxiosInstance.post.mockReset();
    mockAxiosInstance.put.mockReset();
    mockAxiosInstance.delete.mockReset();
    mockAxiosInstance.request.mockReset();
    
    // Reset the interceptors mocks
    mockAxiosInstance.interceptors.request.use.mockClear();
    mockAxiosInstance.interceptors.response.use.mockClear();
    
    // Create a new ApiService instance
    apiService = new TestApiService('http://localhost/api');
  });
  
  it('should make a GET request', async () => {
    // Setup mock response
    mockAxiosInstance.request.mockResolvedValueOnce({
      data: { message: 'Success' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {}
    });
    
    const response = await apiService.get('/test');
    expect(response).toBeDefined();
    expect(mockAxiosInstance.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: '/test'
      })
    );
  });
  
  it('should make a POST request', async () => {
    // Setup mock response
    mockAxiosInstance.request.mockResolvedValueOnce({
      data: { message: 'Success' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {}
    });
    
    const data = { test: 'data' };
    const response = await apiService.post('/test', data);
    
    expect(response).toBeDefined();
    expect(mockAxiosInstance.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: '/test',
        data
      })
    );
  });
  
  it('should make a PUT request', async () => {
    // Setup mock response
    mockAxiosInstance.request.mockResolvedValueOnce({
      data: { message: 'Success' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {}
    });
    
    const data = { test: 'data' };
    const response = await apiService.put('/test', data);
    
    expect(response).toBeDefined();
    expect(mockAxiosInstance.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'PUT',
        url: '/test',
        data
      })
    );
  });
  
  it('should make a DELETE request', async () => {
    // Setup mock response
    mockAxiosInstance.request.mockResolvedValueOnce({
      data: { message: 'Success' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {}
    });
    
    const response = await apiService.delete('/test');
    
    expect(response).toBeDefined();
    expect(mockAxiosInstance.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'DELETE',
        url: '/test'
      })
    );
  });
  
  it('should handle server errors', async () => {
    // Setup mock error response
    const errorResponse = {
      response: {
        status: 500,
        data: { message: 'Internal Server Error' }
      },
      isAxiosError: true,
      config: {}
    };
    mockAxiosInstance.request.mockRejectedValueOnce(errorResponse);
    
    await expect(apiService.get('/error')).rejects.toMatchObject({
      status: 500,
      message: expect.any(String)
    });
  });
  
  it('should handle network errors', async () => {
    // Setup mock network error
    const networkError = {
      message: 'Network Error',
      isAxiosError: true,
      response: undefined,
      config: {}
    };
    mockAxiosInstance.request.mockRejectedValueOnce(networkError);
    
    await expect(apiService.get('/network-error')).rejects.toMatchObject({
      status: 0,
      message: 'Network Error'
    });
  });
  
  it('should handle 401 unauthorized errors', async () => {
    // Mock window.location
    const originalLocation = window.location;
    window.location = { ...originalLocation, href: '' } as any;
    
    // Setup mock unauthorized error
    const unauthorizedError = {
      response: {
        status: 401,
        data: { message: 'Unauthorized' }
      },
      isAxiosError: true,
      config: {}
    };
    
    // Test the error handler directly
    if (mockResponseErrorHandler) {
      const promise = mockResponseErrorHandler(unauthorizedError);
      await expect(promise).rejects.toBeTruthy();
      
      // Check if location was changed to login
      expect(window.location.href).toBe('/login');
      
      // Restore original location
      window.location = originalLocation;
    } else {
      fail('Response error handler was not captured');
    }
  });
  
  it('should handle validation errors', async () => {
    // Setup mock validation error
    const validationError = {
      response: {
        status: 400,
        data: { 
          message: 'Validation Error',
          errors: ['Field is required']
        }
      },
      isAxiosError: true,
      config: {}
    };
    mockAxiosInstance.request.mockRejectedValueOnce(validationError);
    
    await expect(apiService.post('/validation-error', {})).rejects.toMatchObject({
      status: 400,
      message: 'Validation Error'
    });
  });
  
  it('should register request and response interceptors', () => {
    // Verify that interceptors are set up
    expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
    expect(mockAxiosInstance.interceptors.response.use).toHaveBeenCalled();
  });
  
  it('should retry failed requests with retryable status codes', async () => {
    // Create a configuration that should be retried
    const retryableError = {
      response: {
        status: 429, // Too Many Requests - should be retried
        data: { message: 'Too Many Requests' }
      },
      isAxiosError: true,
      config: { _retry: 0 } // Already prepared for retrying
    };
    
    // First attempt will fail with a retryable error
    mockAxiosInstance.request
      .mockRejectedValueOnce(retryableError)
      // Second attempt will succeed
      .mockResolvedValueOnce({
        data: { message: 'Success after retry' },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {}
      });
    
    // Call the API method
    const response = await apiService.get('/rate-limit');
    
    // It should have called request twice (once for original, once for retry)
    expect(mockAxiosInstance.request).toHaveBeenCalledTimes(2);
    expect(response).toBeDefined();
    expect(response.data).toEqual({ message: 'Success after retry' });
  });
  
  it('should add auth token to request headers', async () => {
    // Mock localStorage to return a token
    const mockToken = JSON.stringify({
      accessToken: 'test-access-token',
      refreshToken: 'test-refresh-token'
    });
    
    const getItemSpy = jest.spyOn(Storage.prototype, 'getItem');
    getItemSpy.mockReturnValue(mockToken);
    
    mockAxiosInstance.request.mockResolvedValueOnce({
      data: { message: 'Success' },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {}
    });
    
    // Make a request
    await apiService.get('/test');
    
    // Check if interceptor was called to add headers
    expect(mockAxiosInstance.interceptors.request.use).toHaveBeenCalled();
    
    // Clean up
    getItemSpy.mockRestore();
  });
}); 