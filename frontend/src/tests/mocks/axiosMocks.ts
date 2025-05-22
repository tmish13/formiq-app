import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';

// Function to create a properly typed axios error
export const createAxiosError = <T = any>(
  status: number,
  statusText: string = '',
  data: any = {},
  message: string = '',
  config: Partial<AxiosRequestConfig> = {}
): AxiosError<T> => {
  // Create a partial response object
  const response: Partial<AxiosResponse<T>> = {
    status,
    statusText,
    data: data as T,
    headers: {},
    config: {
      url: 'https://api.example.com/test',
      method: 'GET',
      headers: {} as any,
      ...config
    }
  };

  // Create the Error object first
  const error = new Error(message || `Request failed with status code ${status}`) as AxiosError<T>;
  
  // Add Axios specific properties
  error.isAxiosError = true;
  error.response = response as AxiosResponse<T>;
  error.config = response.config;
  error.toJSON = () => ({});
  
  return error;
};

// Create specific error types
export const createNetworkError = (): AxiosError => {
  const error = new Error('Network Error') as AxiosError;
  error.isAxiosError = true;
  error.config = {
    url: 'https://api.example.com/test',
    method: 'GET',
    headers: {} as any
  };
  error.message = 'Network Error';
  error.toJSON = () => ({});
  return error;
};

export const createTimeoutError = (): AxiosError => {
  const error = new Error('Timeout Error') as AxiosError;
  error.isAxiosError = true;
  error.code = 'ECONNABORTED';
  error.config = {
    url: 'https://api.example.com/test',
    method: 'GET',
    headers: {} as any,
    timeout: 3000
  };
  error.message = 'timeout of 3000ms exceeded';
  error.toJSON = () => ({});
  return error;
};

export const createUnauthorizedError = (): AxiosError => {
  return createAxiosError(
    401,
    'Unauthorized',
    { message: 'Authentication required' },
    'Request failed with status code 401'
  );
};

export const createForbiddenError = (): AxiosError => {
  return createAxiosError(
    403,
    'Forbidden',
    { message: 'Access denied' },
    'Request failed with status code 403'
  );
};

export const createNotFoundError = (): AxiosError => {
  return createAxiosError(
    404,
    'Not Found',
    { message: 'Resource not found' },
    'Request failed with status code 404'
  );
};

export const createCsrfError = (): AxiosError => {
  return createAxiosError(
    419,
    'CSRF Token Mismatch',
    { message: 'CSRF token mismatch' },
    'Request failed with status code 419'
  );
};

export const createValidationError = (errors?: Record<string, string[]>): AxiosError => {
  return createAxiosError(
    422,
    'Unprocessable Entity',
    { 
      message: 'The given data was invalid.',
      errors: errors || {
        field1: ['Field 1 is required'],
        field2: ['Field 2 must be a valid email']
      }
    },
    'Request failed with status code 422'
  );
};

export const createServerError = (): AxiosError => {
  return createAxiosError(
    500,
    'Internal Server Error',
    { message: 'Server error' },
    'Request failed with status code 500'
  );
}; 