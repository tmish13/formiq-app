import React from 'react';
import { render, screen } from '@testing-library/react';
import { ProtectedRoute } from '../ProtectedRoute';
import { MemoryRouter } from 'react-router-dom';

// Mock the Navigate component from react-router-dom
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  Navigate: () => <div data-testid="navigate">Redirected to login</div>,
  useLocation: () => ({ pathname: '/test', search: '', hash: '', state: null, key: 'test' }),
}));

// Mock the LoadingSpinner component
jest.mock('../atoms/LoadingSpinner', () => ({
  __esModule: true,
  default: () => <div role="status" data-testid="loading-spinner">Loading...</div>,
}));

// Mock the useAuth hook
jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('ProtectedRoute Component', () => {
  const TestComponent = () => <div data-testid="protected-content">Protected Content</div>;
  
  // Import the mocked hook inside describe to avoid hoisting issues
  const { useAuth } = require('../../hooks/useAuth');
  
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  test('shows loading state when authentication is in progress', () => {
    // Set up the mock implementation for loading state
    useAuth.mockReturnValue({
      isLoading: true,
      isAuthenticated: false,
      user: null
    });
    
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    );
    
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.queryByTestId('navigate')).not.toBeInTheDocument();
  });
  
  test('redirects to login when user is not authenticated', () => {
    // Set up the mock implementation for unauthenticated state
    useAuth.mockReturnValue({
      isLoading: false,
      isAuthenticated: false,
      user: null
    });
    
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    );
    
    expect(screen.getByTestId('navigate')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });
  
  test('renders protected content when user is authenticated', () => {
    // Set up the mock implementation for authenticated state
    useAuth.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      user: { id: '1', name: 'Test User', email: 'test@example.com', role: 'user' }
    });
    
    render(
      <MemoryRouter>
        <ProtectedRoute>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    );
    
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
    expect(screen.queryByTestId('navigate')).not.toBeInTheDocument();
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });
  
  test('redirects when user does not have required role', () => {
    // Set up the mock implementation for authenticated state with incorrect role
    useAuth.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      user: { id: '1', name: 'Test User', email: 'test@example.com', role: 'user' }
    });
    
    render(
      <MemoryRouter>
        <ProtectedRoute requiredRoles={['admin']}>
          <TestComponent />
        </ProtectedRoute>
      </MemoryRouter>
    );
    
    expect(screen.getByTestId('navigate')).toBeInTheDocument();
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });
}); 