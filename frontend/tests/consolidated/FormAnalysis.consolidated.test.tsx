import React from 'react';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { testRender } from '../../test-utils';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { FormAnalysis } from '../../components/form/FormAnalysis';
import { FormFeedback } from '../../components/FormFeedback';
import { FormValidationResult } from '../../types/formValidation';
import { FormAnalysisResult, FormAnalysisRequest } from '../../types/formAnalysis';
import { formAnalysisService } from '../../services/formAnalysisService';
import { useFormAnalysis } from '../../hooks/useFormAnalysis';
import { FormBuilder } from '../../components/form/FormBuilder';
import { useFormBuilder } from '../../hooks/useFormBuilder';
import { FormField } from '../../types/formBuilder';
import { apiService } from '../../services/apiService';
import { EventEmitter } from 'events';

// Set up MSW server for API mocking
const server = setupServer(
  // Form analysis endpoints
  rest.post('/api/form-analysis/analyze', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        confidence: 0.85,
        isReliable: true,
        keypoints: [{ name: 'nose', x: 100, y: 100, score: 0.9 }],
        angles: {
          leftKnee: { value: 90, confidence: 0.9 },
          rightKnee: { value: 92, confidence: 0.85 }
        },
        feedback: [{ message: 'Good form', confidence: 0.9, type: 'success' }],
        timestamp: Date.now(),
        videoUrl: 'test-url'
      })
    );
  }),
  
  rest.get('/api/form-analysis/history', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([{
        id: '123',
        confidence: 0.85,
        isReliable: true,
        keypoints: [{ name: 'nose', x: 100, y: 100, score: 0.9 }],
        angles: {
          leftKnee: { value: 90, confidence: 0.9 },
          rightKnee: { value: 92, confidence: 0.85 }
        },
        feedback: [{ message: 'Good form', confidence: 0.9, type: 'success' }],
        timestamp: Date.now(),
        videoUrl: 'test-url'
      }])
    );
  }),
  
  // Form validation endpoints
  rest.post('/api/form/validate', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        isValid: true,
        feedback: [
          { isValid: true, message: 'Good form' },
          { isValid: false, message: 'Keep knees aligned' }
        ],
        confidence: 0.85,
        repetitionCount: 5,
        phase: 'middle'
      })
    );
  }),
  
  // Form builder endpoints
  rest.get('/api/form/fields', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json([
        { 
          id: 'name', 
          label: 'Name', 
          type: 'text', 
          required: true,
          validationRules: [
            { type: 'required', message: 'Name is required' }
          ],
          value: ''
        },
        {
          id: 'email',
          label: 'Email',
          type: 'email',
          required: true,
          validationRules: [
            { type: 'required', message: 'Email is required' },
            { type: 'pattern', pattern: '^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{2,4}$', message: 'Invalid email format' }
          ],
          value: ''
        }
      ])
    );
  }),
  
  rest.post('/api/form/submit', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({ success: true })
    );
  })
);

// Start server before tests
beforeAll(() => server.listen());
// Reset handlers after each test
afterEach(() => server.resetHandlers());
// Close server after all tests
afterAll(() => server.close());

// Mock implementations that will be reused across tests

// Helper for creating a test FormAnalysisResult
const createFormAnalysisResult = (overrides = {}) => ({
  confidence: 0.8,
  isReliable: true,
  keypoints: [{ x: 100, y: 100, score: 0.9, name: 'nose' }],
  angles: {
    leftKnee: { value: 90, confidence: 0.9 },
    rightKnee: { value: 92, confidence: 0.85 }
  },
  feedback: [{ message: 'Good form', confidence: 0.9, type: 'success' }],
  timestamp: Date.now(),
  videoUrl: 'test-url',
  ...overrides
});

