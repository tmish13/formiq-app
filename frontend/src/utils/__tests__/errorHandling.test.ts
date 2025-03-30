import { handleApiError, AppError, ApiError } from '../errorHandling';
import { AxiosError } from 'axios';

describe('Error Handling', () => {
  describe('AppError', () => {
    it('should create an AppError with message', () => {
      const error = new AppError('Test error');
      expect(error.message).toBe('Test error');
      expect(error.name).toBe('AppError');
    });

    it('should create an AppError with message and code', () => {
      const error = new AppError('Test error', 'TEST_ERROR');
      expect(error.message).toBe('Test error');
      expect(error.code).toBe('TEST_ERROR');
      expect(error.name).toBe('AppError');
    });
  });

  describe('handleApiError', () => {
    it('should handle network errors', () => {
      const error = new Error('Network Error') as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Network connection error. Please check your internet connection.');
      expect(result.code).toBe('NETWORK_ERROR');
    });

    it('should handle timeout errors', () => {
      const error = new Error('timeout of 5000ms exceeded') as AxiosError;
      error.code = 'ECONNABORTED';
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Request timed out. Please try again.');
      expect(result.code).toBe('TIMEOUT_ERROR');
    });

    it('should handle 401 unauthorized errors', () => {
      const error = {
        response: {
          status: 401,
          data: { message: 'Unauthorized' },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Your session has expired. Please log in again.');
      expect(result.code).toBe('UNAUTHORIZED');
    });

    it('should handle 403 forbidden errors', () => {
      const error = {
        response: {
          status: 403,
          data: { message: 'Forbidden' },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('You do not have permission to perform this action.');
      expect(result.code).toBe('FORBIDDEN');
    });

    it('should handle 404 not found errors', () => {
      const error = {
        response: {
          status: 404,
          data: { message: 'Not Found' },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('The requested resource was not found.');
      expect(result.code).toBe('NOT_FOUND');
    });

    it('should handle 422 validation errors', () => {
      const error = {
        response: {
          status: 422,
          data: {
            message: 'Validation Error',
            errors: ['Field is required'],
          },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Validation Error: Field is required');
      expect(result.code).toBe('VALIDATION_ERROR');
    });

    it('should handle 429 rate limit errors', () => {
      const error = {
        response: {
          status: 429,
          data: { message: 'Too Many Requests' },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Too many requests. Please try again later.');
      expect(result.code).toBe('RATE_LIMIT_ERROR');
    });

    it('should handle 500 server errors', () => {
      const error = {
        response: {
          status: 500,
          data: { message: 'Internal Server Error' },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('An unexpected error occurred. Please try again later.');
      expect(result.code).toBe('SERVER_ERROR');
    });

    it('should handle unknown errors', () => {
      const error = new Error('Unknown error') as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('An unexpected error occurred. Please try again later.');
      expect(result.code).toBe('UNKNOWN_ERROR');
    });

    it('should handle errors with custom messages', () => {
      const error = {
        response: {
          status: 400,
          data: { message: 'Custom error message' },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Custom error message');
      expect(result.code).toBe('BAD_REQUEST');
    });

    it('should handle errors with multiple validation messages', () => {
      const error = {
        response: {
          status: 422,
          data: {
            message: 'Validation Error',
            errors: ['Field 1 is required', 'Field 2 is invalid'],
          },
        },
      } as AxiosError;
      const result = handleApiError(error);
      expect(result).toBeInstanceOf(AppError);
      expect(result.message).toBe('Validation Error: Field 1 is required, Field 2 is invalid');
      expect(result.code).toBe('VALIDATION_ERROR');
    });
  });
}); 