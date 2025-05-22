/**
 * Consolidated Tests for Form Check Redux Flow
 * 
 * This file tests the full Form Check flow with a behavior-driven approach:
 * 1. User-centric workflows (submit, view, analyze, delete)
 * 2. UI and Redux state coordination
 * 3. Component behavior with Redux data
 * 4. Error handling and validation
 * 
 * Tests use a behavior-driven style focusing on user interactions
 * rather than implementation details.
 */
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { configureStore } from '@reduxjs/toolkit';
import { Provider } from 'react-redux';
import '@testing-library/jest-dom';

// Import shared mocks and utilities
import { 
  http, 
  formCheckHandlers, 
  setupMockServer, 
  setupServerLifecycle,
  createMockFormCheck,
  createMockFormChecks,
  FormCheck
} from '../../utils/sharedMocks';

// Import components, hooks and state management
import FormCheckFeedback from '../../components/FormCheckFeedback';
import { formCheckService } from '../../services/formCheckService';
import { 
  fetchFormChecks,
  fetchFormCheck,
  submitFormCheck,
  deleteFormCheck,
  updateFormCheckStatus,
  setFormChecks,
  addFormCheck,
  updateFormCheck,
  setCurrentFormCheck,
  setLoading,
  setError,
  formCheckReducer 
} from '../../store/slices/formCheckSlice';
import { ExerciseType, FormCheckStatus } from '../../types/formCheck';
import { testRender } from '../../tests/utils/testRender';

// Define additional type for feedback severity
type FeedbackSeverity = 'good' | 'warning' | 'error';

// Setup MSW server with formCheck handlers
const server = setupMockServer(formCheckHandlers);
setupServerLifecycle(server);

interface FeedbackItem {
  id: number;
  message: string;
  severity: 'good' | 'warning' | 'error';
  timestamp?: number;
}

