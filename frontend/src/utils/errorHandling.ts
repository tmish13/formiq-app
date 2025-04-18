import { AxiosError } from 'axios';

export enum ErrorCode {
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',
  NETWORK_ERROR = 'NETWORK_ERROR',
  AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  RATE_LIMIT_ERROR = 'RATE_LIMIT_ERROR',
  SERVER_ERROR = 'SERVER_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',
  CSRF_ERROR = 'CSRF_ERROR',
  API_ERROR = 'API_ERROR',
  BAD_REQUEST = 'BAD_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND'
}

export interface ApiError {
  message: string;
  code: ErrorCode | string;
  status: number;
  details?: Record<string, any>;
  fieldErrors?: Record<string, string[]>;
  retry?: boolean;
}

export class AppError extends Error {
  code: ErrorCode | string;
  status: number;
  details?: Record<string, any>;
  fieldErrors?: Record<string, string[]>;
  retry: boolean;

  constructor(
    message: string,
    code: ErrorCode | string = ErrorCode.UNKNOWN_ERROR,
    status: number = 500,
    details?: Record<string, any>,
    fieldErrors?: Record<string, string[]>,
    retry: boolean = false
  ) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.status = status;
    this.details = details;
    this.fieldErrors = fieldErrors;
    this.retry = retry;
    
    // This is needed for proper instanceof checks with classes that extend Error
    Object.setPrototypeOf(this, AppError.prototype);
  }
}

export const handleApiError = (error: unknown): AppError => {
  if (error instanceof AppError) {
    return error;
  }

  // Special handling for network errors with pattern match for error message
  if (error instanceof Error && error.message === 'Network Error') {
    return new AppError(
      'Network connection error. Please check your internet connection.',
      ErrorCode.NETWORK_ERROR,
      0
    );
  }

  // Special handling for timeout errors
  const axiosError = error as AxiosError;
  if (
    axiosError && 
    axiosError.message && 
    typeof axiosError.message === 'string' && 
    axiosError.message.includes('timeout') && 
    axiosError.code === 'ECONNABORTED'
  ) {
    return new AppError(
      'Request timed out. Please try again.',
      ErrorCode.TIMEOUT_ERROR,
      408
    );
  }

  if (axiosError && axiosError.response) {
    const status = axiosError.response?.status || 0;
    const data = axiosError.response?.data as Record<string, any> || {};
    
    // Handle based on status code
    switch (status) {
      case 401:
        return new AppError(
          'Your session has expired. Please log in again.',
          ErrorCode.UNAUTHORIZED,
          401
        );
      
      case 403:
        // Check if this is a CSRF token error
        const csrfMessage = data.message as string;
        if (csrfMessage && csrfMessage.includes('CSRF')) {
          return new AppError(
            'Security validation failed. Please try again.',
            ErrorCode.CSRF_ERROR,
            403
          );
        }
        return new AppError(
          'You do not have permission to perform this action.',
          ErrorCode.FORBIDDEN,
          403
        );
      
      case 404:
        return new AppError(
          'The requested resource was not found.',
          ErrorCode.NOT_FOUND,
          404
        );
      
      case 422:
        // Extract validation errors if available
        const fieldErrors = data.errors as string[];
        
        if (Array.isArray(fieldErrors) && fieldErrors.length > 0) {
          return new AppError(
            `Validation Error: ${fieldErrors.join(', ')}`,
            ErrorCode.VALIDATION_ERROR,
            422
          );
        }
        
        return new AppError(
          'Validation Error',
          ErrorCode.VALIDATION_ERROR,
          422
        );
      
      case 400:
        // Check if there's a custom message
        const customMessage = data.message as string;
        if (customMessage) {
          return new AppError(
            customMessage,
            ErrorCode.BAD_REQUEST,
            400
          );
        }
        
        return new AppError(
          'Bad request',
          ErrorCode.BAD_REQUEST,
          400
        );
      
      case 429:
        return new AppError(
          'Too many requests. Please try again later.',
          ErrorCode.RATE_LIMIT_ERROR,
          429
        );
      
      default:
        if (status >= 500) {
          return new AppError(
            'An unexpected error occurred. Please try again later.',
            ErrorCode.SERVER_ERROR,
            status
          );
        }
    }
  }

  // For unknown errors
  if (error instanceof Error) {
    return new AppError(
      'An unexpected error occurred. Please try again later.',
      ErrorCode.UNKNOWN_ERROR,
      500
    );
  }

  return new AppError(
    'An unexpected error occurred. Please try again later.',
    ErrorCode.UNKNOWN_ERROR,
    500
  );
};

export const isNetworkError = (error: unknown): boolean => {
  if (error instanceof AxiosError) {
    return !error.response;
  }
  return false;
};

export const isAuthError = (error: unknown): boolean => {
  if (error instanceof AxiosError) {
    return error.response?.status === 401;
  }
  return false;
};

export const isCsrfError = (error: unknown): boolean => {
  if (error instanceof AxiosError && error.response?.status === 403) {
    const data = error.response.data as Record<string, any> || {};
    const message = data.message as string;
    return typeof message === 'string' && message.includes('CSRF');
  }
  return false;
}; 