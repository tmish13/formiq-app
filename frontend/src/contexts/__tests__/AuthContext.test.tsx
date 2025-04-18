import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { AuthProvider, useAuth } from '../AuthContext';
import { MemoryRouter } from 'react-router-dom';

// Import to enable mocking navigate and location
import * as router from 'react-router-dom';

// Mock useNavigate and useLocation
const mockNavigate = jest.fn();
jest.spyOn(router, 'useNavigate').mockImplementation(() => mockNavigate);
jest.spyOn(router, 'useLocation').mockImplementation(() => ({ 
  pathname: '/test', 
  search: '', 
  hash: '', 
  state: null,
  key: 'default'
}));

const mockUser = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  subscription_tier: 'basic',
  subscription_end_date: new Date(Date.now() + 86400000).toISOString(),
  is_email_verified: true,
};

// Make sure server handlers use the correct API paths that match the actual implementation
const server = setupServer(
  rest.get('/api/auth/me', (req, res, ctx) => {
    return res(ctx.json(mockUser));
  }),
  rest.get('/api/auth/validate', (req, res, ctx) => {
    return res(ctx.json(mockUser));
  }),
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(ctx.json({
      token: 'mock_token',
      user: mockUser,
    }));
  }),
  rest.post('/api/auth/logout', (req, res, ctx) => {
    return res(ctx.status(200));
  })
);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
  mockNavigate.mockClear();
});
afterAll(() => server.close());

// Test component that uses the auth context
const TestComponent = () => {
  const { user, isLoading, error, login, logout } = useAuth();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!user) return <button onClick={() => login('test@example.com', 'password')}>Login</button>;

  return (
    <div>
      <div>Logged in as {user.email}</div>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <MemoryRouter>
      {ui}
    </MemoryRouter>
  );
};

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: jest.fn((key: string) => store[key] || null),
    setItem: jest.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: jest.fn((key: string) => {
      delete store[key];
    }),
    clear: jest.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('AuthContext', () => {
  beforeEach(() => {
    // Clear localStorage mock data
    localStorageMock.clear();
  });

  it('provides initial loading state', async () => {
    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // We need to wait for the loading state to be shown first
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    // Then wait for it to change to login button (since there's no token)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });
  });

  it('loads user from token in localStorage', async () => {
    // Set the token in localStorage
    localStorageMock.setItem('token', 'mock_token');
    
    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // First verify loading state
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    
    // Then wait for user to be loaded
    await waitFor(() => {
      expect(screen.getByText(`Logged in as ${mockUser.email}`)).toBeInTheDocument();
    });
  });

  it('handles login successfully', async () => {
    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // First verify loading state is gone and login button is shown
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    // Click login
    act(() => {
      screen.getByRole('button', { name: /login/i }).click();
    });

    // Wait for login to complete and verify user is logged in
    await waitFor(() => {
      expect(screen.getByText(`Logged in as ${mockUser.email}`)).toBeInTheDocument();
      expect(localStorageMock.setItem).toHaveBeenCalledWith('token', 'mock_token');
    });
  });

  it('handles login error', async () => {
    // Setup error response
    server.use(
      rest.post('/api/auth/login', (req, res, ctx) => {
        return res(ctx.status(401), ctx.json({ message: 'Invalid credentials' }));
      })
    );

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Wait for login button to appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    // Click login
    act(() => {
      screen.getByRole('button', { name: /login/i }).click();
    });

    // Verify error is displayed
    await waitFor(() => {
      expect(screen.getByText(/error:/i)).toBeInTheDocument();
    });
  });

  it('handles logout successfully', async () => {
    // Set the token in localStorage and mock the user being logged in
    localStorageMock.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Wait for logout button to appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    });

    // Click logout
    act(() => {
      screen.getByRole('button', { name: /logout/i }).click();
    });

    // Verify user is logged out and token is removed
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('token');
    });
  });

  it('handles expired subscription', async () => {
    const expiredUser = {
      ...mockUser,
      subscription_end_date: new Date(Date.now() - 86400000).toISOString(),
    };

    // Mock response with expired subscription
    server.use(
      rest.get('/api/auth/me', (req, res, ctx) => {
        return res(ctx.json(expiredUser));
      })
    );

    localStorageMock.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Verify the expired user is still shown as logged in
    await waitFor(() => {
      expect(screen.getByText(`Logged in as ${expiredUser.email}`)).toBeInTheDocument();
    });
  });

  it('handles network error when fetching user', async () => {
    // Mock server error
    server.use(
      rest.get('/api/auth/me', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ message: 'Server error' }));
      })
    );

    localStorageMock.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Verify error is displayed
    await waitFor(() => {
      expect(screen.getByText(/error:/i)).toBeInTheDocument();
    });
  });

  it('handles invalid token', async () => {
    // Mock unauthorized response
    server.use(
      rest.get('/api/auth/me', (req, res, ctx) => {
        return res(ctx.status(401), ctx.json({ message: 'Invalid token' }));
      })
    );

    localStorageMock.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    // Verify user is logged out after invalid token
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('token');
    });
  });
}); 