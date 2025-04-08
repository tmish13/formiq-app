import axios from 'axios';
import { ApiError } from '../types';
import { Capacitor } from '@capacitor/core';

// Get the base URL for the API depending on environment
const getBaseUrl = () => {
  // In native mobile platforms
  if (Capacitor.isNativePlatform()) {
    if (Capacitor.getPlatform() === 'android') {
      return 'http://10.0.2.2:8000/api/v1';
    }
    if (Capacitor.getPlatform() === 'ios') {
      return 'http://localhost:8000/api/v1';
    }
  }
  
  // In web browser
  return process.env.REACT_APP_API_URL ? 
    `${process.env.REACT_APP_API_URL}/api/v1` : 
    'http://localhost:8000/api/v1';
};

const api = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000, // Increase timeout for slower connections
});

// Add request interceptor to include auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  return config;
});

// Add response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    console.log(`API Response (${response.status}):`, response.data);
    return response;
  },
  (error: ApiError) => {
    console.error('API Error:', error);
    
    // Network error handling
    if (!error.response) {
      console.log('Network error detected');
      // You could dispatch to a global error state here
    } else {
      console.log(`API Error (${error.response.status}):`, error.response.data);
    }
    
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const endpoints = {
  auth: {
    login: '/auth/login',
    register: '/auth/register',
    refreshToken: '/auth/refresh',
    logout: '/auth/logout',
  },
  user: {
    profile: '/users/me',
    update: '/users/me',
    subscription: '/users/subscription',
  },
  workouts: {
    list: '/workouts',
    detail: (id: string) => `/workouts/${id}`,
    create: '/workouts',
    update: (id: string) => `/workouts/${id}`,
    delete: (id: string) => `/workouts/${id}`,
  },
  formChecks: {
    upload: '/form-checks',
    detail: (id: string) => `/form-checks/${id}`,
    list: '/form-checks',
    delete: (id: string) => `/form-checks/${id}`,
    complete: (id: string) => `/form-checks/${id}/complete`,
    feedback: (id: string) => `/form-checks/${id}/feedback`,
  },
} as const;

export default api; 