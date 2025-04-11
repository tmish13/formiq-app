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
  API_ERROR = 'API_ERROR'
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
  constructor(
    message: string,
    public code: ErrorCode | string = ErrorCode.UNKNOWN_ERROR,
    public status: number = 500,
    public details?: Record<string, any>,
    public fieldErrors?: Record<string, string[]>,
    public retry: boolean = false
  ) {
    super(message);
    this.name = 'AppError';
  }
}

export const handleApiError = (error: unknown): ApiError => {
  if (error instanceof AppError) {
    return {
      message: error.message,
      code: error.code,
      status: error.status,
      details: error.details,
      fieldErrors: error.fieldErrors,
      retry: error.retry
    };
  }

  if (error instanceof AxiosError) {
    const status = error.response?.status || 0;
    let code = error.response?.data?.code || ErrorCode.API_ERROR;
    let retry = false;

    // Determine error type based on status code
    if (!error.response) {
      code = ErrorCode.NETWORK_ERROR;
      retry = true;
    } else if (status === 401) {
      code = ErrorCode.AUTHENTICATION_ERROR;
    } else if (status === 403) {
      code = ErrorCode.AUTHORIZATION_ERROR;
      // Check if this is a CSRF token error
      if (error.response.data?.message?.includes('CSRF')) {
        code = ErrorCode.CSRF_ERROR;
        retry = true;
      }
    } else if (status === 422 || status === 400) {
      code = ErrorCode.VALIDATION_ERROR;
    } else if (status === 429) {
      code = ErrorCode.RATE_LIMIT_ERROR;
      retry = true;
    } else if (status >= 500) {
      code = ErrorCode.SERVER_ERROR;
      retry = true;
    } else if (error.code === 'ECONNABORTED') {
      code = ErrorCode.TIMEOUT_ERROR;
      retry = true;
    }

    // Extract field validation errors if available
    const fieldErrors = error.response?.data?.details?.errors || 
                      error.response?.data?.errors ||
                      undefined;

    return {
      message: error.response?.data?.message || error.message || 'An error occurred',
      code,
      status,
      details: error.response?.data,
      fieldErrors,
      retry
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
      code: ErrorCode.UNKNOWN_ERROR,
      status: 500,
    };
  }

  return {
    message: 'An unexpected error occurred',
    code: ErrorCode.UNKNOWN_ERROR,
    status: 500,
  };
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
    return error.response.data?.message?.includes('CSRF') || false;
  }
  return false;
}; 