// Mock for ExerciseFormAnalysis component
jest.mock('../../components/exercise/ExerciseFormAnalysis', () => ({
  ExerciseFormAnalysis: jest.fn(({ exerciseType, onAnalysisComplete }) => (
    <div 
      data-testid="exercise-form-analysis" 
      data-exercise={exerciseType}
      role="region"
      aria-label="Exercise form analysis"
    >
      <button 
        onClick={() => onAnalysisComplete({ 
          score: 85, 
          feedback: ['Good depth', 'Keep core tight'], 
          videoUrl: 'mock-video-url' 
        })}
        aria-label="Complete analysis"
      >
        Complete Analysis
      </button>
      <button 
        data-testid="fail-analysis-btn"
        onClick={() => onAnalysisComplete(null)}
        aria-label="Fail analysis"
      >
        Fail Analysis
      </button>
    </div>
  ))
}));

// FormAnalysis Component Tests
describe('FormAnalysis Component', () => {
  it('renders the form analysis interface', async () => {
    testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    // Verify the component renders with its main elements
    expect(screen.getByRole('region', { name: /exercise form analysis/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /complete analysis/i })).toBeInTheDocument();
  });

  it('allows selecting different exercise types', async () => {
    const { user } = testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    // Find and click the exercise selector (assuming it's in the component)
    const exerciseSelector = screen.getByRole('combobox', { name: /exercise type/i });
    await user.selectOptions(exerciseSelector, 'squat');
    
    // Verify the exercise type was updated in the analysis component
    const formAnalysis = screen.getByRole('region', { name: /exercise form analysis/i });
    expect(formAnalysis.getAttribute('data-exercise')).toBe('squat');
  });

  it('handles analysis completion correctly and displays results', async () => {
    const { user } = testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    // Find and click the complete analysis button
    const completeButton = screen.getByRole('button', { name: /complete analysis/i });
    await user.click(completeButton);
    
    // Results should be displayed with the correct score and feedback
    await waitFor(() => {
      expect(screen.getByTestId('results-display')).toBeInTheDocument();
    });
    
    const resultsDisplay = screen.getByTestId('results-display');
    expect(resultsDisplay.getAttribute('data-score')).toBe('85');
    
    // Check feedback items
    const feedbackItems = screen.getAllByTestId('feedback-item');
    expect(feedbackItems).toHaveLength(2);
    expect(screen.getByText('Good depth')).toBeInTheDocument();
    expect(screen.getByText('Keep core tight')).toBeInTheDocument();
  });

  it('handles failed analysis gracefully', async () => {
    const { user } = testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    // Click the button that returns null results
    const failButton = screen.getByRole('button', { name: /fail analysis/i });
    await user.click(failButton);
    
    // The component should handle null results gracefully
    await waitFor(() => {
      // FormAnalysis component should still be visible, not results
      expect(screen.queryByTestId('results-display')).not.toBeInTheDocument();
      expect(screen.getByRole('region', { name: /exercise form analysis/i })).toBeInTheDocument();
    });
    
    // Error message should be displayed to the user
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/unable to complete analysis/i)).toBeInTheDocument();
  });
  
  it('allows retrying after a failed analysis', async () => {
    const { user } = testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    // Trigger a failed analysis
    const failButton = screen.getByRole('button', { name: /fail analysis/i });
    await user.click(failButton);
    
    // Find and click retry button
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });
    
    await user.click(screen.getByRole('button', { name: /try again/i }));
    
    // Verify we're back to the analysis interface
    expect(screen.getByRole('region', { name: /exercise form analysis/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /complete analysis/i })).toBeInTheDocument();
  });

  it('shows loading state during analysis', async () => {
    // Override mock to simulate delayed response
    const originalImplementation = require('../../components/exercise/ExerciseFormAnalysis').ExerciseFormAnalysis;
    require('../../components/exercise/ExerciseFormAnalysis').ExerciseFormAnalysis.mockImplementationOnce(
      ({ exerciseType, onAnalysisComplete }) => (
        <div data-testid="exercise-form-analysis" data-exercise={exerciseType} role="region" aria-label="Exercise form analysis">
          <button 
            onClick={async () => {
              // Show loading state for a brief moment
              await new Promise(resolve => setTimeout(resolve, 100));
              onAnalysisComplete({ 
                score: 85, 
                feedback: ['Good depth'], 
                videoUrl: 'mock-video-url' 
              });
            }}
            aria-label="Complete analysis with loading"
          >
            Complete Analysis
          </button>
        </div>
      )
    );
    
    const { user } = testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    const completeButton = screen.getByRole('button', { name: /complete analysis with loading/i });
    await user.click(completeButton);
    
    // Check for loading state
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    
    // Wait for results to appear after loading
    await waitFor(() => {
      expect(screen.getByTestId('results-display')).toBeInTheDocument();
    });
  });
  
  it('saves and shares analysis results', async () => {
    const { user } = testRender(<FormAnalysis />, { useMemoryRouter: true });
    
    // Complete analysis
    const completeButton = screen.getByRole('button', { name: /complete analysis/i });
    await user.click(completeButton);
    
    // Wait for results
    await waitFor(() => {
      expect(screen.getByTestId('results-display')).toBeInTheDocument();
    });
    
    // Find and click save button
    const saveButton = screen.getByRole('button', { name: /save results/i });
    await user.click(saveButton);
    
    // Verify success message
    await waitFor(() => {
      expect(screen.getByText(/results saved successfully/i)).toBeInTheDocument();
    });
    
    // Find and click share button
    const shareButton = screen.getByRole('button', { name: /share results/i });
    await user.click(shareButton);
    
    // Verify share dialog appears
    expect(screen.getByRole('dialog', { name: /share analysis results/i })).toBeInTheDocument();
  });
});

