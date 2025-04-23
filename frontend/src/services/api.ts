import axios from 'axios';
import { logError } from '../utils/errorLogging';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    logError('API Request Error', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    logError('API Response Error', error);
    
    // Handle token expiration
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      // You might want to redirect to login page
    }
    
    return Promise.reject(error);
  }
);

// Export the API instance for use in services
export const apiService = api;

export default api; 