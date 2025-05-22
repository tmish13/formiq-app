import React from 'react';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { configureStore } from '@reduxjs/toolkit';
import '@testing-library/jest-dom';

// Import the components and utilities
import FormCheckFeedback from '../../src/components/FormCheckFeedback';
import { formCheckService } from '../../src/services/formCheckService';
import { 
  fetchFormChecks,
  deleteFormCheck,
  setFormChecks,
  formCheckReducer 
} from '../../src/store/slices/formCheckSlice';
import { ExerciseType, FormCheckStatus } from '../../src/types/formCheck';
import { testRender } from '../../src/test-utils';

// Mock API
const server = setupServer(
  // Get form checks
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
    const formCheck = mockFormChecks.find(check => check.id === id);
    
    if (!formCheck) {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found', code: 'NOT_FOUND' }));
    }
    
    return res(ctx.json(formCheck));
  }),
  
  // Create form check
  rest.post('/api/form-checks', (req, res, ctx) => {
    const newFormCheck = {
      id: 'new-id',
      ...req.body,
      status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    return res(ctx.status(201), ctx.json(newFormCheck));
  }),
  
  // Update form check status
  rest.patch('/api/form-checks/:id/status', (req, res, ctx) => {
    const { id } = req.params;
    const { status } = req.body;
    const formCheck = mockFormChecks.find(check => check.id === id);
    
    if (!formCheck) {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found', code: 'NOT_FOUND' }));
    }
    
    const updatedFormCheck = {
      ...formCheck,
      status,
      updated_at: new Date().toISOString()
    };
    
    return res(ctx.json(updatedFormCheck));
  }),
  
  // Analyze form check
  rest.post('/api/form-checks/:id/analyze', (req, res, ctx) => {
    const { id } = req.params;
    const formCheck = mockFormChecks.find(check => check.id === id);
    
    if (!formCheck) {
      return res(ctx.status(404), ctx.json({ message: 'Form check not found', code: 'NOT_FOUND' }));
    }
    
    // Simulate analysis success
    const analyzedFormCheck = {
      ...formCheck,
      status: 'analyzed',
      score: 85,
      feedback: 'Great form! Keep your back straight for better results.',
      updated_at: new Date().toISOString()
    };
    
    return res(ctx.json(analyzedFormCheck));
  }),
  
  // Get form check history
  rest.get('/api/form-checks/history', (_req, res, ctx) => {
    return res(ctx.json(mockFormChecks));
  }),

  // Fallback for unhandled requests
  rest.all('*', (req, res, ctx) => {
    console.error(`Unhandled request: ${req.method} ${req.url.pathname}`);
    return res(ctx.status(500), ctx.json({ error: 'Please add request handler' }));
  })
);

// Mock data
const mockFormChecks = [
  {
    id: '1',
    user_id: '101',
    exercise_type: 'squat' as ExerciseType,
    video_url: 'https://example.com/video1.mp4',
    score: 85,
    status: 'completed' as FormCheckStatus,
    feedback: 'Great form! Keep your back straight for better results.',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
  },
  {
    id: '2',
    user_id: '101',
    exercise_type: 'deadlift' as ExerciseType,
    video_url: 'https://example.com/video2.mp4',
    score: 78,
    status: 'completed' as FormCheckStatus,
    feedback: 'Watch your back angle and keep your core engaged.',
    created_at: '2023-01-02T00:00:00Z',
    updated_at: '2023-01-02T00:00:00Z',
  },
];

