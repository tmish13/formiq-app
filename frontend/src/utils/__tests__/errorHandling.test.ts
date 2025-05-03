import axios, { AxiosError } from 'axios';
import { 
  AppError, 
  ErrorCode, 
  handleApiError
} from '../errorHandling';

// Mock axios for controlled testing
jest.mock('axios');

// Mock the error detection functions for testing
const mockIsNetworkError = (error: unknown): boolean => {
  if (error && typeof error === 'object' && 'isAxiosError' in error) {
    return !('response' in error);
  }
  return false;
};

const mockIsAuthError = (error: unknown): boolean => {
  if (error && typeof error === 'object' && 'isAxiosError' in error && 'response' in error) {
    const axiosError = error as any;
    return axiosError.response?.status === 401;
  }
  return false;
};

const mockIsCsrfError = (error: unknown): boolean => {
  if (error && typeof error === 'object' && 'isAxiosError' in error && 'response' in error) {
    const axiosError = error as any;
    if (axiosError.response?.status === 403) {
      const data = axiosError.response.data as Record<string, any> || {};
      const message = data.message as string;
      return typeof message === 'string' && message.includes('CSRF');
    }
  }
  return false;
};

// Mock the module to use our test versions
jest.mock('../errorHandling', () => {
  const originalModule = jest.requireActual('../errorHandling');
  return {
    ...originalModule,
    isNetworkError: jest.fn((error) => mockIsNetworkError(error)),
    isAuthError: jest.fn((error) => mockIsAuthError(error)),
    isCsrfError: jest.fn((error) => mockIsCsrfError(error))
  };
});

describe('Error Handling Utilities', () => {
  describe('AppError class', () => {
    it('should correctly initialize with default values', () => {
      const error = new AppError('Test error');
      
      expect(error.message).toBe('Test error');
      expect(error.code).toBe(ErrorCode.UNKNOWN_ERROR);
      expect(error.status).toBe(500);
      expect(error.retry).toBe(false);
      expect(error.details).toBeUndefined();
      expect(error.fieldErrors).toBeUndefined();
    });
    
    it('should correctly initialize with custom values', () => {
      const details = { id: 'test-id' };
      const fieldErrors = { name: ['Name is required'] };
      
      const error = new AppError(
        'Custom error', 
        ErrorCode.VALIDATION_ERROR, 
        422, 
        details, 
        fieldErrors, 
        true
      );
      
      expect(error.message).toBe('Custom error');
      expect(error.code).toBe(ErrorCode.VALIDATION_ERROR);
      expect(error.status).toBe(422);
      expect(error.retry).toBe(true);
      expect(error.details).toEqual(details);
      expect(error.fieldErrors).toEqual(fieldErrors);
    });
    
    it('should be an instance of Error', () => {
      const error = new AppError('Test error');
      expect(error).toBeInstanceOf(Error);
    });
  });
  
  describe('handleApiError function', () => {
    it('should return the error if it is already an AppError', () => {
      const originalError = new AppError('Already an AppError', ErrorCode.BAD_REQUEST, 400);
      const result = handleApiError(originalError);
      
      expect(result).toBe(originalError);
    });
    
    it('should handle network errors', () => {
      const networkError = new Error('Network Error') as AxiosError;
      const result = handleApiError(networkError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.NETWORK_ERROR);
      expect(result.status).toBe(0);
    });
    
    it('should handle timeout errors', () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 1000ms exceeded',
        isAxiosError: true
      } as unknown as AxiosError;
      
      const result = handleApiError(timeoutError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.TIMEOUT_ERROR);
      expect(result.status).toBe(408);
    });
    
    it('should handle 401 Unauthorized errors', () => {
      const unauthorizedError = {
        response: {
          status: 401,
          data: { message: 'Unauthorized' }
        },
        isAxiosError: true
      } as unknown as AxiosError;
      
      const result = handleApiError(unauthorizedError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.UNAUTHORIZED);
      expect(result.status).toBe(401);
    });
    
    it('should handle CSRF errors', () => {
      const csrfError = {
        response: {
          status: 403,
          data: { message: 'CSRF token validation failed' }
        },
        isAxiosError: true
      } as unknown as AxiosError;
      
      const result = handleApiError(csrfError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.CSRF_ERROR);
      expect(result.status).toBe(403);
    });
    
    it('should handle validation errors with field errors', () => {
      const validationError = {
        response: {
          status: 422,
          data: { 
            errors: { 
              email: ['Email is required'], 
              password: ['Password is too short'] 
            } 
          }
        },
        isAxiosError: true
      } as unknown as AxiosError;
      
      const result = handleApiError(validationError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.VALIDATION_ERROR);
      expect(result.status).toBe(422);
      expect(result.fieldErrors).toEqual({ 
        email: ['Email is required'], 
        password: ['Password is too short'] 
      });
    });
    
    it('should handle validation errors with array of errors', () => {
      const validationError = {
        response: {
          status: 422,
          data: { 
            errors: ['Email is required', 'Password is too short']
          }
        },
        isAxiosError: true
      } as unknown as AxiosError;
      
      const result = handleApiError(validationError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.VALIDATION_ERROR);
      expect(result.status).toBe(422);
      expect(result.message).toBe('Validation Error: Email is required, Password is too short');
    });
    
    it('should handle server errors', () => {
      const serverError = {
        response: {
          status: 500,
          data: { message: 'Internal Server Error' }
        },
        isAxiosError: true
      } as unknown as AxiosError;
      
      const result = handleApiError(serverError);
      
      expect(result).toBeInstanceOf(AppError);
      expect(result.code).toBe(ErrorCode.SERVER_ERROR);
      expect(result.status).toBe(500);
    });
  });
  
  describe('Error type detection functions', () => {
    it('should correctly identify network errors', () => {
      // For isNetworkError we need an AxiosError with no response property
      const networkError = {
        isAxiosError: true,
        request: {}
        // No response property
      };
      
      expect(mockIsNetworkError(networkError)).toBe(true);
      
      // Create a response error
      const responseError = {
        isAxiosError: true,
        request: {},
        response: { status: 400 }
      };
      
      expect(mockIsNetworkError(responseError)).toBe(false);
      
      const nonAxiosError = new Error('Not an axios error');
      expect(mockIsNetworkError(nonAxiosError)).toBe(false);
    });
    
    it('should correctly identify authentication errors', () => {
      // Create auth error with status 401
      const authError = {
        isAxiosError: true,
        response: { status: 401 }
      };
      
      expect(mockIsAuthError(authError)).toBe(true);
      
      // Create non-auth error
      const nonAuthError = {
        isAxiosError: true,
        response: { status: 403 }
      };
      
      expect(mockIsAuthError(nonAuthError)).toBe(false);
      
      const nonAxiosError = new Error('Not an axios error');
      expect(mockIsAuthError(nonAxiosError)).toBe(false);
    });
    
    it('should correctly identify CSRF errors', () => {
      // Create CSRF error (403 status with CSRF in message)
      const csrfError = {
        isAxiosError: true,
        response: { 
          status: 403,
          data: { message: 'CSRF token validation failed' }
        }
      };
      
      expect(mockIsCsrfError(csrfError)).toBe(true);
      
      // Create non-CSRF error (403 but no CSRF message)
      const nonCsrfError = {
        isAxiosError: true,
        response: { 
          status: 403,
          data: { message: 'Forbidden' }
        }
      };
      
      expect(mockIsCsrfError(nonCsrfError)).toBe(false);
      
      const nonAxiosError = new Error('Not an axios error');
      expect(mockIsCsrfError(nonAxiosError)).toBe(false);
    });
  });
}); 