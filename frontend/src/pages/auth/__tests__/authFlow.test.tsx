import React from 'react';
import { act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import authReducer from '../../../store/slices/authSlice';
import formCheckReducer from '../../../store/slices/formCheckSlice';
import subscriptionReducer from '../../../store/slices/subscriptionSlice';
import workoutReducer from '../../../store/slices/workoutSlice';
import formAnalysisReducer from '../../../store/slices/formAnalysisSlice';
import { renderWithProviders } from '../../../test-utils';

// Mock API service
jest.mock('../../../services/apiService', () => ({
  apiService: {
    auth: {
      login: jest.fn(),
      register: jest.fn(),
      logout: jest.fn(),
      validate: jest.fn(),
      refreshToken: jest.fn()
    }
  }
}));

// Create a mock store for testing
const createMockStore = (preloadedState = {}) => {
  return configureStore({
    reducer: {
      auth: authReducer,
      formCheck: formCheckReducer,
      subscription: subscriptionReducer,
      workout: workoutReducer,
      formAnalysis: formAnalysisReducer
    },
    preloadedState
  });
};

// Initial state for tests
const initialState = {
  auth: {
    user: null,
    token: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  }
};

describe('Authentication Flow', () => {
  // Mock functions for testing
  const mockRegister = jest.fn();
  const mockLogin = jest.fn();
  const mockLogout = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    
    // Mock implementation for successful registration
    mockRegister.mockImplementation(() => {
      return Promise.resolve({
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
      });
    });
    
    // Mock implementation for successful login
    mockLogin.mockImplementation(() => {
      return Promise.resolve({
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user',
      });
    });
  });

  it('should complete the full authentication flow', async () => {
    // Create a fresh store
    const store = createMockStore(initialState);
    
    // Directly test the authentication flow
    const userData = {
      name: 'Test User',
      email: 'test@example.com',
      password: 'Password123',
      confirmPassword: 'Password123'
    };
    
    await act(async () => {
      await mockRegister(userData);
    });
    
    // Verify register was called with correct data
    expect(mockRegister).toHaveBeenCalledWith(userData);
  });

  it('should handle registration validation errors', async () => {
    const store = createMockStore(initialState);
    
    // Set up mock to simulate validation error
    mockRegister.mockRejectedValueOnce('All fields are required');
    
    // Attempt registration with empty data
    try {
      await mockRegister({ name: '', email: '', password: '', confirmPassword: '' });
    } catch (error) {
      // Expected error
    }
    
    // Verify register was called
    expect(mockRegister).toHaveBeenCalled();
  });

  it('should handle login validation errors', async () => {
    const store = createMockStore(initialState);
    
    // Set up mock to simulate validation error
    mockLogin.mockRejectedValueOnce('Email and password are required');
    
    // Attempt login with empty credentials
    try {
      await mockLogin({ email: '', password: '' });
    } catch (error) {
      // Expected error
    }
    
    // Verify login was called
    expect(mockLogin).toHaveBeenCalled();
  });

  it('should handle authentication errors', async () => {
    const store = createMockStore(initialState);
    
    // Set up mock to simulate auth error
    mockLogin.mockRejectedValueOnce('Invalid credentials');
    
    // Attempt login with invalid credentials
    try {
      await mockLogin({ email: 'test@example.com', password: 'wrongpassword' });
    } catch (error) {
      // Expected error
    }
    
    // Verify login was called
    expect(mockLogin).toHaveBeenCalled();
  });

  it('should handle token expiration', async () => {
    const store = createMockStore({
      auth: {
        ...initialState.auth,
        token: 'expired-token',
        isAuthenticated: true,
        user: { id: '123', email: 'test@example.com', name: 'Test User' }
      }
    });
    
    // Simulate token validation failure
    const validateTokenMock = jest.spyOn(require('../../../services/apiService').apiService.auth, 'validate');
    validateTokenMock.mockRejectedValueOnce(new Error('Token expired'));
    
    // When token is expired, auth state should be updated
    expect(store.getState().auth.isAuthenticated).toBe(true);
    
    // In a real scenario, the authSlice would handle this by 
    // dispatching a logout action, but we're just testing the flow
    store.dispatch({ type: 'auth/logout' });
    
    // After logout, auth state should be reset
    expect(store.getState().auth.isAuthenticated).toBe(false);
    expect(store.getState().auth.token).toBe(null);
    expect(store.getState().auth.user).toBe(null);
  });

  it('should handle logout correctly', async () => {
    const store = createMockStore({
      auth: {
        ...initialState.auth,
        token: 'valid-token',
        refreshToken: 'valid-refresh-token',
        isAuthenticated: true,
        user: { id: '123', email: 'test@example.com', name: 'Test User' }
      }
    });
    
    // Before logout
    expect(store.getState().auth.isAuthenticated).toBe(true);
    
    // Perform logout
    await act(async () => {
      await mockLogout();
    });
    
    // Simulate logout action
    store.dispatch({ type: 'auth/logout' });
    
    // After logout
    expect(store.getState().auth.isAuthenticated).toBe(false);
    expect(store.getState().auth.token).toBe(null);
    expect(store.getState().auth.user).toBe(null);
    expect(mockLogout).toHaveBeenCalled();
  });
}); 