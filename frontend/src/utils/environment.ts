/**
 * Utilities for environment detection and configuration
 */

/**
 * Check if the current environment is a test environment
 * @returns boolean indicating if code is running in a test environment
 */
export function isTestEnvironment(): boolean {
  return process.env.NODE_ENV === 'test' || 
         process.env.JEST_WORKER_ID !== undefined ||
         !!process.env.TEST_ENV;
}

/**
 * Check if the current environment is a development environment
 * @returns boolean indicating if code is running in development
 */
export function isDevelopmentEnvironment(): boolean {
  return process.env.NODE_ENV === 'development';
}

/**
 * Check if the current environment is a production environment
 * @returns boolean indicating if code is running in production
 */
export function isProductionEnvironment(): boolean {
  return process.env.NODE_ENV === 'production';
}

/**
 * Get the current environment name
 * @returns string representing the current environment
 */
export function getEnvironment(): string {
  if (isTestEnvironment()) return 'test';
  if (isDevelopmentEnvironment()) return 'development';
  if (isProductionEnvironment()) return 'production';
  return 'unknown';
}

/**
 * Check if the code is running in a browser environment
 * @returns boolean indicating if code is running in a browser
 */
export function isBrowserEnvironment(): boolean {
  return typeof window !== 'undefined' && typeof document !== 'undefined';
}

/**
 * Check if the code is running in a Node.js environment
 * @returns boolean indicating if code is running in Node.js
 */
export function isNodeEnvironment(): boolean {
  return typeof process !== 'undefined' && 
         !!process.versions &&
         !!process.versions.node;
}

/**
 * Get the application version from environment variables
 * @returns string representing the application version or 'unknown'
 */
export function getAppVersion(): string {
  return process.env.REACT_APP_VERSION || 'unknown';
} 