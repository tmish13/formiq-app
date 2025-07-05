/**
 * Test setup for API integration tests
 */

import axios from 'axios';

// Create a test-specific axios instance without interceptors
export const testApi = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 5000,
});

// Simple endpoints object
export const testEndpoints = {
  auth: {
    login: '/auth/login',
    refreshToken: '/auth/refresh',
    logout: '/auth/logout',
  },
  formChecks: {
    history: '/form-checks/history',
    upload: '/form-checks',
    detail: (id: string) => `/form-checks/${id}`,
  },
};

export default testApi;