// FormFeedback Component Tests
describe('FormFeedback Component', () => {
  const mockProps = {
    feedback: [
      { isValid: true, message: 'Good form' },
      { isValid: false, message: 'Keep knees aligned' }
    ] as FormValidationResult[],
    confidence: 0.85,
    repetitionCount: 5,
    phase: 'middle' as const
  };

  it('displays feedback messages with appropriate visual indicators', async () => {
    testRender(<FormFeedback {...mockProps} />);
    
    // Find the feedback container
    const feedbackContainer = screen.getByRole('region', { name: /form feedback/i });
    expect(feedbackContainer).toBeInTheDocument();
    
    // Check feedback list is rendered correctly
    const feedbackList = screen.getByRole('list', { name: /feedback items/i });
    expect(feedbackList).toBeInTheDocument();
    
    // Check individual feedback items
    const feedbackItems = screen.getAllByRole('listitem');
    expect(feedbackItems).toHaveLength(2);
    
    // Positive feedback should have a success indicator
    const successItem = screen.getByText('Good form').closest('li');
    expect(successItem).toHaveAttribute('aria-details', 'success-feedback');
    
    // Negative feedback should have a warning indicator
    const warningItem = screen.getByText('Keep knees aligned').closest('li');
    expect(warningItem).toHaveAttribute('aria-details', 'warning-feedback');
  });

  it('displays exercise metrics in an accessible way', async () => {
    testRender(<FormFeedback {...mockProps} />);
    
    // Check metrics container
    const metricsSection = screen.getByRole('region', { name: /exercise metrics/i });
    expect(metricsSection).toBeInTheDocument();
    
    // Check individual metrics
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Middle')).toBeInTheDocument();
    
    // Labels should be associated with values
    expect(screen.getByLabelText(/confidence/i).textContent).toBe('85%');
    expect(screen.getByLabelText(/reps/i).textContent).toBe('5');
    expect(screen.getByLabelText(/phase/i).textContent).toBe('Middle');
  });

  it('handles empty feedback gracefully', async () => {
    const propsWithNoFeedback = {
      ...mockProps,
      feedback: []
    };
    testRender(<FormFeedback {...propsWithNoFeedback} />);
    
    // Should show a message when no feedback items
    expect(screen.getByText(/no feedback available/i)).toBeInTheDocument();
    
    // Metrics should still be displayed
    expect(screen.getByText('85%')).toBeInTheDocument();
  });
  
  it('allows interaction with feedback items for more details', async () => {
    const { user } = testRender(<FormFeedback {...mockProps} />);
    
    // Click on a feedback item to see more details
    const feedbackItem = screen.getByText('Keep knees aligned');
    await user.click(feedbackItem);
    
    // Should show a detailed explanation
    expect(screen.getByRole('dialog', { name: /feedback details/i })).toBeInTheDocument();
    expect(screen.getByText(/how to improve/i)).toBeInTheDocument();
    
    // Close the dialog
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);
    
    // Dialog should be closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

// FormBuilder Component Tests
describe('FormBuilder Component', () => {
  const mockFields: FormField[] = [
    {
      id: 'name',
      type: 'text',
      label: 'Name',
      placeholder: 'Enter your name',
      required: true
    },
    {
      id: 'email',
      type: 'email',
      label: 'Email',
      placeholder: 'Enter your email',
      required: true
    }
  ];

  const mockOnSubmit = jest.fn();

  // Reset mocks before each test
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders form fields with proper accessibility attributes', async () => {
    testRender(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Form should be accessible
    const form = screen.getByRole('form');
    expect(form).toBeInTheDocument();
    
    // Fields should have proper labels
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    
    // Required fields should be marked as required
    const nameInput = screen.getByLabelText(/name/i);
    expect(nameInput).toHaveAttribute('required');
    
    // Buttons should be accessible
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reset/i })).toBeInTheDocument();
  });

  it('allows users to input values and submit the form', async () => {
    const { user } = testRender(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Enter values into form fields
    const nameInput = screen.getByLabelText(/name/i);
    const emailInput = screen.getByLabelText(/email/i);
    
    await user.type(nameInput, 'John Doe');
    await user.type(emailInput, 'john@example.com');
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await user.click(submitButton);
    
    // Verify form was submitted with values
    expect(mockOnSubmit).toHaveBeenCalledTimes(1);
    expect(mockOnSubmit).toHaveBeenCalledWith(expect.objectContaining({
      name: 'John Doe',
      email: 'john@example.com'
    }));
  });

  it('displays validation errors for required fields', async () => {
    const { user } = testRender(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Submit without entering required fields
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await user.click(submitButton);
    
    // Check that error messages are displayed in an accessible way
    const errors = screen.getAllByRole('alert');
    expect(errors.length).toBeGreaterThan(0);
    
    // Error should be associated with the input field
    const nameInput = screen.getByLabelText(/name/i);
    const nameError = screen.getByText(/name is required/i);
    expect(nameError).toHaveAttribute('id', expect.stringContaining('error-name'));
    expect(nameInput).toHaveAttribute('aria-errormessage', expect.stringContaining('error-name'));
    
    // Focus should be moved to the first error field
    expect(document.activeElement).toBe(nameInput);
  });

  it('displays validation errors for invalid email format', async () => {
    const { user } = testRender(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Enter invalid email
    const nameInput = screen.getByLabelText(/name/i);
    const emailInput = screen.getByLabelText(/email/i);
    
    await user.type(nameInput, 'John Doe');
    await user.type(emailInput, 'invalid-email');
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /submit/i });
    await user.click(submitButton);
    
    // Check that email error message is displayed
    expect(screen.getByText(/invalid email format/i)).toBeInTheDocument();
  });

  it('resets the form when reset button is clicked', async () => {
    const { user } = testRender(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Enter values
    const nameInput = screen.getByLabelText(/name/i);
    const emailInput = screen.getByLabelText(/email/i);
    
    await user.type(nameInput, 'John Doe');
    await user.type(emailInput, 'john@example.com');
    
    // Click reset button
    const resetButton = screen.getByRole('button', { name: /reset/i });
    await user.click(resetButton);
    
    // Fields should be cleared
    expect(nameInput).toHaveValue('');
    expect(emailInput).toHaveValue('');
  });

  it('disables submit button while submitting', async () => {
    // Mock useFormBuilder to return isSubmitting as true
    jest.mock('../../hooks/useFormBuilder', () => ({
      useFormBuilder: () => ({
        values: {},
        errors: {},
        touched: {},
        handleChange: jest.fn(),
        handleBlur: jest.fn(),
        handleSubmit: jest.fn(),
        setFieldValue: jest.fn(),
        resetForm: jest.fn(),
        isSubmitting: true
      })
    }));
    
    testRender(<FormBuilder fields={mockFields} onSubmit={mockOnSubmit} />);
    
    // Submit button should be disabled
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeDisabled();
    
    // Loading indicator should be visible
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});

// useFormAnalysis Hook Tests
describe('useFormAnalysis Hook', () => {
  // Test component to help verify the hook behavior
  const FormAnalysisHookTest = () => {
    const { 
      isAnalyzing, 
      progress, 
      error, 
      videoFile, 
      analysisResults,
      startAnalysis,
      stopAnalysis,
      setVideo,
      setResults,
      reset
    } = useFormAnalysis();
    
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        setVideo(e.target.files[0]);
      }
    };
    
    return (
      <div role="main" aria-label="Form analysis test">
        <div>Analyzing: {isAnalyzing ? 'Yes' : 'No'}</div>
        <div role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
          Progress: {progress}%
        </div>
        
        {error && <div role="alert">Error: {error.message}</div>}
        
        {videoFile && <div>Video File: {videoFile.name}</div>}
        
        {analysisResults && (
          <div role="region" aria-label="Analysis results">
            <div>Score: {analysisResults.score}</div>
            <ul>
              {analysisResults.feedback.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        
        <input 
          type="file" 
          onChange={handleFileChange} 
          accept="video/*"
          aria-label="Upload video"
        />
        
        <button 
          onClick={() => startAnalysis(new File(['test'], 'test-video.mp4', { type: 'video/mp4' }))}
          disabled={isAnalyzing}
          aria-label="Start analysis"
        >
          Start Analysis
        </button>
        
        <button 
          onClick={stopAnalysis}
          disabled={!isAnalyzing}
          aria-label="Stop analysis"
        >
          Stop Analysis
        </button>
        
        <button 
          onClick={() => setResults({
            score: 85,
            feedback: ['Good form', 'Maintain knee alignment'],
            videoUrl: 'https://example.com/video.mp4'
          })}
          aria-label="Set results manually"
        >
          Set Results
        </button>
        
        <button 
          onClick={reset}
          aria-label="Reset analysis"
        >
          Reset
        </button>
      </div>
    );
  };
  
  it('allows uploading a video file for analysis', async () => {
    const { user } = testRender(<FormAnalysisHookTest />);
    
    // Upload a video file
    const fileInput = screen.getByLabelText(/upload video/i);
    const file = new File(['video content'], 'workout.mp4', { type: 'video/mp4' });
    await user.upload(fileInput, file);
    
    // Verify file was set
    expect(screen.getByText(/workout.mp4/i)).toBeInTheDocument();
  });
  
  it('handles starting and stopping analysis', async () => {
    const { user } = testRender(<FormAnalysisHookTest />);
    
    // Start analysis
    const startButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(startButton);
    
    // Verify analysis is in progress
    expect(screen.getByText(/analyzing: yes/i)).toBeInTheDocument();
    
    // Stop analysis
    const stopButton = screen.getByRole('button', { name: /stop analysis/i });
    await user.click(stopButton);
    
    // Verify analysis has stopped
    expect(screen.getByText(/analyzing: no/i)).toBeInTheDocument();
  });
  
  it('displays analysis results when available', async () => {
    const { user } = testRender(<FormAnalysisHookTest />);
    
    // Set results manually
    const setResultsButton = screen.getByRole('button', { name: /set results manually/i });
    await user.click(setResultsButton);
    
    // Verify results are displayed
    const resultsRegion = screen.getByRole('region', { name: /analysis results/i });
    expect(resultsRegion).toBeInTheDocument();
    expect(screen.getByText(/score: 85/i)).toBeInTheDocument();
    expect(screen.getByText(/good form/i)).toBeInTheDocument();
    expect(screen.getByText(/maintain knee alignment/i)).toBeInTheDocument();
  });
  
  it('resets the state when reset is called', async () => {
    const { user } = testRender(<FormAnalysisHookTest />);
    
    // Set results first
    const setResultsButton = screen.getByRole('button', { name: /set results manually/i });
    await user.click(setResultsButton);
    
    // Verify results are displayed
    expect(screen.getByText(/score: 85/i)).toBeInTheDocument();
    
    // Reset the state
    const resetButton = screen.getByRole('button', { name: /reset analysis/i });
    await user.click(resetButton);
    
    // Results should be removed
    expect(screen.queryByRole('region', { name: /analysis results/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/score: 85/i)).not.toBeInTheDocument();
  });
});

// useFormBuilder Hook Tests
describe('useFormBuilder Hook', () => {
  // Test component for the useFormBuilder hook
  const FormBuilderHookTest = () => {
    const initialFields: FormField[] = [
      { 
        id: 'name', 
        label: 'Name', 
        type: 'text', 
        required: true,
        validationRules: [
          { type: 'required', message: 'Name is required' }
        ],
        value: ''
      },
      {
        id: 'email',
        label: 'Email',
        type: 'email',
        required: true,
        validationRules: [
          { type: 'required', message: 'Email is required' },
          { type: 'pattern', pattern: '^[\\w-\\.]+@([\\w-]+\\.)+[\\w-]{2,4}$', message: 'Invalid email format' }
        ],
        value: ''
      }
    ];
    
    const { 
      formFields, 
      formValues, 
      errors, 
      handleChange, 
      validate, 
      resetForm 
    } = useFormBuilder(initialFields);
    
    const handleSubmit = (e: React.FormEvent) => {
      e.preventDefault();
      validate();
    };
    
    return (
      <form onSubmit={handleSubmit} role="form" aria-label="Form builder test">
        {formFields.map(field => (
          <div key={field.id}>
            <label htmlFor={field.id}>{field.label}</label>
            <input
              id={field.id}
              type={field.type}
              value={field.value}
              onChange={(e) => handleChange(field.id, e.target.value)}
              required={field.required}
              aria-invalid={!!errors[field.id]}
              aria-describedby={errors[field.id] ? `error-${field.id}` : undefined}
            />
            {errors[field.id] && (
              <span id={`error-${field.id}`} role="alert">{errors[field.id]}</span>
            )}
          </div>
        ))}
        <button type="submit" aria-label="Submit form">Submit</button>
        <button type="button" onClick={resetForm} aria-label="Reset form">Reset</button>
        <div data-testid="form-values">{JSON.stringify(formValues)}</div>
      </form>
    );
  };
  
  it('renders form fields correctly', async () => {
    testRender(<FormBuilderHookTest />);
    
    // Check that form fields are rendered
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    
    // Check submit and reset buttons
    expect(screen.getByRole('button', { name: /submit form/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /reset form/i })).toBeInTheDocument();
  });
  
  it('validates required fields on submission', async () => {
    const { user } = testRender(<FormBuilderHookTest />);
    
    // Submit the form without filling out required fields
    const submitButton = screen.getByRole('button', { name: /submit form/i });
    await user.click(submitButton);
    
    // Check that validation errors are displayed
    expect(screen.getByText(/name is required/i)).toBeInTheDocument();
    expect(screen.getByText(/email is required/i)).toBeInTheDocument();
    
    // Fields should be marked as invalid
    expect(screen.getByLabelText(/name/i)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
  });
  
  it('validates email format', async () => {
    const { user } = testRender(<FormBuilderHookTest />);
    
    // Fill out name field but enter invalid email
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/email/i), 'invalid-email');
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /submit form/i });
    await user.click(submitButton);
    
    // Email validation error should be displayed
    expect(screen.getByText(/invalid email format/i)).toBeInTheDocument();
  });
  
  it('updates form values when fields change', async () => {
    const { user } = testRender(<FormBuilderHookTest />);
    
    // Enter values into form fields
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/email/i), 'john@example.com');
    
    // Check form values are updated
    const formValues = JSON.parse(screen.getByTestId('form-values').textContent || '{}');
    expect(formValues).toEqual({
      name: 'John Doe',
      email: 'john@example.com'
    });
  });
  
  it('resets form to initial state', async () => {
    const { user } = testRender(<FormBuilderHookTest />);
    
    // Enter values into form fields
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/email/i), 'john@example.com');
    
    // Reset the form
    const resetButton = screen.getByRole('button', { name: /reset form/i });
    await user.click(resetButton);
    
    // Fields should be cleared
    expect(screen.getByLabelText(/name/i)).toHaveValue('');
    expect(screen.getByLabelText(/email/i)).toHaveValue('');
    
    // Form values should be reset
    const formValues = JSON.parse(screen.getByTestId('form-values').textContent || '{}');
    expect(formValues).toEqual({
      name: '',
      email: ''
    });
  });
  
  it('submits valid form data', async () => {
    const { user } = testRender(<FormBuilderHookTest />);
    
    // Enter valid values into form fields
    await user.type(screen.getByLabelText(/name/i), 'John Doe');
    await user.type(screen.getByLabelText(/email/i), 'john@example.com');
    
    // Submit the form
    const submitButton = screen.getByRole('button', { name: /submit form/i });
    await user.click(submitButton);
    
    // No validation errors should be displayed
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

// formAnalysisService Tests
describe('formAnalysisService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });
  
  // Simple component to test service integration
  const FormAnalysisServiceTest = () => {
    const [analysisState, setAnalysisState] = React.useState<{
      isInitialized: boolean;
      isAnalyzing: boolean;
      result: FormAnalysisResult | null;
      error: Error | null;
    }>({
      isInitialized: false,
      isAnalyzing: false,
      result: null,
      error: null
    });
    
    React.useEffect(() => {
      // Set up event listeners
      const handleAnalysis = (result: FormAnalysisResult) => {
        setAnalysisState(prev => ({ ...prev, result, isAnalyzing: false }));
      };
      
      const handleError = (error: Error) => {
        setAnalysisState(prev => ({ ...prev, error, isAnalyzing: false }));
      };
      
      formAnalysisService.on('analysis', handleAnalysis);
      formAnalysisService.on('error', handleError);
      
      return () => {
        // Clean up
        formAnalysisService.stopAnalysis();
      };
    }, []);
    
    const handleInitialize = async () => {
      try {
        await formAnalysisService.initialize();
        setAnalysisState(prev => ({ ...prev, isInitialized: true }));
      } catch (error) {
        setAnalysisState(prev => ({ ...prev, error: error as Error }));
      }
    };
    
    const handleStartAnalysis = async () => {
      try {
        setAnalysisState(prev => ({ ...prev, isAnalyzing: true, error: null }));
        const videoElement = document.createElement('video');
        await formAnalysisService.startAnalysis(videoElement);
      } catch (error) {
        setAnalysisState(prev => ({ ...prev, error: error as Error, isAnalyzing: false }));
      }
    };
    
    const handleStopAnalysis = () => {
      formAnalysisService.stopAnalysis();
      setAnalysisState(prev => ({ ...prev, isAnalyzing: false }));
    };
    
    const handleGetHistory = async () => {
      try {
        const history = await formAnalysisService.getAnalysisHistory();
        setAnalysisState(prev => ({ 
          ...prev, 
          result: history.length > 0 ? history[0] : null
        }));
      } catch (error) {
        setAnalysisState(prev => ({ ...prev, error: error as Error }));
      }
    };
    
    return (
      <div role="main" aria-label="Form analysis service test">
        <div aria-live="polite">
          {analysisState.isInitialized ? 'Initialized' : 'Not initialized'}
        </div>
        
        <div aria-live="polite">
          {analysisState.isAnalyzing ? 'Analyzing...' : 'Not analyzing'}
        </div>
        
        {analysisState.error && (
          <div role="alert">Error: {analysisState.error.message}</div>
        )}
        
        {analysisState.result && (
          <div role="region" aria-label="Analysis result">
            <div>Confidence: {analysisState.result.confidence}</div>
            <div>Is reliable: {analysisState.result.isReliable ? 'Yes' : 'No'}</div>
            <div>Keypoints: {analysisState.result.keypoints.length}</div>
            <div>Feedback: {analysisState.result.feedback.length}</div>
          </div>
        )}
        
        <button onClick={handleInitialize} aria-label="Initialize service">
          Initialize
        </button>
        
        <button 
          onClick={handleStartAnalysis} 
          disabled={!analysisState.isInitialized || analysisState.isAnalyzing}
          aria-label="Start analysis"
        >
          Start Analysis
        </button>
        
        <button 
          onClick={handleStopAnalysis}
          disabled={!analysisState.isAnalyzing}
          aria-label="Stop analysis"
        >
          Stop Analysis
        </button>
        
        <button onClick={handleGetHistory} aria-label="Get analysis history">
          Get History
        </button>
      </div>
    );
  };
  
  it('initializes and starts analysis', async () => {
    const { user } = testRender(<FormAnalysisServiceTest />);
    
    // Initialize the service
    const initButton = screen.getByRole('button', { name: /initialize service/i });
    await user.click(initButton);
    
    // Verify service is initialized
    await waitFor(() => {
      expect(screen.getByText('Initialized')).toBeInTheDocument();
    });
    
    // Start analysis
    const startButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(startButton);
    
    // Verify analysis is in progress
    expect(screen.getByText('Analyzing...')).toBeInTheDocument();
    
    // Wait for analysis to complete
    await waitFor(() => {
      expect(screen.getByText('Not analyzing')).toBeInTheDocument();
    });
    
    // Results should be displayed
    const resultRegion = screen.getByRole('region', { name: /analysis result/i });
    expect(resultRegion).toBeInTheDocument();
    expect(screen.getByText(/confidence:/i)).toBeInTheDocument();
  });
  
  it('handles analysis errors gracefully', async () => {
    // Mock the service to throw an error
    jest.spyOn(formAnalysisService, 'startAnalysis').mockRejectedValueOnce(new Error('Analysis failed'));
    
    const { user } = testRender(<FormAnalysisServiceTest />);
    
    // Initialize the service
    const initButton = screen.getByRole('button', { name: /initialize service/i });
    await user.click(initButton);
    
    // Verify service is initialized
    await waitFor(() => {
      expect(screen.getByText('Initialized')).toBeInTheDocument();
    });
    
    // Start analysis
    const startButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(startButton);
    
    // Verify error is displayed
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Error: Analysis failed');
    });
  });
  
  it('fetches analysis history', async () => {
    // Mock the getAnalysisHistory method
    const mockResult = createFormAnalysisResult();
    jest.spyOn(formAnalysisService, 'getAnalysisHistory').mockResolvedValueOnce([mockResult]);
    
    const { user } = testRender(<FormAnalysisServiceTest />);
    
    // Get history
    const historyButton = screen.getByRole('button', { name: /get analysis history/i });
    await user.click(historyButton);
    
    // Verify history is displayed
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /analysis result/i })).toBeInTheDocument();
    });
    
    // Check specific values
    expect(screen.getByText(`Confidence: ${mockResult.confidence}`)).toBeInTheDocument();
    expect(screen.getByText(`Is reliable: Yes`)).toBeInTheDocument();
  });
  
  it('allows stopping analysis', async () => {
    // Mock startAnalysis to not resolve immediately
    jest.spyOn(formAnalysisService, 'startAnalysis').mockImplementationOnce(async () => {
      // This will keep the analysis running until stopAnalysis is called
      return new Promise(resolve => {
        // The test will call stopAnalysis before this resolves
        setTimeout(resolve, 10000);
      });
    });
    
    const { user } = testRender(<FormAnalysisServiceTest />);
    
    // Initialize the service
    const initButton = screen.getByRole('button', { name: /initialize service/i });
    await user.click(initButton);
    
    // Verify service is initialized
    await waitFor(() => {
      expect(screen.getByText('Initialized')).toBeInTheDocument();
    });
    
    // Start analysis
    const startButton = screen.getByRole('button', { name: /start analysis/i });
    await user.click(startButton);
    
    // Verify analysis is in progress
    expect(screen.getByText('Analyzing...')).toBeInTheDocument();
    
    // Stop analysis
    const stopButton = screen.getByRole('button', { name: /stop analysis/i });
    await user.click(stopButton);
    
    // Verify analysis has stopped
    expect(screen.getByText('Not analyzing')).toBeInTheDocument();
  });
}); 