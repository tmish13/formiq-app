import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../AuthContext';

const mockUser = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  subscription_tier: 'basic',
  subscription_end_date: new Date(Date.now() + 86400000).toISOString(),
  is_email_verified: true,
};

const server = setupServer(
  rest.get('https://api.formiq-app.com/auth/validate', (req, res, ctx) => {
    return res(ctx.json(mockUser));
  }),
  rest.post('https://api.formiq-app.com/auth/login', (req, res, ctx) => {
    return res(ctx.json({
      access_token: 'mock_token',
      user: mockUser,
    }));
  }),
  rest.post('https://api.formiq-app.com/auth/logout', (req, res, ctx) => {
    return res(ctx.status(200));
  })
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
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
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  );
};

describe('AuthContext', () => {
  it('provides initial loading state', () => {
    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('loads user from token in localStorage', async () => {
    localStorage.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

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

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    act(() => {
      screen.getByRole('button', { name: /login/i }).click();
    });

    await waitFor(() => {
      expect(screen.getByText(`Logged in as ${mockUser.email}`)).toBeInTheDocument();
      expect(localStorage.getItem('token')).toBe('mock_token');
    });
  });

  it('handles login error', async () => {
    server.use(
      rest.post('/api/auth/login', (req, res, ctx) => {
        return res(ctx.status(401));
      })
    );

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });

    act(() => {
      screen.getByRole('button', { name: /login/i }).click();
    });

    await waitFor(() => {
      expect(screen.getByText(/error:/i)).toBeInTheDocument();
    });
  });

  it('handles logout successfully', async () => {
    localStorage.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    });

    act(() => {
      screen.getByRole('button', { name: /logout/i }).click();
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
      expect(localStorage.getItem('token')).toBeNull();
    });
  });

  it('handles expired subscription', async () => {
    const expiredUser = {
      ...mockUser,
      subscription_end_date: new Date(Date.now() - 86400000).toISOString(),
    };

    server.use(
      rest.get('/api/auth/me', (req, res, ctx) => {
        return res(ctx.json(expiredUser));
      })
    );

    localStorage.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(`Logged in as ${expiredUser.email}`)).toBeInTheDocument();
    });
  });

  it('handles network error when fetching user', async () => {
    server.use(
      rest.get('/api/auth/me', (req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    localStorage.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/error:/i)).toBeInTheDocument();
    });
  });

  it('handles invalid token', async () => {
    server.use(
      rest.get('/api/auth/me', (req, res, ctx) => {
        return res(ctx.status(401));
      })
    );

    localStorage.setItem('token', 'mock_token');

    renderWithRouter(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
      expect(localStorage.getItem('token')).toBeNull();
    });
  });
}); 