/**
 * Application-wide constants
 */

// API base URL - use environment variable in production
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

// Authentication constants
export const AUTH_TOKEN_KEY = 'access_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';
export const AUTH_EXPIRY_KEY = 'token_expiry';

// Session constants
export const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds
export const USER_INACTIVE_TIMEOUT = 15 * 60 * 1000; // 15 minutes in milliseconds

// Pagination defaults
export const DEFAULT_PAGE_SIZE = 10;
export const DEFAULT_PAGE = 1; 