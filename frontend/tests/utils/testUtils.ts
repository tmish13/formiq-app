import { configureStore } from '@reduxjs/toolkit';
import { FormCheck, FormCheckStatus, ExerciseType } from '../../src/types';
import formCheckReducer from '../../src/store/slices/formCheckSlice';
import authReducer from '../../src/store/slices/authSlice';
import uiReducer from '../../src/store/slices/uiSlice';
import { AxiosError, AxiosHeaders, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

// Define FormCheckFeedback interface locally since it might not be exported
interface FormCheckFeedback {
  type: string;
  message: string;
  timestamp: string;
}

/**
 * Creates a mock API service with jest mock functions for all HTTP methods
 */
export function createMockApiService() {
  return {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    patch: jest.fn(),
  };
}

/**
 * Creates a configureStore instance with optional preloaded state
 */
export function createTestStore(preloadedState = {}) {
  return configureStore({
    reducer: {
      formCheck: formCheckReducer,
      auth: authReducer,
      ui: uiReducer,
    },
    preloadedState,
  });
}

/**
 * Creates a mock FormCheck object with default values that can be overridden
 */
export function createMockFormCheck(overrides = {}): FormCheck {
  return {
    id: 1,
    user_id: 1,
    exercise_type: 'squat' as ExerciseType,
    video_url: 'https://example.com/video.mp4',
    status: 'pending' as FormCheckStatus,
    created_at: '2025-04-15T19:10:15.715Z',
    updated_at: '2025-04-15T19:10:15.716Z',
    ...overrides
  };
}

/**
 * Creates an array of mock FormCheck objects
 */
export function createMockFormChecks(count = 2, overridesFn?: (index: number) => Partial<FormCheck>): FormCheck[] {
  return Array.from({ length: count }, (_, i) => {
    const defaults = {
      id: i + 1,
      exercise_type: i % 2 === 0 ? 'squat' : 'deadlift' as ExerciseType,
    };
    const overrides = overridesFn ? overridesFn(i) : {};
    return createMockFormCheck({ ...defaults, ...overrides });
  });
}

/**
 * Creates a mock FormCheckFeedback item
 */
export function createMockFeedbackItem(overrides = {}): FormCheckFeedback {
  return {
    type: 'success',
    message: 'Good form overall',
    timestamp: '2024-03-20T10:00:00Z',
    ...overrides
  };
}

/**
 * Generate default axios config for error mocking
 */
function createDefaultConfig(): InternalAxiosRequestConfig {
  return {
    headers: new AxiosHeaders(),
    url: 'https://api.example.com/test',
    method: 'get',
    baseURL: 'https://api.example.com',
    transformRequest: [],
    transformResponse: [],
    timeout: 0,
    xsrfCookieName: 'XSRF-TOKEN',
    xsrfHeaderName: 'X-XSRF-TOKEN',
    maxContentLength: -1,
    maxBodyLength: -1,
    env: {
      FormData: window.FormData
    }
  };
}

/**
 * Types of error scenarios for the createAxiosError factory
 */
export type ErrorType = 'network' | 'timeout' | 'response' | 'csrf' | 'auth' | 'validation' | 'server';

/**
 * Creates a properly typed Axios error for testing
 * @param options Configuration for the error
 * @returns A typed AxiosError instance
 */
export function createAxiosError<T = any, D = any>(
  options: {
    status?: number;
    data?: D;
    message?: string;
    code?: string;
    errorType?: ErrorType;
  } = {}
): AxiosError<T> {
  const {
    status = 500,
    data = {},
    message = `Request failed with status code ${status}`,
    code = '',
    errorType = 'response'
  } = options;

  // Create a base error
  const error = new AxiosError<T>(
    message,
    code || (errorType === 'timeout' ? 'ECONNABORTED' : 'ERR_BAD_RESPONSE'),
    createDefaultConfig(),
    {} // request
  );

  // Set isAxiosError flag
  error.isAxiosError = true;

  // Configure specific error types
  switch (errorType) {
    case 'network':
      // Network errors don't have a response
      error.message = 'Network Error';
      error.response = undefined;
      break;

    case 'timeout':
      error.message = 'timeout of 10000ms exceeded';
      error.code = 'ECONNABORTED';
      error.response = undefined;
      break;

    case 'csrf':
      // CSRF errors are 403 with specific message
      const csrfData = { message: 'CSRF token validation failed', ...(data as Object) };
      error.response = {
        status: 403,
        statusText: 'Forbidden',
        headers: {},
        config: createDefaultConfig(),
        data: csrfData as T
      } as AxiosResponse;
      break;

    case 'auth':
      // Auth errors are 401
      error.response = {
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config: createDefaultConfig(),
        data: { message: 'Unauthorized', ...(data as Object) } as T
      } as AxiosResponse;
      break;

    case 'validation':
      // Validation errors are 422
      error.response = {
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: {},
        config: createDefaultConfig(),
        data: data as T
      } as AxiosResponse;
      break;

    case 'server':
      // Server errors are 500+
      error.response = {
        status: status,
        statusText: 'Internal Server Error',
        headers: {},
        config: createDefaultConfig(),
        data: { message: 'Internal Server Error', ...(data as Object) } as T
      } as AxiosResponse;
      break;

    case 'response':
    default:
      // Standard response error
      error.response = {
        status: status,
        statusText: status === 404 ? 'Not Found' : status === 400 ? 'Bad Request' : 'Error',
        headers: {},
        config: createDefaultConfig(),
        data: data as T
      } as AxiosResponse;
      break;
  }

  return error;
}

/**
 * Creates a file object for testing file uploads
 */
export function createMockFile(name = 'test-video.mp4', type = 'video/mp4', size = 1024): File {
  const file = new File(['mock file content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
} 