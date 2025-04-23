import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter as Router } from 'react-router-dom';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { ThemeProvider } from 'styled-components';
import { LoginPage } from '../../src/pages/auth/LoginPage';
import { FormUploadPage } from '../../src/pages/upload/FormUploadPage';
import { FeedbackPage } from '../../src/pages/feedback/FeedbackPage';
import { AuthProvider } from '../../src/contexts/AuthContext';
import { mockThemeWithFallbacks as mockTheme } from '../__mocks__/mockTheme';
import userEvent from '@testing-library/user-event';

// Mock server setup
const server = setupServer(
  // Mock login endpoint
  rest.post('/api/auth/login', (req, res, ctx) => {
    return res(
      ctx.json({
        token: 'mock-token-123',
        user: {
          id: 'user-123',
          name: 'Test User',
          email: 'test@example.com',
        },
      })
    );
  }),

  // Mock form upload endpoint
  rest.post('/api/uploads/form-video', (req, res, ctx) => {
    return res(
      ctx.json({
        uploadId: 'upload-123',
        status: 'processing',
        message: 'Form video uploaded successfully. Processing has begun.',
      })
    );
  }),

  // Mock upload status endpoint
  rest.get('/api/uploads/status/:uploadId', (req, res, ctx) => {
    const { uploadId } = req.params;
    return res(
      ctx.json({
        uploadId,
        status: 'completed',
        results: {
          score: 85,
          feedback: 'Overall good form with minor adjustments needed.',
          formIssues: [
            {
              id: 'issue-1',
              title: 'Knee alignment',
              description: 'Knees going slightly past toes during squat.',
              severity: 'minor',
              timestamp: 2.5,
              recommendation: 'Focus on pushing hips back more before bending knees.',
            },
            {
              id: 'issue-2',
              title: 'Depth',
              description: 'Not reaching full depth on some repetitions.',
              severity: 'medium',
              timestamp: 5.8,
              recommendation: 'Work on mobility to achieve deeper squat position safely.',
            },
          ],
        },
      })
    );
  }),

  // Mock feedback detail endpoint
  rest.get('/api/feedback/:feedbackId', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'feedback-123',
        uploadId: 'upload-123',
        exerciseType: 'squat',
        score: 85,
        overallFeedback: 'Overall good form with minor adjustments needed.',
        formIssues: [
          {
            id: 'issue-1',
            title: 'Knee alignment',
            description: 'Knees going slightly past toes during squat.',
            severity: 'minor',
            timestamp: 2.5,
            recommendation: 'Focus on pushing hips back more before bending knees.',
          },
          {
            id: 'issue-2',
            title: 'Depth',
            description: 'Not reaching full depth on some repetitions.',
            severity: 'medium',
            timestamp: 5.8,
            recommendation: 'Work on mobility to achieve deeper squat position safely.',
          },
        ],
        videoUrl: 'https://mock-video-url.com/upload-123.mp4',
        createdAt: new Date().toISOString(),
      })
    );
  })
);

// Mock navigation
jest.mock('react-router-dom', () => {
  const originalModule = jest.requireActual('react-router-dom');
  return {
    ...originalModule,
    useNavigate: () => jest.fn(),
  };
});

// Mock file upload components
jest.mock('../../src/components/camera/CameraCapture', () => ({
  CameraCapture: ({ onVideoCapture }: { onVideoCapture: (file: File) => void }) => {
    const handleCapture = () => {
      const mockFile = new File(['mock video content'], 'exercise.mp4', { type: 'video/mp4' });
      onVideoCapture(mockFile);
    };

    return (
      <div data-testid="camera-capture">
        <button data-testid="capture-button" onClick={handleCapture}>
          Capture Video
        </button>
      </div>
    );
  },
}));

// Start server before tests
beforeAll(() => server.listen());
// Reset handlers after each test
afterEach(() => server.resetHandlers());
// Close server after all tests
afterAll(() => server.close());

