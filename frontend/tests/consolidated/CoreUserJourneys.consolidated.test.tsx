/**
 * Core User Journeys - Consolidated Test Suite
 * 
 * This file tests the primary user journeys through the FormIQ application:
 * 1. Registration & Login Flow - User account creation and authentication
 * 2. Upload & Analysis Flow - Video submission and form check analysis
 * 3. Results & Feedback Flow - Viewing and interacting with analysis results
 * 4. Workout Tracking Flow - Managing exercise sessions and tracking progress
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ThemeProvider } from 'styled-components';

// Import components and types necessary for test
import LoginForm from '../../frontend/src/components/auth/LoginForm';
import RegisterForm from '../../frontend/src/components/auth/RegisterForm';
import ProtectedRoute from '../../frontend/src/components/auth/ProtectedRoute';
import CameraCapture from '../../frontend/src/components/camera/CameraCapture';
import WorkoutTracking from '../../frontend/src/components/workout/WorkoutTracking';
import UploadComponent from '../../frontend/src/components/upload/UploadComponent';
import Dashboard from '../../frontend/src/pages/Dashboard';
import FormCheckFeedback from '../../frontend/src/components/feedback/FormCheckFeedback';
import UserProfile from '../../frontend/src/components/profile/UserProfile';
import { theme } from '../../frontend/src/theme';

// Import reducers
import authReducer from '../../frontend/src/store/slices/authSlice';
import workoutReducer from '../../frontend/src/store/slices/workoutSlice';
import formCheckReducer from '../../frontend/src/store/slices/formCheckSlice';
import uploadReducer from '../../frontend/src/store/slices/uploadSlice';
import profileReducer from '../../frontend/src/store/slices/profileSlice';

// Mock the media devices API
const mockMediaStream = {} as MediaStream;
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: jest.fn().mockResolvedValue(mockMediaStream),
    enumerateDevices: jest.fn().mockResolvedValue([{
      kind: 'videoinput',
      deviceId: 'mock-camera-id',
      label: 'Mock Camera'
    }])
  },
  writable: true
});

// Mock video element
const mockVideoElement = {
  play: jest.fn(),
  pause: jest.fn(),
  srcObject: null,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn()
};

// Mock localStorage for auth token storage
const localStorageMock = (function() {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

// Setup MSW for API mocking
const server = setupServer(
  // Auth endpoints
  rest.post('/api/auth/login', (req, res, ctx) => {
    const { email, password } = req.body as any;
    
    if (email === 'test@example.com' && password === 'password123') {
      return res(
        ctx.status(200),
        ctx.json({
          user: {
            id: 'user-123',
            email: 'test@example.com',
            name: 'Test User'
          },
          tokens: {
            accessToken: 'mock-token-123',
            refreshToken: 'mock-refresh-token-123'
          }
        })
      );
    }
    
    return res(
      ctx.status(401),
      ctx.json({ message: 'Invalid credentials' })
    );
  }),
  
  rest.post('/api/auth/register', (req, res, ctx) => {
    const { email, password, name } = req.body as any;
    
    if (!email || !password || !name) {
      return res(
        ctx.status(400),
        ctx.json({ message: 'All fields are required' })
      );
    }
    
    return res(
      ctx.status(201),
      ctx.json({
        user: {
          id: 'user-new',
          email,
          name
        },
        tokens: {
          accessToken: 'mock-token-new',
          refreshToken: 'mock-refresh-token-new'
        }
      })
    );
  }),
  
  // Video upload endpoint
  rest.post('/api/uploads/video', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        id: 'upload-123',
        url: 'https://example.com/videos/mock-video.mp4'
      })
    );
  }),
  
  // Form check submission endpoint
  rest.post('/api/form-checks', (req, res, ctx) => {
    const body = req.body as any;
    
    return res(
      ctx.status(201),
      ctx.json({
        id: 'form-check-123',
        user_id: 'user-123',
        exercise_type: body.exercise_type,
        video_url: body.video_url,
        status: 'pending',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
    );
  }),
  
  // Form check analysis endpoint
  rest.post('/api/form-checks/:id/analyze', (req, res, ctx) => {
    const { id } = req.params;
    
    return res(
      ctx.status(200),
      ctx.json({
        id,
        status: 'analyzing'
      })
    );
  }),
  
  // Form check result endpoint
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    
    return res(
      ctx.status(200),
      ctx.json({
        id,
        user_id: 'user-123',
        exercise_type: 'squat',
        video_url: 'https://example.com/videos/mock-video.mp4',
        status: 'completed',
        score: 85,
        feedback_items: [
          {
            id: 1,
            message: 'Good depth on your squat',
            severity: 'good',
            timestamp: 1000
          },
          {
            id: 2,
            message: 'Keep your knees aligned with your toes',
            severity: 'warning',
            timestamp: 2000
          }
        ],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
    );
  }),
  
  // Workout endpoints
  rest.get('/api/workouts', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        {
          id: 'workout-1',
          name: 'Full Body Workout',
          exercises: [
            {
              id: 'exercise-1',
              name: 'Squats',
              sets: 3,
              reps: 10
            },
            {
              id: 'exercise-2',
              name: 'Push-ups',
              sets: 3,
              reps: 10
            }
          ]
        }
      ])
    );
  }),
  
  rest.post('/api/workouts/:id/start', (req, res, ctx) => {
    const { id } = req.params;
    
    return res(
      ctx.status(200),
      ctx.json({
        id: 'session-123',
        workout_id: id,
        status: 'in_progress',
        started_at: new Date().toISOString()
      })
    );
  }),
  
  rest.post('/api/workouts/sessions/:id/complete', (req, res, ctx) => {
    const { id } = req.params;
    
    return res(
      ctx.status(200),
      ctx.json({
        id,
        status: 'completed',
        completed_at: new Date().toISOString()
      })
    );
  }),
  
  // User profile endpoints
  rest.get('/api/users/profile', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: 'user-123',
        name: 'Test User',
        email: 'test@example.com',
        created_at: '2023-01-01T00:00:00.000Z',
        preferences: {
          notifications_enabled: true,
          dark_mode: false
        }
      })
    );
  }),
  
  rest.put('/api/users/profile', (req, res, ctx) => {
    const updatedProfile = req.body as any;
    
    return res(
      ctx.status(200),
      ctx.json({
        ...updatedProfile,
        id: 'user-123',
        updated_at: new Date().toISOString()
      })
    );
  })
);

beforeAll(() => {
  // Start the API mocking server
  server.listen();
  
  // Mock document.createElement for video elements
  global.document.createElement = jest.fn().mockImplementation((tag) => {
    if (tag === 'video') {
      return mockVideoElement as unknown as HTMLVideoElement;
    }
    return document.createElement(tag);
  });
});

afterEach(() => {
  // Reset request handlers
  server.resetHandlers();
  
  // Clear localStorage and mocks
  localStorage.clear();
  jest.clearAllMocks();
});

afterAll(() => {
  // Stop API mocking server
  server.close();
});

// Setup store for testing
const createTestStore = (preloadedState = {}) => {
  return configureStore({
    reducer: {
      auth: authReducer,
      workout: workoutReducer,
      formCheck: formCheckReducer,
      upload: uploadReducer,
      profile: profileReducer
    },
    preloadedState
  });
};

// Render with all providers needed for testing
const renderWithProviders = (
  ui: React.ReactElement,
  {
    preloadedState = {},
    store = createTestStore(preloadedState),
    route = '/',
    ...renderOptions
  } = {}
) => {
  const Wrapper: React.FC<{children: React.ReactNode}> = ({ children }) => {
    return (
      <Provider store={store}>
        <ThemeProvider theme={theme}>
          <MemoryRouter initialEntries={[route]}>
            {children}
          </MemoryRouter>
        </ThemeProvider>
      </Provider>
    );
  };
  
  return {
    user: userEvent.setup(),
    store,
    ...render(ui, { wrapper: Wrapper, ...renderOptions })
  };
};

// App component for integration testing
const TestApp = () => (
  <Routes>
    <Route path="/login" element={<LoginForm />} />
    <Route path="/register" element={<RegisterForm />} />
    <Route path="/dashboard" element={
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    } />
    <Route path="/upload" element={
      <ProtectedRoute>
        <UploadComponent />
      </ProtectedRoute>
    } />
    <Route path="/camera" element={
      <ProtectedRoute>
        <CameraCapture />
      </ProtectedRoute>
    } />
    <Route path="/workout" element={
      <ProtectedRoute>
        <WorkoutTracking />
      </ProtectedRoute>
    } />
    <Route path="/feedback/:id" element={
      <ProtectedRoute>
        <FormCheckFeedback />
      </ProtectedRoute>
    } />
    <Route path="/profile" element={
      <ProtectedRoute>
        <UserProfile />
      </ProtectedRoute>
    } />
  </Routes>
);

describe('Core User Journeys', () => {
  /**
   * Registration & Login Flow
   * Tests the user account creation and authentication journeys
   */
  describe('Registration & Login Journey', () => {
    it('GIVEN a new user WHEN they complete registration THEN they are logged in and redirected to dashboard', async () => {
      const { user } = renderWithProviders(<TestApp />, { route: '/register' });
      
      // Complete registration form
      await user.type(screen.getByLabelText(/name/i), 'New User');
      await user.type(screen.getByLabelText(/email/i), 'newuser@example.com');
      await user.type(screen.getByLabelText(/password/i), 'newpassword123');
      await user.click(screen.getByRole('button', { name: /register/i }));
      
      // Wait for registration API call to complete and redirect to dashboard
      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBe('mock-token-new');
      });
      
      // Verify user is on dashboard page
      await waitFor(() => {
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a returning user WHEN they login THEN they can access protected content', async () => {
      const { user } = renderWithProviders(<TestApp />, { route: '/login' });
      
      // Complete login form
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.click(screen.getByRole('button', { name: /login/i }));
      
      // Verify login was successful
      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBe('mock-token-123');
      });
      
      // Verify user can access protected content
      await waitFor(() => {
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a user with incorrect credentials WHEN they attempt login THEN they see an error message', async () => {
      const { user } = renderWithProviders(<TestApp />, { route: '/login' });
      
      // Complete login form with wrong password
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
      await user.click(screen.getByRole('button', { name: /login/i }));
      
      // Verify error is displayed
      await waitFor(() => {
        expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
      });
    });
  });
  
  /**
   * Upload & Analysis Flow
   * Tests the video capture, upload and analysis submission journeys
   */
  describe('Upload & Analysis Journey', () => {
    // Set authenticated state for protected routes
    const authenticatedState = {
      auth: {
        isAuthenticated: true,
        user: { id: 'user-123', email: 'test@example.com' },
        isLoading: false,
        error: null
      }
    };
    
    it('GIVEN an authenticated user WHEN they capture video with camera THEN they can upload it for analysis', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/camera',
        preloadedState: authenticatedState
      });
      
      // Wait for camera to initialize
      await waitFor(() => {
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      });
      
      // Start recording
      await user.click(screen.getByRole('button', { name: /record/i }));
      
      // Verify recording has started
      expect(screen.getByText(/recording/i)).toBeInTheDocument();
      
      // Stop recording
      await user.click(screen.getByRole('button', { name: /stop/i }));
      
      // Verify preview is shown
      await waitFor(() => {
        expect(screen.getByTestId('video-preview')).toBeInTheDocument();
      });
      
      // Submit for analysis
      await user.click(screen.getByRole('button', { name: /upload/i }));
      
      // Verify loading state is shown
      expect(screen.getByTestId('upload-progress')).toBeInTheDocument();
      
      // Verify redirection to feedback page
      await waitFor(() => {
        expect(screen.getByTestId('feedback-view')).toBeInTheDocument();
      });
    });
    
    it('GIVEN an authenticated user WHEN they select a video file THEN they can upload it for form check', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/upload',
        preloadedState: authenticatedState
      });
      
      // Select exercise type
      await user.selectOptions(
        screen.getByLabelText(/exercise type/i),
        'squat'
      );
      
      // Upload video file
      const fileInput = screen.getByLabelText(/upload video/i);
      const file = new File(['video content'], 'squat.mp4', { type: 'video/mp4' });
      await user.upload(fileInput, file);
      
      // Verify file was selected
      expect(fileInput.files?.[0]?.name).toBe('squat.mp4');
      
      // Submit for analysis
      await user.click(screen.getByRole('button', { name: /analyze/i }));
      
      // Verify loading state during upload
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      
      // Verify redirect to feedback page after upload
      await waitFor(() => {
        expect(screen.getByTestId('feedback-view')).toBeInTheDocument();
      });
    });
    
    it('GIVEN an authenticated user WHEN they attempt to upload an invalid file THEN they see an appropriate error', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/upload',
        preloadedState: authenticatedState
      });
      
      // Upload invalid file
      const fileInput = screen.getByLabelText(/upload video/i);
      const file = new File(['text content'], 'document.txt', { type: 'text/plain' });
      await user.upload(fileInput, file);
      
      // Verify error message is shown
      await waitFor(() => {
        expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();
      });
    });
  });
  
  /**
   * Results & Feedback Flow
   * Tests the viewing and interaction with analysis results
   */
  describe('Results & Feedback Journey', () => {
    // Set authenticated state for protected routes with form check results
    const authenticatedStateWithResults = {
      auth: {
        isAuthenticated: true,
        user: { id: 'user-123', email: 'test@example.com' },
        isLoading: false,
        error: null
      },
      formCheck: {
        currentFormCheck: {
          id: 'form-check-123',
          exercise_type: 'squat',
          status: 'completed',
          score: 85,
          feedback_items: [
            {
              id: 1,
              message: 'Good depth on your squat',
              severity: 'good',
              timestamp: 1000
            },
            {
              id: 2,
              message: 'Keep your knees aligned with your toes',
              severity: 'warning',
              timestamp: 2000
            }
          ]
        },
        isLoading: false,
        error: null
      }
    };
    
    it('GIVEN a user with completed form check WHEN they view results THEN they can see detailed feedback', async () => {
      renderWithProviders(<TestApp />, {
        route: '/feedback/form-check-123',
        preloadedState: authenticatedStateWithResults
      });
      
      // Verify feedback page is shown
      await waitFor(() => {
        expect(screen.getByTestId('feedback-view')).toBeInTheDocument();
      });
      
      // Verify score is displayed
      expect(screen.getByText(/85/i)).toBeInTheDocument();
      
      // Verify feedback items are displayed
      expect(screen.getByText(/good depth on your squat/i)).toBeInTheDocument();
      expect(screen.getByText(/keep your knees aligned with your toes/i)).toBeInTheDocument();
    });
    
    it('GIVEN a user viewing feedback WHEN they navigate through feedback items THEN they can see specific timestamps', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/feedback/form-check-123',
        preloadedState: authenticatedStateWithResults
      });
      
      // Wait for feedback page to load
      await waitFor(() => {
        expect(screen.getByTestId('feedback-view')).toBeInTheDocument();
      });
      
      // Click on second feedback item
      await user.click(screen.getByText(/keep your knees aligned with your toes/i));
      
      // Verify video timestamp is updated (if applicable in your UI)
      // This will depend on your actual implementation
      const feedbackItem = screen.getByText(/keep your knees aligned with your toes/i).closest('div');
      expect(feedbackItem).toHaveAttribute('data-active', 'true');
    });
  });
  
  /**
   * Workout Tracking Flow
   * Tests the management of workout sessions and exercise tracking
   */
  describe('Workout Tracking Journey', () => {
    // Set authenticated state for protected routes
    const authenticatedState = {
      auth: {
        isAuthenticated: true,
        user: { id: 'user-123', email: 'test@example.com' },
        isLoading: false,
        error: null
      }
    };
    
    it('GIVEN an authenticated user WHEN they start and complete a workout THEN their progress is tracked', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/workout',
        preloadedState: authenticatedState
      });
      
      // Wait for workout plans to load
      await waitFor(() => {
        expect(screen.getByText(/full body workout/i)).toBeInTheDocument();
      });
      
      // Start workout
      await user.click(screen.getByRole('button', { name: /start workout/i }));
      
      // Verify workout has started
      await waitFor(() => {
        expect(screen.getByText(/in progress/i)).toBeInTheDocument();
      });
      
      // Complete first exercise
      const exerciseItem = screen.getByText(/squats/i).closest('div');
      await user.click(within(exerciseItem!).getByRole('button', { name: /complete/i }));
      
      // Complete second exercise
      const secondExercise = screen.getByText(/push-ups/i).closest('div');
      await user.click(within(secondExercise!).getByRole('button', { name: /complete/i }));
      
      // Finish workout
      await user.click(screen.getByRole('button', { name: /finish workout/i }));
      
      // Verify workout has been completed
      await waitFor(() => {
        expect(screen.getByText(/completed/i)).toBeInTheDocument();
      });
      
      // Verify workout history is updated
      expect(screen.getByTestId('workout-history')).toHaveTextContent(/full body workout/i);
    });
  });
  
  /**
   * Profile Management Flow
   * Tests the viewing and updating of user profile information
   */
  describe('Profile Management Journey', () => {
    // Set authenticated state with profile data
    const authenticatedStateWithProfile = {
      auth: {
        isAuthenticated: true,
        user: { id: 'user-123', email: 'test@example.com' },
        isLoading: false,
        error: null
      },
      profile: {
        data: {
          name: 'Test User',
          email: 'test@example.com',
          preferences: {
            notifications_enabled: true,
            dark_mode: false
          }
        },
        isLoading: false,
        error: null
      }
    };
    
    it('GIVEN an authenticated user WHEN they view their profile THEN they can update personal information', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/profile',
        preloadedState: authenticatedStateWithProfile
      });
      
      // Verify profile page is loaded
      await waitFor(() => {
        expect(screen.getByTestId('user-profile')).toBeInTheDocument();
      });
      
      // Edit name
      const nameInput = screen.getByLabelText(/name/i);
      await user.clear(nameInput);
      await user.type(nameInput, 'Updated User Name');
      
      // Submit form
      await user.click(screen.getByRole('button', { name: /save/i }));
      
      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/profile updated/i)).toBeInTheDocument();
      });
    });
    
    it('GIVEN an authenticated user WHEN they update preferences THEN changes are saved', async () => {
      const { user } = renderWithProviders(<TestApp />, {
        route: '/profile',
        preloadedState: authenticatedStateWithProfile
      });
      
      // Verify profile page is loaded
      await waitFor(() => {
        expect(screen.getByTestId('user-profile')).toBeInTheDocument();
      });
      
      // Toggle notifications preference
      await user.click(screen.getByLabelText(/notifications/i));
      
      // Save changes
      await user.click(screen.getByRole('button', { name: /save/i }));
      
      // Verify success message
      await waitFor(() => {
        expect(screen.getByText(/profile updated/i)).toBeInTheDocument();
      });
    });
  });
  
  /**
   * End-to-End User Journey
   * Tests complete user flows combining multiple journeys
   */
  describe('Complete End-to-End Journey', () => {
    it('GIVEN a new user WHEN they follow the complete app journey THEN they experience the core value proposition', async () => {
      const { user } = renderWithProviders(<TestApp />, { route: '/login' });
      
      // Login
      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.click(screen.getByRole('button', { name: /login/i }));
      
      // Verify login success and navigation to dashboard
      await waitFor(() => {
        expect(screen.getByTestId('dashboard')).toBeInTheDocument();
      });
      
      // Navigate to upload
      await user.click(screen.getByRole('link', { name: /upload/i }));
      
      // Wait for upload page to load
      await waitFor(() => {
        expect(screen.getByTestId('upload-component')).toBeInTheDocument();
      });
      
      // Select exercise type
      await user.selectOptions(
        screen.getByLabelText(/exercise type/i),
        'squat'
      );
      
      // Upload video file
      const fileInput = screen.getByLabelText(/upload video/i);
      const file = new File(['video content'], 'squat.mp4', { type: 'video/mp4' });
      await user.upload(fileInput, file);
      
      // Submit for analysis
      await user.click(screen.getByRole('button', { name: /analyze/i }));
      
      // Wait for redirect to feedback page
      await waitFor(() => {
        expect(screen.getByTestId('feedback-view')).toBeInTheDocument();
      });
      
      // Verify feedback is shown
      expect(screen.getByText(/good depth on your squat/i)).toBeInTheDocument();
      expect(screen.getByText(/keep your knees aligned with your toes/i)).toBeInTheDocument();
      
      // Verify score is displayed
      expect(screen.getByText(/85/i)).toBeInTheDocument();
      
      // Navigate to workout tracking
      await user.click(screen.getByRole('link', { name: /workout/i }));
      
      // Complete a workout tracking flow
      await waitFor(() => {
        expect(screen.getByText(/full body workout/i)).toBeInTheDocument();
      });
      
      // Start workout
      await user.click(screen.getByRole('button', { name: /start workout/i }));
      
      // Finish workout
      await waitFor(() => {
        expect(screen.getByText(/in progress/i)).toBeInTheDocument();
      });
      await user.click(screen.getByRole('button', { name: /finish workout/i }));
      
      // Verify workout completion
      await waitFor(() => {
        expect(screen.getByText(/completed/i)).toBeInTheDocument();
      });
    });
  });
}); 