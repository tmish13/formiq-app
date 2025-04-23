/**
 * Error logging utility to centralize and control error logging in the application.
 * In production, this can be configured to send errors to monitoring services,
 * while in development it can provide more verbose output.
 */

// Import error monitoring service (if used in production)
// import * as Sentry from '@sentry/react';

/**
 * Environment-aware error logger
 * @param message A descriptive message about the error
 * @param error The actual error object
 * @param metadata Optional additional data to help with debugging
 */
export function logError(message: string, error: any, metadata?: Record<string, any>): void {
  const isProduction = process.env.NODE_ENV === 'production';
  
  // In production, we could send to monitoring service and suppress console
  if (isProduction) {
    // Send to monitoring service like Sentry
    // Sentry.captureException(error, {
    //   extra: {
    //     message,
    //     ...metadata,
    //   },
    // });
    
    // Optional: minimal logging in production
    // To completely disable console logs in production, just remove this line
    // This leaves the function in place so code doesn't break, but prevents logs
    // from appearing in production
  } else {
    // In development, we can be more verbose
    if (metadata) {
      console.error(`[ERROR] ${message}:`, error, 'Additional data:', metadata);
    } else {
      console.error(`[ERROR] ${message}:`, error);
    }
  }
}

/**
 * Create a standardized error object with metadata
 * @param message The error message
 * @param code Optional error code
 * @param metadata Additional data about the error
 */
export function createErrorObject(
  message: string,
  code?: string,
  metadata?: Record<string, any>
): Error & { code?: string; metadata?: Record<string, any> } {
  const error = new Error(message) as Error & { code?: string; metadata?: Record<string, any> };
  
  if (code) {
    error.code = code;
  }
  
  if (metadata) {
    error.metadata = metadata;
  }
  
  return error;
}

/**
 * Log network errors with specific handling
 * @param endpoint The API endpoint that failed
 * @param error The error returned
 */
export function logNetworkError(endpoint: string, error: any): void {
  const status = error?.response?.status;
  const data = error?.response?.data;
  
  logError(`API Error (${endpoint})`, error, {
    status,
    endpoint,
    responseData: data,
  });
}

/**
 * Log JavaScript errors with source information
 * @param error The error object
 * @param source Where the error occurred
 */
export function logJsError(error: Error, source: string): void {
  logError(`JavaScript Error in ${source}`, error, {
    stack: error.stack,
    source,
  });
} 