describe('User Flow: Login → Upload Form → Receive Feedback', () => {
  // Mock localStorage
  let localStorageMock: { [key: string]: string } = {};
  
  beforeEach(() => {
    // Set up localStorage mock
    localStorageMock = {};
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn((key) => localStorageMock[key] || null),
        setItem: jest.fn((key, value) => {
          localStorageMock[key] = value;
        }),
        removeItem: jest.fn((key) => {
          delete localStorageMock[key];
        }),
        clear: jest.fn(() => {
          localStorageMock = {};
        }),
      },
      writable: true,
    });
  });

  const renderWithProviders = (component: React.ReactNode) => {
    return render(
      <Router>
        <ThemeProvider theme={mockTheme}>
          <AuthProvider>{component}</AuthProvider>
        </ThemeProvider>
      </Router>
    );
  };

  test('Complete user flow: login, upload form video, and view feedback', async () => {
    // Step 1: Render Login Page
    const { unmount } = renderWithProviders(<LoginPage />);
    
    // Fill in login form
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    userEvent.type(emailInput, 'test@example.com');
    userEvent.type(passwordInput, 'password123');
    fireEvent.click(loginButton);

    // Wait for login to complete
    await waitFor(() => {
      // Check localStorage for auth token
      expect(window.localStorage.getItem('auth_token')).toBe('mock-token-123');
    });

    // Unmount login page
    unmount();

    // Step 2: Render Form Upload Page
    renderWithProviders(<FormUploadPage />);

    // Capture video using mocked camera component
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Select exercise type (if available)
    const exerciseSelect = screen.getByLabelText(/exercise type/i);
    if (exerciseSelect) {
      fireEvent.change(exerciseSelect, { target: { value: 'squat' } });
    }

    // Submit form for analysis
    const uploadButton = screen.getByRole('button', { name: /upload.*analysis/i });
    fireEvent.click(uploadButton);

    // Wait for upload to complete
    await waitFor(() => {
      // Expect loading indicator or success message
      expect(screen.getByText(/processing|uploaded successfully/i)).toBeInTheDocument();
    });

    // Step 3: Transition to Feedback Page (would usually happen via redirect)
    renderWithProviders(<FeedbackPage />);

    // Wait for feedback to load
    await waitFor(() => {
      // Check for score display
      expect(screen.getByText(/85/)).toBeInTheDocument();
      // Check for feedback items
      expect(screen.getByText(/knee alignment/i)).toBeInTheDocument();
      expect(screen.getByText(/depth/i)).toBeInTheDocument();
      // Check for overall feedback text
      expect(screen.getByText(/overall good form/i)).toBeInTheDocument();
    });

    // Check detailed feedback interaction
    const feedbackItems = screen.getAllByRole('button', { name: /view details/i });
    if (feedbackItems.length > 0) {
      fireEvent.click(feedbackItems[0]);
      
      // Expect detailed recommendations to appear
      await waitFor(() => {
        expect(screen.getByText(/Focus on pushing hips back/i)).toBeInTheDocument();
      });
    }
  });

  test('Handles login error gracefully', async () => {
    // Override server response for this test
    server.use(
      rest.post('/api/auth/login', (req, res, ctx) => {
        return res(
          ctx.status(401),
          ctx.json({
            error: 'Invalid credentials'
          })
        );
      })
    );

    // Render login page
    renderWithProviders(<LoginPage />);
    
    // Fill in login form with invalid credentials
    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);
    const loginButton = screen.getByRole('button', { name: /login/i });

    userEvent.type(emailInput, 'wrong@example.com');
    userEvent.type(passwordInput, 'wrongpassword');
    fireEvent.click(loginButton);

    // Expect error message
    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  test('Handles upload processing errors gracefully', async () => {
    // Override server response for this test
    server.use(
      rest.post('/api/uploads/form-video', (req, res, ctx) => {
        return res(
          ctx.status(500),
          ctx.json({
            error: 'Error processing video'
          })
        );
      })
    );

    // Set mock authentication token
    window.localStorage.setItem('auth_token', 'mock-token-123');

    // Render upload page directly
    renderWithProviders(<FormUploadPage />);

    // Capture video
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Submit form
    const uploadButton = screen.getByRole('button', { name: /upload.*analysis/i });
    fireEvent.click(uploadButton);

    // Expect error message
    await waitFor(() => {
      expect(screen.getByText(/error processing video/i)).toBeInTheDocument();
    });
  });
}); 