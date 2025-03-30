import React from 'react';
import { screen, render } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import ProtectedRoute from '../ProtectedRoute';
import authReducer from '../../store/slices/authSlice';
import { User, SubscriptionTier } from '../../types';

const mockUser: User = {
  id: 'user_1',
  email: 'test@example.com',
  name: 'Test User',
  role: 'user',
  subscription_tier: 'basic' as SubscriptionTier,
  subscription_end_date: '2024-04-01T00:00:00Z',
  created_at: '2024-03-01T00:00:00Z',
  updated_at: '2024-03-01T00:00:00Z',
};

const TestComponent = () => <div>Protected Content</div>;

const createTestStore = (initialState: any) => {
  return configureStore({
    reducer: {
      auth: authReducer,
    },
    preloadedState: initialState,
  });
};

describe('ProtectedRoute', () => {
  it('should show loading state when authentication is in progress', () => {
    const store = createTestStore({
      auth: {
        isLoading: true,
        isAuthenticated: false,
        user: null,
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should show error message when authentication fails', () => {
    const store = createTestStore({
      auth: {
        isLoading: false,
        isAuthenticated: false,
        user: null,
        error: 'Authentication failed',
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Authentication failed')).toBeInTheDocument();
  });

  it('should redirect to login page when user is not authenticated', () => {
    const store = createTestStore({
      auth: {
        isLoading: false,
        isAuthenticated: false,
        user: null,
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Login Page')).toBeInTheDocument();
  });

  it('should render protected content when user is authenticated', () => {
    const store = createTestStore({
      auth: {
        isLoading: false,
        isAuthenticated: true,
        user: mockUser,
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('should redirect to subscription page when required subscription tier is not met', () => {
    const store = createTestStore({
      auth: {
        isLoading: false,
        isAuthenticated: true,
        user: {
          ...mockUser,
          subscription_tier: 'free' as SubscriptionTier,
        },
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute requiredSubscription="basic">
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Subscription Page')).toBeInTheDocument();
  });

  it('should redirect to subscription page when subscription has expired', () => {
    const store = createTestStore({
      auth: {
        isLoading: false,
        isAuthenticated: true,
        user: {
          ...mockUser,
          subscription_end_date: '2024-03-01T00:00:00Z', // Past date
        },
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute>
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Subscription Page')).toBeInTheDocument();
  });

  it('should allow access when user has required subscription tier', () => {
    const store = createTestStore({
      auth: {
        isLoading: false,
        isAuthenticated: true,
        user: {
          ...mockUser,
          subscription_tier: 'pro' as SubscriptionTier,
        },
      },
    });

    render(
      <Provider store={store}>
        <BrowserRouter>
          <ProtectedRoute requiredSubscription="basic">
            <TestComponent />
          </ProtectedRoute>
        </BrowserRouter>
      </Provider>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });
}); 