// Mock components for testing Redux integration
const FormCheckList: React.FC = () => {
  const [formChecks, setFormChecks] = React.useState<FormCheck[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const dispatch = useAppDispatch();

  React.useEffect(() => {
    const loadFormChecks = async () => {
      setLoading(true);
      try {
        await dispatch(fetchFormChecks());
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    loadFormChecks();
  }, [dispatch]);

  const handleDelete = async (id: string | number) => {
    try {
      await dispatch(deleteFormCheck(id));
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Get form checks from Redux store
  const { formChecks: storeFormChecks, isLoading: storeLoading, error: storeError } = useAppSelector(
    (state) => state.formCheck
  );

  // Update local state when Redux state changes
  React.useEffect(() => {
    setFormChecks(storeFormChecks);
    setLoading(storeLoading);
    setError(storeError);
  }, [storeFormChecks, storeLoading, storeError]);

  if (loading) return <div data-testid="loading">Loading form checks...</div>;
  if (error) return <div data-testid="error">Error: {error}</div>;
  
  return (
    <div>
      <h2>Form Check History</h2>
      {formChecks.length === 0 ? (
        <p data-testid="empty-message">No form checks available</p>
      ) : (
        <ul data-testid="form-check-list">
          {formChecks.map((check) => (
            <li key={check.id} data-testid={`form-check-item-${check.id}`}>
              <div>
                <strong>{check.exercise_type}</strong>
                <p>Status: {check.status}</p>
                <p>Score: {check.score || 'Not scored yet'}</p>
                <button 
                  onClick={() => handleDelete(check.id)}
                  data-testid={`delete-btn-${check.id}`}
                >
                  Delete
                </button>
                <button
                  onClick={() => dispatch(fetchFormCheck(check.id.toString()))}
                  data-testid={`view-btn-${check.id}`}
                >
                  View Details
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

const FormCheckDetail: React.FC = () => {
  const { currentFormCheck, isLoading, error } = useAppSelector((state) => state.formCheck);
  const dispatch = useAppDispatch();

  const handleAnalyze = () => {
    if (currentFormCheck) {
      dispatch(updateFormCheckStatus({ id: currentFormCheck.id, status: 'analyzing' }));
      // Simulate analysis completion after delay
      setTimeout(() => {
        dispatch(updateFormCheckStatus({ 
          id: currentFormCheck.id, 
          status: 'completed',
          score: 85,
          feedback_items: [
            {
              id: 1,
              form_check_id: Number(currentFormCheck.id),
              type: 'form',
              severity: 'medium',
              message: 'Keep your knees aligned with your toes',
              timestamp: 1000,
              description: 'Your knees are moving inward during the squat',
              suggestions: 'Focus on pushing your knees outward'
            },
            {
              id: 2,
              form_check_id: Number(currentFormCheck.id),
              type: 'posture',
              severity: 'high',
              message: 'Maintain a neutral spine',
              timestamp: 2000,
              description: 'Your back is rounding at the bottom of the squat',
              suggestions: 'Keep your chest up and core engaged'
            }
          ]
        }));
      }, 500);
    }
  };

  if (isLoading) return <div data-testid="detail-loading">Loading form check details...</div>;
  if (error) return <div data-testid="detail-error">Error: {error}</div>;
  if (!currentFormCheck) return <div data-testid="no-form-check">No form check selected</div>;

  return (
    <div data-testid="form-check-detail">
      <h2>Form Check Details</h2>
      <p>Exercise: {currentFormCheck.exercise_type}</p>
      <p>Status: {currentFormCheck.status}</p>
      <p>Score: {currentFormCheck.score || 'Not scored yet'}</p>
      
      {currentFormCheck.status === 'pending' && (
        <button 
          onClick={handleAnalyze}
          data-testid="analyze-button"
        >
          Analyze Form
        </button>
      )}
      
      {currentFormCheck.status === 'analyzing' && (
        <div data-testid="analyzing-indicator">Analyzing your form...</div>
      )}
      
      {currentFormCheck.status === 'completed' && currentFormCheck.feedback_items && (
        <div data-testid="feedback-container">
          <h3>Feedback</h3>
          <FormCheckFeedback 
            feedback={currentFormCheck.feedback_items.map(item => ({
              id: item.id,
              message: item.message,
              severity: item.severity as 'good' | 'warning' | 'error'
            }))} 
            score={currentFormCheck.score || 0} 
          />
        </div>
      )}
    </div>
  );
};

const FormCheckSubmission: React.FC = () => {
  const [exerciseType, setExerciseType] = React.useState<ExerciseType>('squat');
  const [videoUrl, setVideoUrl] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const dispatch = useAppDispatch();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    
    try {
      await dispatch(submitFormCheck({
        exercise_type: exerciseType,
        video_url: videoUrl
      }));
      // Reset form after successful submission
      setVideoUrl('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <h2>Submit Form Check</h2>
      {error && <div data-testid="submit-error">Error: {error}</div>}
      
      <form onSubmit={handleSubmit} data-testid="form-check-form">
        <div>
          <label htmlFor="exercise-type">Exercise Type:</label>
          <select 
            id="exercise-type"
            value={exerciseType}
            onChange={(e) => setExerciseType(e.target.value as ExerciseType)}
            data-testid="exercise-type-select"
          >
            <option value="squat">Squat</option>
            <option value="deadlift">Deadlift</option>
            <option value="bench_press">Bench Press</option>
          </select>
        </div>
        
        <div>
          <label htmlFor="video-url">Video URL:</label>
          <input 
            id="video-url"
            type="text"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="Enter video URL"
            data-testid="video-url-input"
            required
          />
        </div>
        
        <button 
          type="submit" 
          disabled={submitting}
          data-testid="submit-button"
        >
          {submitting ? 'Submitting...' : 'Submit Form Check'}
        </button>
      </form>
    </div>
  );
};

// Create a combined component for testing the entire flow
const FormCheckApp: React.FC = () => {
  return (
    <div>
      <FormCheckSubmission />
      <FormCheckList />
      <FormCheckDetail />
    </div>
  );
};

// Mock hooks from Redux
const useAppDispatch = () => {
  const { useDispatch } = require('react-redux');
  return useDispatch();
};

const useAppSelector = <T,>(selector: (state: any) => T) => {
  const { useSelector } = require('react-redux');
  return useSelector(selector);
};

// Mock data
const mockFormChecks: FormCheck[] = [
  {
    id: '1',
    user_id: 101,
    exercise_type: 'squat',
    video_url: 'https://example.com/video1.mp4',
    score: 85,
    status: 'completed',
    feedback_items: [
      {
        id: 1,
        form_check_id: 1,
        type: 'form',
        severity: 'medium',
        message: 'Keep your knees aligned with your toes',
        timestamp: 1000,
        description: 'Your knees are moving inward during the squat',
        suggestions: 'Focus on pushing your knees outward'
      }
    ],
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
  },
  {
    id: '2',
    user_id: 101,
    exercise_type: 'deadlift',
    video_url: 'https://example.com/video2.mp4',
    score: 78,
    status: 'completed',
    created_at: '2023-01-02T00:00:00Z',
    updated_at: '2023-01-02T00:00:00Z',
  },
  {
    id: '3',
    user_id: 101,
    exercise_type: 'bench_press',
    video_url: 'https://example.com/video3.mp4',
    status: 'pending',
    created_at: '2023-01-03T00:00:00Z',
    updated_at: '2023-01-03T00:00:00Z',
  }
];

// Mock API endpoints with MSW
const server = setupServer(
  // Get all form checks
  rest.get('/api/form-checks', (req, res, ctx) => {
    const exerciseType = req.url.searchParams.get('exercise_type');
    let formChecks = [...mockFormChecks];
    
    if (exerciseType) {
      formChecks = formChecks.filter(check => check.exercise_type === exerciseType);
    }
    
    return res(ctx.json(formChecks));
  }),
  
  // Get single form check
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    const formCheck = mockFormChecks.find(check => check.id.toString() === id);
    
    if (!formCheck) {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found' }));
    }
    
    return res(ctx.json(formCheck));
  }),
  
  // Create form check
  rest.post('/api/form-checks', (req, res, ctx) => {
    const body = req.body as any;
    const newFormCheck: FormCheck = {
      id: `${Date.now()}`,
      user_id: 101,
      exercise_type: body.exercise_type,
      video_url: body.video_url,
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    return res(ctx.status(201), ctx.json(newFormCheck));
  }),
  
  // Delete form check
  rest.delete('/api/form-checks/:id', (req, res, ctx) => {
    return res(ctx.json({ success: true }));
  }),
  
  // Update form check status
  rest.patch('/api/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    const body = req.body as any;
    const formCheck = mockFormChecks.find(check => check.id.toString() === id);
    
    if (!formCheck) {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found' }));
    }
    
    const updatedFormCheck = {
      ...formCheck,
      ...body,
      updated_at: new Date().toISOString()
    };
    
    return res(ctx.json(updatedFormCheck));
  }),
  
  // Analyze form check
  rest.post('/api/form-checks/:id/analyze', (req, res, ctx) => {
    const { id } = req.params;
    const formCheck = mockFormChecks.find(check => check.id.toString() === id);
    
    if (!formCheck) {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found' }));
    }
    
    const analyzedFormCheck = {
      ...formCheck,
      status: 'analyzing',
      updated_at: new Date().toISOString()
    };
    
    return res(ctx.json(analyzedFormCheck));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock FormCheckService
jest.mock('../../services/formCheckService', () => ({
  formCheckService: {
    getFormChecks: jest.fn(),
    getFormCheck: jest.fn(),
    createFormCheck: jest.fn(),
    updateFormCheck: jest.fn(),
    deleteFormCheck: jest.fn(),
    analyze: jest.fn()
  }
}));

// Helper function to render with Redux store
const renderWithStore = (
  ui: React.ReactNode,
  {
    preloadedState = {},
    store = configureStore({
      reducer: { formCheck: formCheckReducer },
      preloadedState
    }),
    ...renderOptions
  } = {}
) => {
  const Wrapper: React.FC<{children: React.ReactNode}> = ({ children }) => (
    <Provider store={store}>{children}</Provider>
  );
  
  return { 
    ...render(ui as React.ReactElement, { wrapper: Wrapper, ...renderOptions }),
    store,
    user: userEvent.setup()
  };
};

describe('FormCheck Redux Flow', () => {
  // =========================================
  // User Workflows - Full Flow Integration Tests
  // =========================================
  describe('User Workflows', () => {
    it('WHEN a user submits a form check THEN they can view it in the list and delete it', async () => {
      const { user } = renderWithStore(<FormCheckApp />);
      
      // Fill out and submit a new form check
      await user.type(screen.getByTestId('video-url-input'), 'https://example.com/my-squat-video.mp4');
      await user.selectOptions(screen.getByTestId('exercise-type-select'), 'squat');
      await user.click(screen.getByTestId('submit-button'));
      
      // Wait for submission and list to update
      await waitFor(() => {
        expect(screen.getByTestId('form-check-list')).toBeInTheDocument();
      });
      
      // Find the newly added form check in the list
      const listItems = await screen.findAllByTestId(/^form-check-item-/);
      expect(listItems.length).toBeGreaterThan(0);
      
      // Click the delete button on the first form check
      const deleteButtons = screen.getAllByTestId(/^delete-btn-/);
      await user.click(deleteButtons[0]);
      
      // Verify the form check was removed
      await waitFor(() => {
        const updatedListItems = screen.getAllByTestId(/^form-check-item-/);
        expect(updatedListItems.length).toBeLessThan(listItems.length);
      });
    });

    it('GIVEN a pending form check WHEN a user views details and analyzes it THEN feedback is displayed', async () => {
      // Set up store with a pending form check
      const preloadedState = {
        formCheck: {
          formChecks: [mockFormChecks[2]], // Use the pending form check
          currentFormCheck: null,
          isLoading: false,
          error: null
        }
      };
      
      const { user } = renderWithStore(<FormCheckApp />, { preloadedState });
      
      // Wait for the form check list to render
      await waitFor(() => {
        expect(screen.getByTestId('form-check-list')).toBeInTheDocument();
      });
      
      // Click view details on the pending form check
      await user.click(screen.getByTestId(`view-btn-${mockFormChecks[2].id}`));
      
      // Wait for the details to load
      await waitFor(() => {
        expect(screen.getByTestId('form-check-detail')).toBeInTheDocument();
      });
      
      // Click the analyze button
      await user.click(screen.getByTestId('analyze-button'));
      
      // Verify analyzing state is shown
      expect(screen.getByTestId('analyzing-indicator')).toBeInTheDocument();
      
      // Wait for analysis to complete and feedback to be shown
      await waitFor(() => {
        expect(screen.getByTestId('feedback-container')).toBeInTheDocument();
      }, { timeout: 1000 });
      
      // Verify feedback content is displayed
      expect(screen.getByText(/Keep your knees aligned with your toes/i)).toBeInTheDocument();
    });
    
    it('GIVEN multiple form checks WHEN a user selects one THEN they can view its detailed information', async () => {
      // Set up store with multiple form checks
      const preloadedState = {
        formCheck: {
          formChecks: mockFormChecks,
          currentFormCheck: null,
          isLoading: false,
          error: null
        }
      };
      
      const { user } = renderWithStore(<FormCheckApp />, { preloadedState });
      
      // Wait for the form check list to render
      await waitFor(() => {
        expect(screen.getByTestId('form-check-list')).toBeInTheDocument();
      });
      
      // Find all view buttons and click on the second one
      const viewButtons = screen.getAllByTestId(/^view-btn-/);
      await user.click(viewButtons[1]); // View the second form check
      
      // Wait for the details to load
      await waitFor(() => {
        expect(screen.getByTestId('form-check-detail')).toBeInTheDocument();
      });
      
      // Verify specific details are shown for the selected form check
      expect(screen.getByText(`Exercise: ${mockFormChecks[1].exercise_type}`)).toBeInTheDocument();
      expect(screen.getByText(`Status: ${mockFormChecks[1].status}`)).toBeInTheDocument();
      
      if (mockFormChecks[1].score) {
        expect(screen.getByText(`Score: ${mockFormChecks[1].score}`)).toBeInTheDocument();
      }
    });
  });
  
  // =========================================
  // UI-Redux Integration Tests
  // =========================================
  describe('UI Integration with Redux', () => {
    it('GIVEN form checks in Redux store WHEN UI renders THEN it displays all form checks', async () => {
      // Render with Redux store containing form checks
      testRender(<FormCheckListView formChecks={mockFormChecks} />, {});

      // Check all form checks are displayed with proper details
      const listItems = screen.getAllByTestId(/^form-check-/);
      expect(listItems).toHaveLength(mockFormChecks.length);
      
      // Verify content of specific form checks
      mockFormChecks.forEach(check => {
        const element = screen.getByTestId(`form-check-${check.id}`);
        expect(element).toBeInTheDocument();
        expect(screen.getByTestId(`exercise-${check.id}`)).toHaveTextContent(check.exercise_type);
        expect(screen.getByTestId(`status-${check.id}`)).toHaveTextContent(check.status);
      });
    });

    it('WHEN delete button is clicked THEN it triggers delete action', async () => {
      // Create mock function for delete callback
      const handleDelete = jest.fn();
      
      // Render component with delete handler
      const { user } = testRender(
        <FormCheckListView formChecks={mockFormChecks} onDeleteClick={handleDelete} />
      );
      
      // Find delete button for the first form check and click it
      const deleteButton = screen.getByTestId(`delete-button-${mockFormChecks[0].id}`);
      await user.click(deleteButton);
      
      // Verify delete handler was called with the correct ID
      expect(handleDelete).toHaveBeenCalledWith(mockFormChecks[0].id);
    });

    it('GIVEN an empty form check list WHEN UI renders THEN it shows empty state message', async () => {
      // Render with an empty list
      testRender(<FormCheckListView formChecks={[]} />);
      
      // Verify empty state message is displayed
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.queryByTestId('form-check-list')).not.toBeInTheDocument();
    });
  });
  
  // =========================================
  // User-Driven Redux State Changes
  // =========================================
  describe('User-Driven Redux State Changes', () => {
    it('WHEN a user fetches form checks THEN the Redux store is updated correctly', async () => {
      const store = configureStore({
        reducer: { formCheck: formCheckReducer }
      });
      
      // Mock service implementation
      (formCheckService.getFormChecks as jest.Mock).mockResolvedValue(mockFormChecks);
      
      // Dispatch the action (simulating a user clicking "fetch" button)
      await store.dispatch(fetchFormChecks());
      
      // Verify store state was updated as expected
      const state = store.getState();
      expect(state.formCheck.formChecks).toEqual(mockFormChecks);
      expect(state.formCheck.isLoading).toBe(false);
      expect(state.formCheck.error).toBe(null);
    });
    
    it('WHEN a user submits a new form check THEN it is added to Redux store', async () => {
      // Create a store with an initial empty state
      const store = configureStore({
        reducer: { formCheck: formCheckReducer },
        preloadedState: {
          formCheck: {
            formChecks: [],
            currentFormCheck: null,
            isLoading: false,
            error: null
          }
        }
      });
      
      // Prepare mock data for new form check
      const newFormCheck = {
        exercise_type: 'squat',
        video_url: 'https://example.com/new-video.mp4'
      };
      
      const createdFormCheck = {
        id: '123',
        user_id: 101,
        ...newFormCheck,
        status: 'pending',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };
      
      // Mock service implementation
      (formCheckService.createFormCheck as jest.Mock).mockResolvedValue(createdFormCheck);
      
      // Dispatch action (simulating user submitting form)
      await store.dispatch(submitFormCheck(newFormCheck));
      
      // Verify store state
      const state = store.getState();
      expect(state.formCheck.currentFormCheck).toEqual(createdFormCheck);
    });
    
    it('WHEN a user deletes a form check THEN it is removed from Redux store', async () => {
      // Create store with initial form checks
      const store = configureStore({
        reducer: { formCheck: formCheckReducer },
        preloadedState: {
          formCheck: {
            formChecks: [...mockFormChecks],
            currentFormCheck: null,
            isLoading: false,
            error: null
          }
        }
      });
      
      // Verify initial state
      expect(store.getState().formCheck.formChecks.length).toBe(mockFormChecks.length);
      
      // Mock service implementation
      (formCheckService.deleteFormCheck as jest.Mock).mockResolvedValue({ success: true });
      
      // Dispatch action (simulating user clicking delete button)
      const idToDelete = mockFormChecks[0].id;
      await store.dispatch(deleteFormCheck(idToDelete));
      
      // Verify form check was removed
      const state = store.getState();
      expect(state.formCheck.formChecks.find(check => 
        check.id.toString() === idToDelete.toString()
      )).toBeUndefined();
      expect(state.formCheck.formChecks.length).toBe(mockFormChecks.length - 1);
    });
  });
  
  // =========================================
  // Form Check Feedback Component
  // =========================================
  describe('Form Check Feedback Component Behavior', () => {
    it('GIVEN a form check with good feedback WHEN rendered THEN it displays with proper severity indicators', () => {
      const mockFeedback: FeedbackItem[] = [
        { id: 1, message: 'Great depth in your squat', severity: 'good' },
        { id: 2, message: 'Nice control throughout the movement', severity: 'good' }
      ];
      
      render(<FormCheckFeedback feedback={mockFeedback} score={95} />);
      
      // Verify score and messages are displayed
      expect(screen.getByText(/95%/i)).toBeInTheDocument();
      expect(screen.getByText(/Great depth in your squat/i)).toBeInTheDocument();
      expect(screen.getByText(/Nice control throughout the movement/i)).toBeInTheDocument();
    });
    
    it('GIVEN a form check with mixed feedback WHEN rendered THEN it shows different severity levels', () => {
      const mockFeedback: FeedbackItem[] = [
        { id: 1, message: 'Good depth', severity: 'good' },
        { id: 2, message: 'Watch your knee alignment', severity: 'warning' },
        { id: 3, message: 'Back is rounding', severity: 'error' }
      ];
      
      render(<FormCheckFeedback feedback={mockFeedback} score={75} />);
      
      // Check that all messages are displayed
      expect(screen.getByText(/Good depth/i)).toBeInTheDocument();
      expect(screen.getByText(/Watch your knee alignment/i)).toBeInTheDocument();
      expect(screen.getByText(/Back is rounding/i)).toBeInTheDocument();
    });
    
    it('GIVEN a form check without feedback WHEN rendered THEN it shows empty state message', () => {
      render(<FormCheckFeedback feedback={[]} score={0} />);
      
      // Verify empty state message
      expect(screen.getByText(/No feedback available/i)).toBeInTheDocument();
    });
  });
  
  // =========================================
  // Error Handling Tests
  // =========================================
  describe('Error Handling', () => {
    it('displays error message when API request fails', async () => {
      // Mock API error
      server.use(
        rest.get('/api/form-checks', (req, res, ctx) => {
          return res(ctx.status(500), ctx.json({ message: 'Server error' }));
        })
      );
      
      renderWithStore(<FormCheckList />);
      
      // Wait for the error to be displayed
      await waitFor(() => {
        expect(screen.getByTestId('error')).toBeInTheDocument();
      });
      
      expect(screen.getByTestId('error')).toHaveTextContent(/error/i);
    });
    
    it('shows validation errors when submitting invalid form data', async () => {
      const { user } = renderWithStore(<FormCheckSubmission />);
      
      // Submit without filling out the required video URL
      await user.selectOptions(screen.getByTestId('exercise-type-select'), 'squat');
      await user.click(screen.getByTestId('submit-button'));
      
      // Check for HTML5 validation - the form shouldn't submit
      expect(screen.getByTestId('video-url-input')).toBeInvalid();
    });
  });
});

// Redux-connected component with detailed presentation options
// This component focuses on more granular Redux-UI integration
const FormCheckListView: React.FC<{
  formChecks: FormCheck[];
  onDeleteClick?: (id: number | string) => void;
}> = ({ 
  formChecks, 
  onDeleteClick 
}) => {
  return (
    <div data-testid="form-check-container">
      {formChecks.length === 0 ? (
        <p data-testid="empty-state">No form checks found</p>
      ) : (
        <div>
          <ul data-testid="form-check-list">
            {formChecks.map(check => (
              <li key={check.id} data-testid={`form-check-${check.id}`}>
                <div data-testid={`exercise-${check.id}`}>
                  Exercise: {check.exercise_type}
                </div>
                <div data-testid={`status-${check.id}`}>
                  Status: {check.status}
                </div>
                {check.score && (
                  <div data-testid={`score-${check.id}`}>
                    Score: {check.score}
                  </div>
                )}
                {onDeleteClick && (
                  <button
                    data-testid={`delete-button-${check.id}`}
                    onClick={() => onDeleteClick(check.id)}
                  >
                    Delete
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}; 