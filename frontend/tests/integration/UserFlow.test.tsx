import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { App } from '../../src/App';
import { render } from '../../src/test-utils';

const server = setupServer(
  // Mock API endpoints
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
  rest.post('/api/form-checks/analyze', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '456',
        exercise: 'squat',
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
          exercise: 'squat',
          feedback: ['Good depth', 'Keep chest up'],
          score: 85,
          createdAt: new Date().toISOString()
        }
      ])
    );
  }),
  rest.get('/api/users/me', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: '123',
        email: 'test@example.com',
        name: 'Test User'
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('User Flow Integration Tests', () => {
  test('Complete flow: Registration to Analysis Result', async () => {
    render(<App />);

    // 1. Navigate to registration
    const registerLink = screen.getByText(/register/i);
    fireEvent.click(registerLink);

    // 2. Fill registration form
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Password123!');
    await userEvent.type(screen.getByLabelText(/full name/i), 'Test User');

    // 3. Submit registration
    const submitButton = screen.getByRole('button', { name: /register/i });
    fireEvent.click(submitButton);

    // 4. Verify successful registration and redirect
    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });

    // 5. Navigate to form check
    const formCheckLink = screen.getByText(/form check/i);
    fireEvent.click(formCheckLink);

    // 6. Upload video and submit for analysis
    const fileInput = screen.getByLabelText(/upload video/i);
    const file = new File(['dummy content'], 'workout.mp4', { type: 'video/mp4' });
    await userEvent.upload(fileInput, file);

    const analyzeButton = screen.getByRole('button', { name: /analyze/i });
    fireEvent.click(analyzeButton);

    // 7. Verify analysis results
    await waitFor(() => {
      expect(screen.getByText(/good depth/i)).toBeInTheDocument();
      expect(screen.getByText(/keep chest up/i)).toBeInTheDocument();
      expect(screen.getByText(/85/)).toBeInTheDocument();
    });
  });

  test('Registration validation and error handling', async () => {
    render(<App />);
    
    // Navigate to registration
    const registerLink = screen.getByText(/register/i);
    fireEvent.click(registerLink);

    // Test invalid email
    await userEvent.type(screen.getByLabelText(/email/i), 'invalid-email');
    const submitButton = screen.getByRole('button', { name: /register/i });
    fireEvent.click(submitButton);
    expect(await screen.findByText(/invalid email format/i)).toBeInTheDocument();

    // Test password mismatch
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'DifferentPass123!');
    fireEvent.click(submitButton);
    expect(await screen.findByText(/passwords do not match/i)).toBeInTheDocument();
  });

  test('Form check analysis error handling', async () => {
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
    
    // Login and navigate to form check
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    const formCheckLink = screen.getByText(/form check/i);
    fireEvent.click(formCheckLink);

    // Upload invalid file
    const fileInput = screen.getByLabelText(/upload video/i);
    const file = new File(['invalid'], 'invalid.txt', { type: 'text/plain' });
    await userEvent.upload(fileInput, file);

    const analyzeButton = screen.getByRole('button', { name: /analyze/i });
    fireEvent.click(analyzeButton);

    // Verify error message
    await waitFor(() => {
      expect(screen.getByText(/invalid video format/i)).toBeInTheDocument();
    });
  });

  test('View exercise history and details', async () => {
    render(<App />);

    // Login
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'Password123!');
    fireEvent.click(screen.getByRole('button', { name: /login/i }));

    // Navigate to history
    const historyLink = screen.getByText(/history/i);
    fireEvent.click(historyLink);

    // Verify history items
    await waitFor(() => {
      expect(screen.getByText(/squat/i)).toBeInTheDocument();
      expect(screen.getByText(/85/)).toBeInTheDocument();
    });

    // View details
    const viewDetailsButton = screen.getByRole('button', { name: /view details/i });
    fireEvent.click(viewDetailsButton);

    // Verify details view
    await waitFor(() => {
      expect(screen.getByText(/good depth/i)).toBeInTheDocument();
      expect(screen.getByText(/keep chest up/i)).toBeInTheDocument();
    });
  });
}); 