// Mock FormCheckList component for Redux tests
const FormCheckList: React.FC = () => {
  const formChecks = useAppSelector((state: any) => state.formCheck.formChecks);
  const isLoading = useAppSelector((state: any) => state.formCheck.loading);
  const error = useAppSelector((state: any) => state.formCheck.error);
  const dispatch = useAppDispatch();

  const handleDelete = (id: string) => {
    dispatch(deleteFormCheck(id));
  };

  if (isLoading) {
    return <div role="status" aria-label="Loading form checks">Loading form checks...</div>;
  }

  if (error) {
    return <div role="alert">Error: {error}</div>;
  }

  return (
    <div>
      <h2>Form Check History</h2>
      {formChecks.length === 0 ? (
        <p data-testid="empty-state" role="status" aria-label="No form checks">No form checks found</p>
      ) : (
        <ul data-testid="form-check-list" aria-label="Form check list">
          {formChecks.map((check: any) => (
            <li 
              key={check.id} 
              data-testid={`form-check-${check.id}`} 
              role="listitem"
              aria-label={`${check.exercise_type} form check`}
            >
              <div>
                <h3>{check.exercise_type}</h3>
                <p>Status: <span aria-label="Status">{check.status}</span></p>
                <p>Score: <span aria-label="Score">{check.score || 'Not scored yet'}</span></p>
                <button 
                  onClick={() => handleDelete(check.id)}
                  data-testid={`delete-button-${check.id}`}
                  aria-label={`Delete ${check.exercise_type} form check`}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

// Mock hook for tests
const useFormCheck = () => {
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [formCheck, setFormCheck] = React.useState<any>(null);
  const [error, setError] = React.useState<string | null>(null);

  const analyzeFormCheck = async (id: string) => {
    try {
      setIsAnalyzing(true);
      setError(null);
      const result = await formCheckService.analyze(id);
      setFormCheck(result);
      return result;
    } catch (err: any) {
      setError(err.message || 'An error occurred during analysis');
      throw err;
    } finally {
      setIsAnalyzing(false);
    }
  };

  const fetchFormCheck = async (id: string) => {
    try {
      setIsAnalyzing(true);
      setError(null);
      const result = await formCheckService.getFormCheck(id);
      setFormCheck(result);
      return result;
    } catch (err: any) {
      setError(err.message || 'An error occurred fetching the form check');
      throw err;
    } finally {
      setIsAnalyzing(false);
    }
  };

  return {
    analyzeFormCheck,
    fetchFormCheck,
    isAnalyzing,
    formCheck,
    error
  };
};

// Component that uses the useFormCheck hook
const FormCheckAnalyzer: React.FC = () => {
  const { analyzeFormCheck, fetchFormCheck, isAnalyzing, formCheck, error } = useFormCheck();
  const [formCheckId, setFormCheckId] = React.useState('');

  const handleAnalyze = async () => {
    try {
      await analyzeFormCheck(formCheckId);
    } catch (err) {
      // Error is handled by the hook
    }
  };

  const handleFetch = async () => {
    try {
      await fetchFormCheck(formCheckId);
    } catch (err) {
      // Error is handled by the hook
    }
  };

  return (
    <div>
      <h2>Form Check Analysis</h2>
      <div>
        <label htmlFor="form-check-id">Form Check ID:</label>
        <input
          id="form-check-id"
          type="text"
          value={formCheckId}
          onChange={(e) => setFormCheckId(e.target.value)}
          aria-label="Form check ID"
        />
        <button 
          onClick={handleFetch}
          disabled={!formCheckId || isAnalyzing}
          aria-label="Fetch form check"
        >
          Fetch
        </button>
        <button 
          onClick={handleAnalyze}
          disabled={!formCheckId || isAnalyzing}
          aria-label="Analyze form check"
        >
          Analyze
        </button>
      </div>

      {isAnalyzing && (
        <div role="status" aria-label="Analyzing form check">
          Analyzing form check...
        </div>
      )}

      {error && (
        <div role="alert" aria-label="Analysis error">
          Error: {error}
        </div>
      )}

      {formCheck && !error && (
        <div role="region" aria-label="Form check result">
          <h3>{formCheck.exercise_type} Form Check</h3>
          <p>Status: {formCheck.status}</p>
          <p>Score: {formCheck.score || 'Not scored yet'}</p>
          {formCheck.feedback && (
            <div aria-label="Feedback">
              <h4>Feedback:</h4>
              <p>{formCheck.feedback}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Setup and teardown
beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

// Import Redux hooks
const { useAppSelector, useAppDispatch } = jest.requireActual('../../src/store/hooks');

describe('FormCheck Consolidated Tests', () => {
  // PART 1: UI Component Tests
  describe('FormCheckFeedback Component', () => {
    it('renders the good severity feedback correctly', async () => {
      const user = userEvent.setup();
      testRender(
        <FormCheckFeedback 
          feedback="Great job! Your form is excellent" 
          score={95} 
          severity="good" 
        />
      );
      
      // Check score is displayed with proper accessibility
      const scoreElement = screen.getByRole('status', { name: /score/i }) || screen.getByTestId('score');
      expect(scoreElement).toHaveTextContent('95%');
      
      // Check feedback text is displayed
      expect(screen.getByText('Great job! Your form is excellent')).toBeInTheDocument();
      
      // Check the correct visual style is applied
      const feedbackContainer = screen.getByRole('region', { name: /feedback/i }) || screen.getByTestId('form-check-feedback');
      expect(feedbackContainer).toBeInTheDocument();
      expect(feedbackContainer).toHaveAttribute('aria-live', 'polite');
      
      // Verify success indicator is visible
      const successIndicator = screen.getByRole('img', { name: /success/i }) || screen.getByLabelText('Success');
      expect(successIndicator).toBeInTheDocument();
    });
    
    it('renders the warning severity feedback correctly', async () => {
      const user = userEvent.setup();
      testRender(
        <FormCheckFeedback 
          feedback="Your form needs some adjustments" 
          score={75} 
          severity="warning" 
        />
      );
      
      // Check score is displayed with proper accessibility
      const scoreElement = screen.getByRole('status', { name: /score/i }) || screen.getByTestId('score');
      expect(scoreElement).toHaveTextContent('75%');
      
      // Check feedback text is displayed
      expect(screen.getByText('Your form needs some adjustments')).toBeInTheDocument();
      
      // Verify warning indicator is visible
      const warningIndicator = screen.getByRole('img', { name: /warning/i }) || screen.getByLabelText('Warning');
      expect(warningIndicator).toBeInTheDocument();
    });
    
    it('renders the error severity feedback correctly', async () => {
      const user = userEvent.setup();
      testRender(
        <FormCheckFeedback 
          feedback="Your form has serious issues that need correction" 
          score={45} 
          severity="error" 
        />
      );
      
      // Check score is displayed with proper accessibility
      const scoreElement = screen.getByRole('status', { name: /score/i }) || screen.getByTestId('score');
      expect(scoreElement).toHaveTextContent('45%');
      
      // Check feedback text is displayed
      expect(screen.getByText('Your form has serious issues that need correction')).toBeInTheDocument();
      
      // Verify error indicator is visible
      const errorIndicator = screen.getByRole('img', { name: /error/i }) || screen.getByLabelText('Error');
      expect(errorIndicator).toBeInTheDocument();
    });
    
    it('applies proper ARIA attributes for accessibility', async () => {
      const user = userEvent.setup();
      testRender(
        <FormCheckFeedback 
          feedback="Feedback message with accessibility" 
          score={65} 
          severity="warning" 
        />
      );
      
      // Verify appropriate ARIA attributes for screen readers
      const feedbackContainer = screen.getByRole('region', { name: /feedback/i }) || screen.getByTestId('form-check-feedback');
      expect(feedbackContainer).toHaveAttribute('aria-live', 'polite');
      
      // Score should be a status to announce changes
      const scoreElement = screen.getByRole('status', { name: /score/i }) || screen.getByTestId('score');
      expect(scoreElement).toBeInTheDocument();
      
      // Warning icon should have appropriate label
      const warningIcon = screen.getByRole('img', { name: /warning/i }) || screen.getByLabelText('Warning');
      expect(warningIcon).toBeInTheDocument();
    });
  });

  // PART 2: useFormCheck Hook Tests
  describe('useFormCheck Hook', () => {
    it('analyzes a form check successfully', async () => {
      const user = userEvent.setup();
      testRender(<FormCheckAnalyzer />);
      
      // Fill in the form check ID
      await user.type(screen.getByLabelText('Form check ID'), '1');
      
      // Click analyze button
      await user.click(screen.getByRole('button', { name: /analyze form check/i }));
      
      // Should show loading state
      expect(screen.getByRole('status', { name: /analyzing form check/i })).toBeInTheDocument();
      
      // Wait for analysis to complete
      await waitFor(() => {
        expect(screen.getByRole('region', { name: /form check result/i })).toBeInTheDocument();
      });
      
      // Check the analysis results are displayed
      const resultRegion = screen.getByRole('region', { name: /form check result/i });
      expect(within(resultRegion).getByText(/squat form check/i)).toBeInTheDocument();
      expect(within(resultRegion).getByText(/status: analyzed/i)).toBeInTheDocument();
      expect(within(resultRegion).getByText(/score: 85/i)).toBeInTheDocument();
      expect(within(resultRegion).getByText(/great form! keep your back straight/i)).toBeInTheDocument();
    });
    
    it('handles analysis errors gracefully', async () => {
      // Override server response for this test
      server.use(
        rest.post('/api/form-checks/:id/analyze', (_req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ message: 'Analysis failed due to server error' })
          );
        })
      );
      
      const user = userEvent.setup();
      testRender(<FormCheckAnalyzer />);
      
      // Fill in the form check ID
      await user.type(screen.getByLabelText('Form check ID'), '1');
      
      // Click analyze button
      await user.click(screen.getByRole('button', { name: /analyze form check/i }));
      
      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByRole('alert', { name: /analysis error/i })).toBeInTheDocument();
      });
      
      // Check error message is displayed correctly
      expect(screen.getByRole('alert')).toHaveTextContent(/error/i);
    });
    
    it('fetches an existing form check', async () => {
      const user = userEvent.setup();
      testRender(<FormCheckAnalyzer />);
      
      // Fill in the form check ID
      await user.type(screen.getByLabelText('Form check ID'), '2');
      
      // Click fetch button
      await user.click(screen.getByRole('button', { name: /fetch form check/i }));
      
      // Wait for fetch to complete
      await waitFor(() => {
        expect(screen.getByRole('region', { name: /form check result/i })).toBeInTheDocument();
      });
      
      // Check the form check data is displayed
      const resultRegion = screen.getByRole('region', { name: /form check result/i });
      expect(within(resultRegion).getByText(/deadlift form check/i)).toBeInTheDocument();
      expect(within(resultRegion).getByText(/status: completed/i)).toBeInTheDocument();
      expect(within(resultRegion).getByText(/score: 78/i)).toBeInTheDocument();
      expect(within(resultRegion).getByText(/watch your back angle/i)).toBeInTheDocument();
    });
    
    it('handles fetch errors gracefully', async () => {
      // Override server response for this test
      server.use(
        rest.get('/api/form-checks/:id', (_req, res, ctx) => {
          return res(
            ctx.status(404),
            ctx.json({ message: 'Form check not found', code: 'NOT_FOUND' })
          );
        })
      );
      
      const user = userEvent.setup();
      testRender(<FormCheckAnalyzer />);
      
      // Fill in the form check ID
      await user.type(screen.getByLabelText('Form check ID'), 'non-existent');
      
      // Click fetch button
      await user.click(screen.getByRole('button', { name: /fetch form check/i }));
      
      // Wait for error to be displayed
      await waitFor(() => {
        expect(screen.getByRole('alert', { name: /analysis error/i })).toBeInTheDocument();
      });
      
      // Check error message is displayed correctly
      expect(screen.getByRole('alert')).toHaveTextContent(/error/i);
    });
    
    it('disables buttons during analysis', async () => {
      const user = userEvent.setup();
      testRender(<FormCheckAnalyzer />);
      
      // Fill in the form check ID
      await user.type(screen.getByLabelText('Form check ID'), '1');
      
      // Get buttons before click
      const analyzeButton = screen.getByRole('button', { name: /analyze form check/i });
      const fetchButton = screen.getByRole('button', { name: /fetch form check/i });
      
      // Click analyze button
      await user.click(analyzeButton);
      
      // Verify buttons are disabled during analysis
      expect(analyzeButton).toBeDisabled();
      expect(fetchButton).toBeDisabled();
      
      // Wait for analysis to complete
      await waitFor(() => {
        expect(screen.getByRole('region', { name: /form check result/i })).toBeInTheDocument();
      });
      
      // Verify buttons are enabled again
      expect(analyzeButton).not.toBeDisabled();
      expect(fetchButton).not.toBeDisabled();
    });
  });

  // PART 3: FormCheck Service Tests
  describe('formCheckService', () => {
    it('gets a form check by ID', async () => {
      const result = await formCheckService.getFormCheck('1');
      
      // Verify returned data
      expect(result).toEqual(expect.objectContaining({
        id: '1',
        exercise_type: 'squat',
        score: 85
      }));
    });
    
    it('creates a new form check', async () => {
      const formCheckData = {
        exercise_type: 'squat' as ExerciseType,
        video_url: 'https://example.com/new-video.mp4',
      };
      
      const result = await formCheckService.createFormCheck(formCheckData);
      
      // Verify created form check data
      expect(result).toEqual(expect.objectContaining({
        id: expect.any(String),
        exercise_type: 'squat',
        video_url: 'https://example.com/new-video.mp4',
        status: 'pending'
      }));
    });
    
    it('updates form check status', async () => {
      const newStatus = 'completed' as FormCheckStatus;
      
      const result = await formCheckService.updateFormCheckStatus('1', newStatus);
      
      // Verify status was updated
      expect(result).toEqual(expect.objectContaining({
        id: '1',
        status: 'completed'
      }));
    });
    
    it('analyzes a form check', async () => {
      const result = await formCheckService.analyze('1');
      
      // Verify analysis results
      expect(result).toEqual(expect.objectContaining({
        id: '1',
        status: 'analyzed',
        score: expect.any(Number),
        feedback: expect.any(String)
      }));
    });
    
    it('fetches form check history', async () => {
      const result = await formCheckService.getHistory();
      
      // Verify history is returned
      expect(result).toEqual(expect.arrayContaining([
        expect.objectContaining({ id: '1' }),
        expect.objectContaining({ id: '2' })
      ]));
      expect(result).toHaveLength(2);
    });
  });

  // PART 4: Redux Slice Tests
  describe('Form Check Redux Flow', () => {
    it('displays the correct number of form checks', async () => {
      const user = userEvent.setup();
      // Create a Redux store with preloaded state
      const store = configureStore({
        reducer: {
          formCheck: formCheckReducer
        },
        preloadedState: {
          formCheck: {
            formChecks: mockFormChecks,
            currentFormCheck: null,
            loading: false,
            error: null,
          },
        },
      });

      // Render the component with Redux store
      testRender(<FormCheckList />, { store });

      // Check that both form checks are displayed
      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);
      
      // Verify the content of the form checks
      expect(screen.getByTestId('form-check-1')).toHaveTextContent('squat');
      expect(screen.getByTestId('form-check-2')).toHaveTextContent('deadlift');
    });

    it('removes a form check when delete button is clicked', async () => {
      const user = userEvent.setup();
      // Create a Redux store with preloaded state
      const store = configureStore({
        reducer: {
          formCheck: formCheckReducer
        },
        preloadedState: {
          formCheck: {
            formChecks: mockFormChecks,
            currentFormCheck: null,
            loading: false,
            error: null,
          },
        },
      });

      // Render the component with Redux store
      testRender(<FormCheckList />, { store });

      // Verify initial state - 2 form checks
      const initialListItems = screen.getAllByRole('listitem');
      expect(initialListItems).toHaveLength(2);

      // Click the delete button for the first form check
      await user.click(screen.getByRole('button', { name: /delete squat form check/i }));

      // Check that only one form check remains
      await waitFor(() => {
        const updatedListItems = screen.getAllByRole('listitem');
        expect(updatedListItems).toHaveLength(1);
      });

      // Verify that the correct form check was deleted
      expect(screen.queryByTestId('form-check-1')).not.toBeInTheDocument();
      expect(screen.getByTestId('form-check-2')).toBeInTheDocument();
    });

    it('displays empty message when no form checks are available', async () => {
      const user = userEvent.setup();
      // Create a Redux store with empty form checks
      const store = configureStore({
        reducer: {
          formCheck: formCheckReducer
        },
        preloadedState: {
          formCheck: {
            formChecks: [],
            currentFormCheck: null,
            loading: false,
            error: null,
          },
        },
      });

      // Render the component with Redux store
      testRender(<FormCheckList />, { store });

      // Check that the empty message is displayed with proper accessibility
      const emptyState = screen.getByRole('status', { name: /no form checks/i });
      expect(emptyState).toBeInTheDocument();
      expect(emptyState).toHaveTextContent('No form checks found');
      expect(screen.queryByTestId('form-check-list')).not.toBeInTheDocument();
    });

    it('updates the list when form checks are added to the store', async () => {
      const user = userEvent.setup();
      // Create a Redux store with empty form checks
      const store = configureStore({
        reducer: {
          formCheck: formCheckReducer
        },
        preloadedState: {
          formCheck: {
            formChecks: [],
            currentFormCheck: null,
            loading: false,
            error: null,
          },
        },
      });

      // Render the component with Redux store
      testRender(<FormCheckList />, { store });

      // Check initial empty state
      expect(screen.getByRole('status', { name: /no form checks/i })).toBeInTheDocument();

      // Dispatch action to set form checks
      store.dispatch(setFormChecks(mockFormChecks));

      // Verify list now shows items
      await waitFor(() => {
        expect(screen.queryByRole('status', { name: /no form checks/i })).not.toBeInTheDocument();
        const listItems = screen.getAllByRole('listitem');
        expect(listItems).toHaveLength(2);
      });
    });

    it('shows loading state while fetching form checks', async () => {
      const user = userEvent.setup();
      // Create a Redux store with loading state
      const store = configureStore({
        reducer: {
          formCheck: formCheckReducer
        },
        preloadedState: {
          formCheck: {
            formChecks: [],
            currentFormCheck: null,
            loading: true,
            error: null,
          },
        },
      });

      // Render the component with Redux store
      testRender(<FormCheckList />, { store });

      // Verify loading state is displayed with proper accessibility
      const loadingElement = screen.getByRole('status', { name: /loading form checks/i });
      expect(loadingElement).toBeInTheDocument();
      expect(loadingElement).toHaveTextContent('Loading');

      // Update state to finished loading
      store.dispatch(setFormChecks(mockFormChecks));

      // Verify loading state is removed and content is displayed
      await waitFor(() => {
        expect(screen.queryByRole('status', { name: /loading form checks/i })).not.toBeInTheDocument();
        expect(screen.getAllByRole('listitem')).toHaveLength(2);
      });
    });

    it('shows error state when fetch fails', async () => {
      const user = userEvent.setup();
      // Create a Redux store with error state
      const store = configureStore({
        reducer: {
          formCheck: formCheckReducer
        },
        preloadedState: {
          formCheck: {
            formChecks: [],
            currentFormCheck: null,
            loading: false,
            error: 'Failed to fetch form checks',
          },
        },
      });

      // Render the component with Redux store
      testRender(<FormCheckList />, { store });

      // Verify error state is displayed with proper accessibility
      const errorElement = screen.getByRole('alert');
      expect(errorElement).toBeInTheDocument();
      expect(errorElement).toHaveTextContent('Error: Failed to fetch form checks');
    });
  });
}); 