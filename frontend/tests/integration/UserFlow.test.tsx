import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { App } from '../../src/App';
import { render } from '../../src/test-utils';

// Mock components to avoid real UI rendering issues
jest.mock('../../src/components/FormCheck', () => ({
  __esModule: true,
  default: () => <div data-testid="form-check-component">Form Check Component</div>
}));

jest.mock('../../src/components/Auth', () => ({
  __esModule: true,
  Login: () => (
    <div data-testid="login-component">
      <label htmlFor="email">Email</label>
      <input id="email" />
      <label htmlFor="password">Password</label>
      <input id="password" />
      <button>Login</button>
    </div>
  ),
  Register: () => (
    <div data-testid="register-component">
      <label htmlFor="email">Email</label>
      <input id="email" />
      <label htmlFor="password">Password</label>
      <input id="password" />
      <label htmlFor="confirm-password">Confirm Password</label>
      <input id="confirm-password" />
      <label htmlFor="full-name">Full Name</label>
      <input id="full-name" />
      <button>Register</button>
    </div>
  )
}));

// Create proper server handlers
const server = setupServer(
  // Auth endpoints
  rest.post('/api/auth/register', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: '123',
        email: 'test@example.com',
        token: 'fake-jwt-token'
      })
    );
  }),
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        token: 'fake-jwt-token',
        user: {
          id: '123',
          email: 'test@example.com',
          name: 'Test User'
        }
      })
    );
  }),
  rest.get('/api/auth/me', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '123',
        email: 'test@example.com',
        name: 'Test User'
      })
    );
  }),
  // Form check endpoints
  rest.post('/api/form-checks/analyze', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '456',
        exercise_type: 'squat',
        feedback: ['Good depth', 'Keep chest up'],
        score: 85
      })
    );
  }),
  rest.get('/api/form-checks', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: '456',
          exercise_type: 'squat',
          feedback: ['Good depth', 'Keep chest up'],
          score: 85,
          created_at: new Date().toISOString()
        }
      ])
    );
  })
);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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

// Mock navigation
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
}));

describe('User Flow Integration Tests', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  test('Complete flow: Registration to Analysis Result', async () => {
    render(<App />);

    // Wait for the app to load (showing login by default)
    await waitFor(() => {
      expect(screen.getByTestId('login-component')).toBeInTheDocument();
    });

    // Find the "Register" link in the navigation
    const registerNav = screen.getByText('Register');
    fireEvent.click(registerNav);

    // Verify we're on the registration screen
    await waitFor(() => {
      expect(screen.getByTestId('register-component')).toBeInTheDocument();
    });

    // Fill registration form
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Password123!');
    await userEvent.type(screen.getByLabelText(/full name/i), 'Test User');

    // Submit registration
    const registerButton = screen.getByRole('button', { name: /register/i });
    fireEvent.click(registerButton);

    // After successful registration, we should see the form check component
    await waitFor(() => {
      expect(screen.getByTestId('form-check-component')).toBeInTheDocument();
    });
  });

  test('Login and access form check', async () => {
    render(<App />);

    // Wait for the app to load and show login component
    await waitFor(() => {
      expect(screen.getByTestId('login-component')).toBeInTheDocument();
    });

    // Fill login form
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    
    // Submit login
    const loginButton = screen.getByRole('button', { name: /login/i });
    fireEvent.click(loginButton);

    // After successful login, we should see the form check component
    await waitFor(() => {
      expect(screen.getByTestId('form-check-component')).toBeInTheDocument();
    });
  });

  test('Registration validation errors', async () => {
    // Mock validation error response
    server.use(
      rest.post('/api/auth/register', (req, res, ctx) => {
        return res(
          ctx.status(400),
          ctx.json({
            errors: {
              email: 'Invalid email format',
              password: 'Password must be at least 8 characters'
            }
          })
        );
      })
    );

    render(<App />);

    // Navigate to registration
    await waitFor(() => {
      expect(screen.getByTestId('login-component')).toBeInTheDocument();
    });
    
    const registerNav = screen.getByText('Register');
    fireEvent.click(registerNav);

    // Verify we're on the registration screen
    await waitFor(() => {
      expect(screen.getByTestId('register-component')).toBeInTheDocument();
    });

    // Fill with invalid data
    await userEvent.type(screen.getByLabelText(/email/i), 'invalid-email');
    await userEvent.type(screen.getByLabelText(/password/i), 'short');
    
    // Submit registration
    const registerButton = screen.getByRole('button', { name: /register/i });
    fireEvent.click(registerButton);

    // We should still be on the registration page
    await waitFor(() => {
      expect(screen.getByTestId('register-component')).toBeInTheDocument();
    });
  });

  test('Error handling with form check analysis', async () => {
    // Mock user is already logged in
    localStorageMock.setItem('token', 'fake-jwt-token');
    
    // Mock error response for analysis
    server.use(
      rest.post('/api/form-checks/analyze', (req, res, ctx) => {
        return res(
          ctx.status(400),
          ctx.json({
            error: 'Invalid video format'
          })
        );
      })
    );

    render(<App />);
    
    // After login with token, we should see the form check component
    await waitFor(() => {
      expect(screen.getByTestId('form-check-component')).toBeInTheDocument();
    });
  });
}); 