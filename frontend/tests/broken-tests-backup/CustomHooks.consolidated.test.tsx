import React, { useState, useEffect } from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { renderHook, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { BrowserRouter, Link, useNavigate } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { rest } from 'msw';
import { setupServer } from 'msw/node';

// Import hooks
import { useWorkout } from '../../src/hooks/useWorkout';
import { useFormCheck } from '../../src/hooks/useFormCheck';
import { useAuth } from '../../src/hooks/useAuth';
import { useApi } from '../../src/hooks/useApi';
import { useFormAnalysis } from '../../src/hooks/useFormAnalysis';
import { useFormBuilder } from '../../src/hooks/useFormBuilder';

// Import reducers and types
import authReducer from '../../src/store/slices/authSlice';
import workoutReducer, { WorkoutState } from '../../src/store/slices/workoutSlice';
import formCheckReducer from '../../src/store/slices/formCheckSlice';
import formAnalysisReducer, { FormAnalysisState } from '../../src/store/slices/formAnalysisSlice';
import { AppError, ErrorCode } from '../../src/utils/errorHandling';
import { testRender, setupMockServer } from '../utils/testRender';

// Common test utilities
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Create a server to handle API requests for all tests
const server = setupServer(
  // Add default handlers later as needed
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

// Common wrapper for Redux-connected hooks
interface WrapperProps {
  children: React.ReactNode;
  initialState?: any;
}

const TestWrapper: React.FC<WrapperProps> = ({ children, initialState = {} }) => {
  const store = configureStore({
    reducer: {
      auth: authReducer,
      workout: workoutReducer,
      formCheck: formCheckReducer,
      formAnalysis: formAnalysisReducer,
    },
    preloadedState: initialState
  });

  return (
    <BrowserRouter>
      <Provider store={store}>
        {children}
      </Provider>
    </BrowserRouter>
  );
};

// Mock file creator helper
const createMockFile = (name = 'test.mp4', mimeType = 'video/mp4') => {
  return new File(['dummy content'], name, { type: mimeType });
};

/**
 * Form Check Hook Tests
 */
describe('useFormCheck Hook', () => {
  // Define API handlers for Form Check tests
  const formCheckHandlers = [
    // GET /api/form-checks - Get all form checks
    rest.get('/api/form-checks', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json([
          {
            id: 1,
            user_id: 1,
            exercise_type: 'squat',
            video_url: 'https://example.com/video1.mp4',
            status: 'pending',
            created_at: '2023-01-01'
          },
          {
            id: 2,
            user_id: 1,
            exercise_type: 'deadlift',
            video_url: 'https://example.com/video2.mp4',
            status: 'pending',
            created_at: '2023-01-02'
          }
        ])
      );
    }),

    // GET /api/form-checks/:id - Get a specific form check
    rest.get('/api/form-checks/:id', (req, res, ctx) => {
      const { id } = req.params;
      return res(
        ctx.status(200),
        ctx.json({
          id: Number(id),
          user_id: 1,
          exercise_type: 'squat',
          video_url: `https://example.com/video${id}.mp4`,
          status: 'pending',
          created_at: '2023-01-03'
        })
      );
    }),

    // POST /api/form-checks/upload - Upload a new form check
    rest.post('/api/form-checks/upload', (req, res, ctx) => {
      return res(
        ctx.status(201),
        ctx.json({
          id: 123,
          user_id: 1,
          exercise_type: 'squat',
          video_url: 'https://example.com/video123.mp4',
          status: 'pending',
          created_at: '2023-01-03'
        })
      );
    }),

    // POST /api/form-checks/:id/analyze - Analyze a form check
    rest.post('/api/form-checks/:id/analyze', (req, res, ctx) => {
      const { id } = req.params;
      return res(
        ctx.status(200),
        ctx.json({
          id: Number(id),
          user_id: 1,
          exercise_type: 'squat',
          video_url: `https://example.com/video${id}.mp4`,
          status: 'analyzed',
          created_at: '2023-01-03',
          feedback: [
            { message: 'Good form', type: 'success' }
          ],
          score: 85
        })
      );
    }),

    // DELETE /api/form-checks/:id - Delete a form check
    rest.delete('/api/form-checks/:id', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json({ success: true })
      );
    }),
  ];

  // Set up the server with Form Check handlers for these tests
  beforeEach(() => {
    server.use(...formCheckHandlers);
  });

  // Create a demo component to test the hook
  const FormCheckTester: React.FC = () => {
    const { 
      formChecks, 
      currentFormCheck, 
      isLoading, 
      error, 
      fetchFormChecks, 
      fetchFormCheck, 
      submitFormCheck, 
      deleteFormCheckById, 
      analyzeFormCheck 
    } = useFormCheck();

    const [formCheckId, setFormCheckId] = useState<string>('');
    const [exerciseType, setExerciseType] = useState<string>('squat');
    const [file, setFile] = useState<File | null>(null);

    // Handler for file input change
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files[0]) {
        setFile(e.target.files[0]);
      }
    };

    return (
      <div>
        <h1>Form Check Tester</h1>
        
        {/* Status display */}
        {isLoading && <div data-testid="loading-indicator">Loading...</div>}
        {error && <div data-testid="error-message">Error: {error}</div>}
        
        {/* Actions */}
        <div>
          <button 
            onClick={() => fetchFormChecks()} 
            data-testid="fetch-all-button"
          >
            Fetch All Form Checks
          </button>

          <div>
            <input 
              type="text" 
              value={formCheckId} 
              onChange={(e) => setFormCheckId(e.target.value)} 
              placeholder="Form Check ID"
              data-testid="form-check-id-input"
              aria-label="Form Check ID"
            />
            <button 
              onClick={() => fetchFormCheck(formCheckId)} 
              data-testid="fetch-one-button"
            >
              Fetch Form Check
            </button>
          </div>

          <div>
            <select 
              value={exerciseType} 
              onChange={(e) => setExerciseType(e.target.value)}
              data-testid="exercise-type-select"
              aria-label="Exercise Type"
            >
              <option value="squat">Squat</option>
              <option value="deadlift">Deadlift</option>
              <option value="bench_press">Bench Press</option>
            </select>
            <input 
              type="file" 
              onChange={handleFileChange} 
              data-testid="file-input"
              aria-label="Upload video"
            />
            <button 
              onClick={() => file && submitFormCheck(file, exerciseType)} 
              disabled={!file}
              data-testid="submit-button"
            >
              Submit Form Check
            </button>
          </div>

          <button 
            onClick={() => formCheckId && analyzeFormCheck(formCheckId)} 
            data-testid="analyze-button"
          >
            Analyze Form Check
          </button>

          <button 
            onClick={() => formCheckId && deleteFormCheckById(Number(formCheckId))} 
            data-testid="delete-button"
          >
            Delete Form Check
          </button>
        </div>
        
        {/* Results Display */}
        {formChecks.length > 0 && (
          <div data-testid="form-checks-list" role="region" aria-label="Form Checks List">
            <h2>Form Checks</h2>
            <ul>
              {formChecks.map(check => (
                <li key={check.id} data-testid={`form-check-${check.id}`}>
                  {check.exercise_type} - Status: {check.status}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {currentFormCheck && (
          <div data-testid="current-form-check" role="region" aria-label="Current Form Check Details">
            <h2>Current Form Check</h2>
            <p>ID: {currentFormCheck.id}</p>
            <p>Exercise: {currentFormCheck.exercise_type}</p>
            <p>Status: {currentFormCheck.status}</p>
            {currentFormCheck.score && (
              <p>Score: {currentFormCheck.score}</p>
            )}
          </div>
        )}
      </div>
    );
  };

  it('should fetch and display all form checks', async () => {
    render(
      <TestWrapper>
        <FormCheckTester />
      </TestWrapper>
    );
    
    // Click the "Fetch All" button
    const fetchButton = screen.getByRole('button', { name: /fetch all form checks/i });
    await userEvent.click(fetchButton);
    
    // While loading, we should see the loading indicator
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // After loading, we should see the form checks list
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /form checks list/i })).toBeInTheDocument();
    });
    
    // Verify that both form checks are displayed
    expect(screen.getByTestId('form-check-1')).toBeInTheDocument();
    expect(screen.getByTestId('form-check-2')).toBeInTheDocument();
    
    // Verify the content of the form checks
    expect(screen.getByTestId('form-check-1')).toHaveTextContent('squat');
    expect(screen.getByTestId('form-check-2')).toHaveTextContent('deadlift');
  });

  it('should fetch a single form check by ID', async () => {
    render(
      <TestWrapper>
        <FormCheckTester />
      </TestWrapper>
    );
    
    // Enter a form check ID
    const input = screen.getByLabelText('Form Check ID');
    await userEvent.clear(input);
    await userEvent.type(input, '123');
    
    // Click the "Fetch One" button
    const fetchButton = screen.getByRole('button', { name: /fetch form check/i });
    await userEvent.click(fetchButton);
    
    // After loading, we should see the current form check details
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /current form check details/i })).toBeInTheDocument();
    });
    
    // Verify the content of the form check
    expect(screen.getByText('ID: 123')).toBeInTheDocument();
    expect(screen.getByText('Exercise: squat')).toBeInTheDocument();
  });

  it('should submit a new form check', async () => {
    // Mock the global File object
    const mockFile = createMockFile();
    
    render(
      <TestWrapper>
        <FormCheckTester />
      </TestWrapper>
    );
    
    // Select an exercise type
    const select = screen.getByLabelText('Exercise Type');
    await userEvent.selectOptions(select, 'squat');
    
    // Set up a mock file input event
    const fileInput = screen.getByLabelText('Upload video') as HTMLInputElement;
    Object.defineProperty(fileInput, 'files', {
      value: [mockFile]
    });
    
    // Trigger change event
    const changeEvent = new Event('change', { bubbles: true });
    fileInput.dispatchEvent(changeEvent);
    
    // Click the Submit button
    const submitButton = screen.getByRole('button', { name: /submit form check/i });
    await userEvent.click(submitButton);
    
    // After submission, we should see the current form check details
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /current form check details/i })).toBeInTheDocument();
    });
    
    // Verify the content of the submitted form check
    expect(screen.getByText('ID: 123')).toBeInTheDocument();
  });

  it('should analyze a form check', async () => {
    render(
      <TestWrapper>
        <FormCheckTester />
      </TestWrapper>
    );
    
    // Enter a form check ID
    const input = screen.getByLabelText('Form Check ID');
    await userEvent.clear(input);
    await userEvent.type(input, '123');
    
    // Click the Analyze button
    const analyzeButton = screen.getByRole('button', { name: /analyze form check/i });
    await userEvent.click(analyzeButton);
    
    // After analysis, we should see the updated form check with score
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /current form check details/i })).toBeInTheDocument();
      expect(screen.getByText('Status: analyzed')).toBeInTheDocument();
      expect(screen.getByText('Score: 85')).toBeInTheDocument();
    });
  });

  it('should delete a form check', async () => {
    render(
      <TestWrapper>
        <FormCheckTester />
      </TestWrapper>
    );
    
    // Fetch all form checks first
    const fetchButton = screen.getByRole('button', { name: /fetch all form checks/i });
    await userEvent.click(fetchButton);
    
    // Wait for the form checks to be displayed
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /form checks list/i })).toBeInTheDocument();
    });
    
    // Enter a form check ID to delete
    const input = screen.getByLabelText('Form Check ID');
    await userEvent.clear(input);
    await userEvent.type(input, '1');
    
    // Click the Delete button
    const deleteButton = screen.getByRole('button', { name: /delete form check/i });
    await userEvent.click(deleteButton);
    
    // After deletion, we should see a loading indicator during the operation
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // After the operation completes, the loading indicator should disappear
    await waitFor(() => {
      expect(screen.queryByTestId('loading-indicator')).not.toBeInTheDocument();
    });
  });
});

/**
 * Form Builder Hook Tests
 */
describe('useFormBuilder Hook', () => {
  // Demo component that uses the useFormBuilder hook
  const FormBuilderTester: React.FC = () => {
    const { 
      values, 
      setFieldValue, 
      errors, 
      isSubmitting, 
      handleChange, 
      handleBlur,
      handleSubmit, 
      resetForm
    } = useFormBuilder({
      name: '',
      email: '',
      age: '',
      terms: false
    });

    // Custom validation rules
    const validationRules: Record<string, (value: any) => string> = {
      name: (value: any): string => value ? '' : 'Name is required',
      email: (value: any): string => {
        if (!value) return 'Email is required';
        if (!/\S+@\S+\.\S+/.test(value)) return 'Email is invalid';
        return '';
      },
      age: (value: any): string => {
        if (!value) return 'Age is required';
        const ageNum = parseInt(value.toString(), 10);
        if (isNaN(ageNum)) return 'Age must be a number';
        if (ageNum < 18) return 'You must be at least 18 years old';
        if (ageNum > 120) return 'Please enter a valid age';
        return '';
      },
      terms: (value: any): string => value ? '' : 'You must accept the terms'
    };

    // Local state to track validation errors
    const [localErrors, setLocalErrors] = React.useState<Record<string, string>>({});

    // Function to validate a single field
    const validateField = (name: string): void => {
      const value = values[name];
      const error = validationRules[name](value);
      setLocalErrors(prev => ({ ...prev, [name]: error }));
    };

    // Function to validate all fields
    const validateAll = (): boolean => {
      const newErrors: Record<string, string> = {};
      let isValid = true;

      Object.keys(validationRules).forEach(field => {
        const value = values[field];
        const error = validationRules[field](value);
        newErrors[field] = error;
        if (error) isValid = false;
      });

      setLocalErrors(newErrors);
      return isValid;
    };

    // Custom submit handler
    const submitForm = async () => {
      if (!validateAll()) return;

      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Reset form on success
      resetForm();
      setLocalErrors({});
    };

    // Function to reset all values
    const resetValues = () => {
      resetForm();
      setLocalErrors({});
    };

    // Function to fill form with test data
    const fillForm = () => {
      setFieldValue('name', 'Test User');
      setFieldValue('email', 'test@example.com');
      setFieldValue('age', '30');
      setFieldValue('terms', true);
    };

    return (
      <div data-testid="form-builder-tester">
        <form 
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit(submitForm)();
          }}
          data-testid="form"
          aria-label="User Information Form"
        >
          <div>
            <label htmlFor="name">Name</label>
            <input
              id="name"
              name="name"
              value={values.name}
              onChange={handleChange}
              onBlur={(e) => {
                handleBlur(e);
                validateField('name');
              }}
              data-testid="name-input"
              aria-invalid={!!localErrors.name}
              aria-describedby={localErrors.name ? "name-error" : undefined}
            />
            {localErrors.name && (
              <div id="name-error" className="error" data-testid="name-error" role="alert">
                {localErrors.name}
              </div>
            )}
          </div>

          <div>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={values.email}
              onChange={handleChange}
              onBlur={(e) => {
                handleBlur(e);
                validateField('email');
              }}
              data-testid="email-input"
              aria-invalid={!!localErrors.email}
              aria-describedby={localErrors.email ? "email-error" : undefined}
            />
            {localErrors.email && (
              <div id="email-error" className="error" data-testid="email-error" role="alert">
                {localErrors.email}
              </div>
            )}
          </div>

          <div>
            <label htmlFor="age">Age</label>
            <input
              id="age"
              name="age"
              type="number"
              value={values.age}
              onChange={handleChange}
              onBlur={(e) => {
                handleBlur(e);
                validateField('age');
              }}
              data-testid="age-input"
              aria-invalid={!!localErrors.age}
              aria-describedby={localErrors.age ? "age-error" : undefined}
            />
            {localErrors.age && (
              <div id="age-error" className="error" data-testid="age-error" role="alert">
                {localErrors.age}
              </div>
            )}
          </div>

          <div>
            <label htmlFor="terms">
              <input
                id="terms"
                name="terms"
                type="checkbox"
                checked={!!values.terms}
                onChange={handleChange}
                data-testid="terms-checkbox"
                aria-invalid={!!localErrors.terms}
                aria-describedby={localErrors.terms ? "terms-error" : undefined}
              />
              I accept the terms and conditions
            </label>
            {localErrors.terms && (
              <div id="terms-error" className="error" data-testid="terms-error" role="alert">
                {localErrors.terms}
              </div>
            )}
          </div>

          <button 
            type="submit" 
            disabled={isSubmitting}
            data-testid="submit-button"
          >
            {isSubmitting ? 'Submitting...' : 'Submit'}
          </button>
        </form>

        {/* Form values display for testing */}
        <div className="form-values" data-testid="form-values">
          <h3>Current Form Values:</h3>
          <pre>{JSON.stringify(values, null, 2)}</pre>
        </div>

        {/* Reset and Fill buttons for testing */}
        <div className="test-controls">
          <button 
            onClick={resetValues}
            data-testid="reset-button"
          >
            Reset Form
          </button>
          <button 
            onClick={fillForm}
            data-testid="fill-button"
          >
            Fill Form
          </button>
          <button 
            onClick={validateAll}
            data-testid="validate-button"
          >
            Validate All
          </button>
        </div>
      </div>
    );
  };

  it('should initialize form with default values', () => {
    render(<FormBuilderTester />);
    
    // Form should be rendered with empty values
    expect(screen.getByLabelText(/name/i)).toHaveValue('');
    expect(screen.getByLabelText(/email/i)).toHaveValue('');
    expect(screen.getByLabelText(/age/i)).toHaveValue('');
    expect(screen.getByLabelText(/terms/i)).not.toBeChecked();
  });

  it('should update form values when user types', async () => {
    render(<FormBuilderTester />);
    
    // Type in the inputs
    await userEvent.type(screen.getByLabelText(/name/i), 'John Doe');
    await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
    await userEvent.type(screen.getByLabelText(/age/i), '25');
    
    // Check the checkbox
    await userEvent.click(screen.getByLabelText(/terms/i));
    
    // Verify values were updated
    expect(screen.getByLabelText(/name/i)).toHaveValue('John Doe');
    expect(screen.getByLabelText(/email/i)).toHaveValue('john@example.com');
    expect(screen.getByLabelText(/age/i)).toHaveValue(25);
    expect(screen.getByLabelText(/terms/i)).toBeChecked();
    
    // Check the JSON display
    const formValues = screen.getByTestId('form-values');
    expect(formValues).toHaveTextContent('John Doe');
    expect(formValues).toHaveTextContent('john@example.com');
    expect(formValues).toHaveTextContent('25');
    expect(formValues).toHaveTextContent('true');
  });

  it('should validate fields on blur', async () => {
    render(<FormBuilderTester />);
    
    // Focus and blur the name field without entering a value
    const nameInput = screen.getByLabelText(/name/i);
    await userEvent.click(nameInput);
    await userEvent.tab(); // Tab to next field to trigger blur
    
    // Validation error should appear
    expect(screen.getByTestId('name-error')).toHaveTextContent('Name is required');
    
    // Enter an invalid email and tab away
    const emailInput = screen.getByLabelText(/email/i);
    await userEvent.type(emailInput, 'invalid-email');
    await userEvent.tab();
    
    // Email validation error should appear
    expect(screen.getByTestId('email-error')).toHaveTextContent('Email is invalid');
    
    // Enter a valid email to clear the error
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, 'valid@example.com');
    await userEvent.tab();
    
    // Email error should be gone
    expect(screen.queryByTestId('email-error')).not.toBeInTheDocument();
  });

  it('should validate all fields when submitting', async () => {
    render(<FormBuilderTester />);
    
    // Try to submit without filling in any fields
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    // All validation errors should appear
    expect(screen.getByTestId('name-error')).toBeInTheDocument();
    expect(screen.getByTestId('email-error')).toBeInTheDocument();
    expect(screen.getByTestId('age-error')).toBeInTheDocument();
    expect(screen.getByTestId('terms-error')).toBeInTheDocument();
  });

  it('should validate against age requirements', async () => {
    render(<FormBuilderTester />);
    
    // Enter an age that's too young
    const ageInput = screen.getByLabelText(/age/i);
    await userEvent.type(ageInput, '16');
    await userEvent.tab();
    
    // Age validation error for too young
    expect(screen.getByTestId('age-error')).toHaveTextContent('You must be at least 18 years old');
    
    // Enter an age that's too old
    await userEvent.clear(ageInput);
    await userEvent.type(ageInput, '150');
    await userEvent.tab();
    
    // Age validation error for too old
    expect(screen.getByTestId('age-error')).toHaveTextContent('Please enter a valid age');
    
    // Enter a valid age
    await userEvent.clear(ageInput);
    await userEvent.type(ageInput, '30');
    await userEvent.tab();
    
    // Age error should be gone
    expect(screen.queryByTestId('age-error')).not.toBeInTheDocument();
  });

  it('should reset form values when reset button is clicked', async () => {
    render(<FormBuilderTester />);
    
    // Fill the form with the convenience button
    await userEvent.click(screen.getByRole('button', { name: /fill form/i }));
    
    // Verify form was filled
    expect(screen.getByLabelText(/name/i)).toHaveValue('Test User');
    expect(screen.getByLabelText(/email/i)).toHaveValue('test@example.com');
    expect(screen.getByLabelText(/age/i)).toHaveValue(30);
    expect(screen.getByLabelText(/terms/i)).toBeChecked();
    
    // Reset the form
    await userEvent.click(screen.getByRole('button', { name: /reset form/i }));
    
    // Verify form was reset
    expect(screen.getByLabelText(/name/i)).toHaveValue('');
    expect(screen.getByLabelText(/email/i)).toHaveValue('');
    expect(screen.getByLabelText(/age/i)).toHaveValue('');
    expect(screen.getByLabelText(/terms/i)).not.toBeChecked();
    
    // Errors should also be cleared
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('should submit successfully with valid data', async () => {
    render(<FormBuilderTester />);
    
    // Fill out the form
    await userEvent.type(screen.getByLabelText(/name/i), 'Complete User');
    await userEvent.type(screen.getByLabelText(/email/i), 'complete@example.com');
    await userEvent.type(screen.getByLabelText(/age/i), '35');
    await userEvent.click(screen.getByLabelText(/terms/i));
    
    // Submit the form
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
    
    // Verify submit button shows loading state
    expect(screen.getByRole('button', { name: /submitting/i })).toBeInTheDocument();
    
    // After submission completes, form should be reset
    await waitFor(() => {
      expect(screen.getByLabelText(/name/i)).toHaveValue('');
    });
    
    expect(screen.getByLabelText(/email/i)).toHaveValue('');
    expect(screen.getByLabelText(/age/i)).toHaveValue('');
    expect(screen.getByLabelText(/terms/i)).not.toBeChecked();
  });
});

/**
 * Auth Hook Tests
 */
describe('useAuth Hook', () => {
  // Define API handlers for Auth tests
  const authHandlers = [
    // POST /api/auth/login - Login endpoint
    rest.post('/api/auth/login', (req, res, ctx) => {
      const { email, password } = req.body as { email: string; password: string };
      
      // Simple validation
      if (email === 'test@example.com' && password === 'password') {
        return res(
          ctx.status(200),
          ctx.json({
            access_token: 'mock-access-token',
            refresh_token: 'mock-refresh-token',
            user: {
              id: '1',
              email: 'test@example.com',
              name: 'Test User',
              role: 'user',
              subscription_tier: 'free',
              subscription_end_date: null,
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z'
            }
          })
        );
      }
      
      return res(
        ctx.status(401),
        ctx.json({ message: 'Invalid credentials' })
      );
    }),
    
    // POST /api/auth/logout - Logout endpoint
    rest.post('/api/auth/logout', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json({ message: 'Logged out successfully' })
      );
    }),
  ];

  // Set up the server with Auth handlers for these tests
  beforeEach(() => {
    server.use(...authHandlers);
    localStorage.clear();
    sessionStorage.clear();
    mockNavigate.mockClear();
  });

  // Create a demo component to test the hook
  const AuthNavbar: React.FC = () => {
    const { user, isAuthenticated, isLoading, error, login, logout } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  
    const handleLogin = async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        await login(email, password);
        setIsLoginModalOpen(false);
        setEmail('');
        setPassword('');
      } catch (error) {
        console.error('Login failed:', error);
      }
    };
  
    const handleLogout = () => {
      logout();
    };
  
    return (
      <nav className="navbar" data-testid="auth-navbar" role="navigation">
        <div className="navbar-brand">
          <Link to="/">FormIQ</Link>
        </div>
        
        <div className="navbar-menu">
          {/* Always visible links */}
          <Link to="/" data-testid="home-link">Home</Link>
          
          {/* Links that should only be visible when authenticated */}
          {isAuthenticated && (
            <>
              <Link to="/dashboard" data-testid="dashboard-link">Dashboard</Link>
              <Link to="/form-analysis" data-testid="form-analysis-link">Form Analysis</Link>
              <Link to="/profile" data-testid="profile-link">Profile</Link>
            </>
          )}
        </div>
        
        <div className="navbar-auth">
          {isLoading ? (
            <div data-testid="loading-indicator" aria-busy="true">Loading...</div>
          ) : isAuthenticated ? (
            <div className="user-menu" data-testid="user-menu">
              <span data-testid="user-greeting">Hello, {user?.name}</span>
              <button onClick={handleLogout} data-testid="logout-button">Logout</button>
            </div>
          ) : (
            <>
              <button 
                onClick={() => setIsLoginModalOpen(true)} 
                data-testid="login-button"
              >
                Login
              </button>
            </>
          )}
        </div>
        
        {/* Simple login modal */}
        {isLoginModalOpen && (
          <div className="login-modal" data-testid="login-modal" role="dialog" aria-label="Login Form">
            <form onSubmit={handleLogin}>
              <h2>Login</h2>
              
              {error && (
                <div className="error-message" data-testid="error-message" role="alert">
                  {error}
                </div>
              )}
              
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  data-testid="email-input"
                  required
                  aria-required="true"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid="password-input"
                  required
                  aria-required="true"
                />
              </div>
              
              <div className="form-actions">
                <button type="button" onClick={() => setIsLoginModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" data-testid="submit-login-button">
                  Login
                </button>
              </div>
            </form>
          </div>
        )}
      </nav>
    );
  };

  it('should show login button when not authenticated', () => {
    render(
      <TestWrapper>
        <AuthNavbar />
      </TestWrapper>
    );
    
    // Should show login button
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    
    // Should not show authenticated-only links
    expect(screen.queryByTestId('dashboard-link')).not.toBeInTheDocument();
    expect(screen.queryByTestId('form-analysis-link')).not.toBeInTheDocument();
    expect(screen.queryByTestId('profile-link')).not.toBeInTheDocument();
    
    // Should not show user menu
    expect(screen.queryByTestId('user-menu')).not.toBeInTheDocument();
  });

  it('should open login modal when login button is clicked', async () => {
    render(
      <TestWrapper>
        <AuthNavbar />
      </TestWrapper>
    );
    
    // Click login button
    await userEvent.click(screen.getByRole('button', { name: /login/i }));
    
    // Modal should be open
    expect(screen.getByRole('dialog', { name: /login form/i })).toBeInTheDocument();
    
    // Form elements should be visible
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('should close login modal when cancel button is clicked', async () => {
    render(
      <TestWrapper>
        <AuthNavbar />
      </TestWrapper>
    );
    
    // Open login modal
    await userEvent.click(screen.getByRole('button', { name: /login/i }));
    expect(screen.getByRole('dialog', { name: /login form/i })).toBeInTheDocument();
    
    // Click cancel button
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));
    
    // Modal should be closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should show error message on failed login', async () => {
    render(
      <TestWrapper>
        <AuthNavbar />
      </TestWrapper>
    );
    
    // Open login modal
    await userEvent.click(screen.getByRole('button', { name: /login/i }));
    
    // Fill form with invalid credentials
    await userEvent.type(screen.getByLabelText(/email/i), 'wrong@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrongpassword');
    
    // Submit form
    await userEvent.click(screen.getByRole('button', { name: /^login$/i }));
    
    // Should show error message
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    
    // Modal should still be open
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('should login successfully with valid credentials', async () => {
    render(
      <TestWrapper>
        <AuthNavbar />
      </TestWrapper>
    );
    
    // Open login modal
    await userEvent.click(screen.getByRole('button', { name: /login/i }));
    
    // Fill form with valid credentials
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'password');
    
    // Submit form
    await userEvent.click(screen.getByRole('button', { name: /^login$/i }));
    
    // Loading indicator should be displayed
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // After loading, user should be logged in
    await waitFor(() => {
      expect(screen.getByTestId('user-menu')).toBeInTheDocument();
    });
    
    // User greeting should show name
    expect(screen.getByText(/hello, test user/i)).toBeInTheDocument();
    
    // Authenticated-only links should be visible
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/form analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/profile/i)).toBeInTheDocument();
    
    // Login modal should be closed
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should logout when logout button is clicked', async () => {
    // Create store with a preloaded authenticated user
    const preloadedState = {
      auth: {
        user: {
          id: '1',
          name: 'Test User',
          email: 'test@example.com',
          role: 'user'
        },
        isAuthenticated: true,
        isLoading: false,
        error: null
      }
    };
    
    render(
      <TestWrapper initialState={preloadedState}>
        <AuthNavbar />
      </TestWrapper>
    );
    
    // Verify user is logged in initially
    expect(screen.getByTestId('user-menu')).toBeInTheDocument();
    expect(screen.getByText(/hello, test user/i)).toBeInTheDocument();
    
    // Click logout button
    await userEvent.click(screen.getByRole('button', { name: /logout/i }));
    
    // Loading indicator should be displayed
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // After loading, user should be logged out
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
    });
    
    // User menu should be gone
    expect(screen.queryByTestId('user-menu')).not.toBeInTheDocument();
    
    // Authenticated-only links should be hidden
    expect(screen.queryByText(/dashboard/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/form analysis/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/profile/i)).not.toBeInTheDocument();
    
    // Navigation to home should occur
    expect(mockNavigate).toHaveBeenCalledWith('/');
  });
});

/**
 * API Hook Tests
 */
describe('useApi Hook', () => {
  const apiHandlers = [
    // GET success response
    rest.get('*/api/test-success', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json({ message: 'Success', data: { id: 1, name: 'Test Item' } })
      );
    }),
    
    // GET error response
    rest.get('*/api/test-error', (req, res, ctx) => {
      return res(
        ctx.status(500),
        ctx.json({ message: 'Server error' })
      );
    }),
    
    // POST success response
    rest.post('*/api/test-post', (req, res, ctx) => {
      const data = req.body as any;
      return res(
        ctx.status(201),
        ctx.json({ 
          message: 'Created successfully', 
          data: { id: 999, ...data } 
        })
      );
    }),
    
    // Network error simulation
    rest.get('*/api/test-network-error', (req, res) => {
      return res.networkError('Simulated network failure');
    })
  ];

  // Set up the server with API handlers for these tests
  beforeEach(() => {
    server.use(...apiHandlers);
  });

  // Demo component that uses the useApi hook
  const ApiDataFetcher: React.FC<{
    endpoint: string;
    method?: 'get' | 'post' | 'put' | 'delete';
    initialData?: any;
  }> = ({ endpoint, method = 'get', initialData = null }) => {
    const { data, loading, error, execute, reset } = useApi(endpoint, method);
    const [formData, setFormData] = useState(initialData || { name: '', description: '' });
    const [hasSubmitted, setHasSubmitted] = useState(false);
    
    // Handle input change
    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const { name, value } = e.target;
      setFormData(prev => ({ ...prev, [name]: value }));
    };
    
    // Handle form submission
    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        await execute({ data: formData });
        setHasSubmitted(true);
      } catch (error) {
        console.error('API error:', error);
      }
    };
    
    // Reset the form and API state
    const handleReset = () => {
      reset();
      setHasSubmitted(false);
    };
    
    return (
      <div data-testid="api-data-fetcher">
        <h2>API Data Fetcher</h2>
        
        {/* Status indicators */}
        {loading && <div data-testid="loading-state" role="status" aria-label="Loading">Loading data...</div>}
        {error && <div data-testid="error-state" role="alert">Error: {error}</div>}
        
        {/* Display data when available */}
        {data && !hasSubmitted && method === 'get' && (
          <div data-testid="data-display" role="region" aria-label="API Response Data">
            <h3>Response Data</h3>
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </div>
        )}
        
        {/* Form for POST/PUT methods */}
        {(method === 'post' || method === 'put') && !hasSubmitted && (
          <form onSubmit={handleSubmit} aria-label="API Data Form">
            <div>
              <label htmlFor="name">Name:</label>
              <input
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                data-testid="name-input"
                aria-label="Name"
                required
              />
            </div>
            
            <div>
              <label htmlFor="description">Description:</label>
              <input
                id="description"
                name="description"
                value={formData.description}
                onChange={handleChange}
                data-testid="description-input"
                aria-label="Description"
              />
            </div>
            
            <button type="submit" data-testid="submit-button">
              Submit Data
            </button>
          </form>
        )}
        
        {/* Success message after form submission */}
        {data && hasSubmitted && (
          <div data-testid="submission-result" role="region" aria-label="Submission Result">
            <h3>Submission Successful</h3>
            <p data-testid="result-message">{data.message}</p>
            <pre>{JSON.stringify(data.data, null, 2)}</pre>
          </div>
        )}
        
        {/* Actions */}
        <div className="api-actions">
          {method === 'get' && (
            <button 
              onClick={() => execute()} 
              data-testid="fetch-button"
            >
              Fetch Data
            </button>
          )}
          
          <button 
            onClick={handleReset} 
            data-testid="reset-button"
          >
            Reset
          </button>
        </div>
      </div>
    );
  };

  it('should show loading state when fetching data', async () => {
    render(<ApiDataFetcher endpoint="/api/test-success" />);
    
    // Click the fetch button
    await userEvent.click(screen.getByRole('button', { name: /fetch data/i }));
    
    // Should show loading state
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/loading/i);
  });

  it('should display fetched data on successful GET request', async () => {
    render(<ApiDataFetcher endpoint="/api/test-success" />);
    
    // Click the fetch button
    await userEvent.click(screen.getByRole('button', { name: /fetch data/i }));
    
    // Wait for data to be displayed
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /api response data/i })).toBeInTheDocument();
    });
    
    // Verify data content
    const dataDisplay = screen.getByRole('region', { name: /api response data/i });
    expect(dataDisplay).toHaveTextContent(/Success/i);
    expect(dataDisplay).toHaveTextContent(/Test Item/i);
  });

  it('should display error message on failed GET request', async () => {
    render(<ApiDataFetcher endpoint="/api/test-error" />);
    
    // Click the fetch button
    await userEvent.click(screen.getByRole('button', { name: /fetch data/i }));
    
    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    
    // Verify error message
    expect(screen.getByRole('alert')).toHaveTextContent(/error/i);
    expect(screen.getByRole('alert')).toHaveTextContent(/server error/i);
  });

  it('should handle form submission for POST requests', async () => {
    render(<ApiDataFetcher endpoint="/api/test-post" method="post" />);
    
    // Fill out the form
    await userEvent.type(screen.getByLabelText(/name/i), 'New Test Item');
    await userEvent.type(screen.getByLabelText(/description/i), 'This is a test description');
    
    // Submit the form
    await userEvent.click(screen.getByRole('button', { name: /submit data/i }));
    
    // Wait for submission result
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /submission result/i })).toBeInTheDocument();
    });
    
    // Verify submission result
    expect(screen.getByTestId('result-message')).toHaveTextContent(/created successfully/i);
    const resultDisplay = screen.getByRole('region', { name: /submission result/i });
    expect(resultDisplay).toHaveTextContent(/New Test Item/i);
    expect(resultDisplay).toHaveTextContent(/This is a test description/i);
  });

  it('should handle network errors gracefully', async () => {
    render(<ApiDataFetcher endpoint="/api/test-network-error" />);
    
    // Click the fetch button
    await userEvent.click(screen.getByRole('button', { name: /fetch data/i }));
    
    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
    
    // Verify error message indicates network issue
    expect(screen.getByRole('alert')).toHaveTextContent(/error/i);
    expect(screen.getByRole('alert')).toHaveTextContent(/network/i);
  });

  it('should reset data and state when reset button is clicked', async () => {
    render(<ApiDataFetcher endpoint="/api/test-success" />);
    
    // Fetch data first
    await userEvent.click(screen.getByRole('button', { name: /fetch data/i }));
    
    // Wait for data to be displayed
    await waitFor(() => {
      expect(screen.getByRole('region', { name: /api response data/i })).toBeInTheDocument();
    });
    
    // Click reset button
    await userEvent.click(screen.getByRole('button', { name: /reset/i }));
    
    // Data should no longer be displayed
    expect(screen.queryByRole('region', { name: /api response data/i })).not.toBeInTheDocument();
  });
});

/**
 * Form Analysis Hook Tests
 */
describe('useFormAnalysis Hook', () => {
  // Demo component that uses the useFormAnalysis hook
  const FormAnalysisTester: React.FC = () => {
    const {
      isAnalyzing,
      progress,
      error,
      videoFile,
      analysisResults,
      startAnalysis,
      stopAnalysis,
      updateProgress,
      setVideo,
      setResults,
      reset
    } = useFormAnalysis();

    const [progressValue, setProgressValue] = useState(0);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        setVideo(e.target.files[0]);
      }
    };

    const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setProgressValue(Number(e.target.value));
    };

    const handleUpdateProgress = () => {
      updateProgress(progressValue);
    };

    const handleSetResults = () => {
      setResults({
        score: 85,
        feedback: ['Good form', 'Keep your back straight'],
        videoUrl: 'https://example.com/analysis-video.mp4'
      });
    };

    return (
      <div data-testid="form-analysis-tester">
        <h2>Form Analysis Demo</h2>
        
        {/* Status display */}
        <div className="status" role="status" aria-live="polite">
          <p>Status: {isAnalyzing ? 'Analyzing' : 'Ready'}</p>
          {isAnalyzing && (
            <div role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
              Analysis Progress: {progress}%
            </div>
          )}
          {error && <div role="alert">Error: {error.message}</div>}
        </div>
        
        {/* Video file selection */}
        <div className="video-selection">
          <label htmlFor="video-file">Select Video:</label>
          <input 
            type="file" 
            id="video-file"
            onChange={handleFileChange}
            accept="video/mp4,video/x-m4v,video/*"
            aria-label="Video file selection"
          />
          {videoFile && (
            <p className="selected-file" data-testid="selected-file">
              Selected: {videoFile.name}
            </p>
          )}
        </div>
        
        {/* Analysis controls */}
        <div className="analysis-controls">
          <button 
            onClick={startAnalysis} 
            disabled={!videoFile || isAnalyzing}
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
            onClick={reset}
            aria-label="Reset"
          >
            Reset
          </button>
        </div>
        
        {/* Manual progress control (for testing) */}
        <div className="progress-control">
          <label htmlFor="progress-slider">Update Progress:</label>
          <input 
            type="range" 
            id="progress-slider"
            min="0" 
            max="100" 
            value={progressValue} 
            onChange={handleProgressChange}
            aria-label="Progress slider"
          />
          <span>{progressValue}%</span>
          <button 
            onClick={handleUpdateProgress}
            aria-label="Update progress"
          >
            Update Progress
          </button>
        </div>
        
        {/* Manual results (for testing) */}
        <div className="results-control">
          <button 
            onClick={handleSetResults}
            aria-label="Set example results"
          >
            Set Example Results
          </button>
        </div>
        
        {/* Analysis results */}
        {analysisResults && (
          <div className="analysis-results" role="region" aria-label="Analysis results">
            <h3>Analysis Results</h3>
            <p><strong>Score:</strong> <span data-testid="result-score">{analysisResults.score}</span>/100</p>
            <h4>Feedback:</h4>
            <ul aria-label="Feedback items" data-testid="feedback-list">
              {analysisResults.feedback.map((item, index) => (
                <li key={index} data-testid={`feedback-item-${index}`}>{item}</li>
              ))}
            </ul>
            <div>
              <p><strong>Video:</strong></p>
              <a 
                href={analysisResults.videoUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                data-testid="result-video-link"
              >
                View Analysis Video
              </a>
            </div>
          </div>
        )}
      </div>
    );
  };

  it('should allow selecting a video file', async () => {
    render(<FormAnalysisTester />);
    
    // Create a mock file
    const mockFile = createMockFile('workout.mp4', 'video/mp4');
    
    // Select the file input and simulate file selection
    const input = screen.getByLabelText(/video file selection/i);
    Object.defineProperty(input, 'files', {
      value: [mockFile]
    });
    
    // Trigger change event
    fireEvent.change(input);
    
    // Verify file was selected
    expect(screen.getByTestId('selected-file')).toBeInTheDocument();
    expect(screen.getByTestId('selected-file')).toHaveTextContent('workout.mp4');
  });

  it('should start analysis when button is clicked', async () => {
    render(<FormAnalysisTester />);
    
    // First, select a file
    const mockFile = createMockFile();
    const input = screen.getByLabelText(/video file selection/i);
    Object.defineProperty(input, 'files', {
      value: [mockFile]
    });
    fireEvent.change(input);
    
    // Start analysis
    await userEvent.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Verify analysis started
    expect(screen.getByRole('status')).toHaveTextContent(/analyzing/i);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  });

  it('should update progress during analysis', async () => {
    render(<FormAnalysisTester />);
    
    // First, select a file
    const mockFile = createMockFile();
    const input = screen.getByLabelText(/video file selection/i);
    Object.defineProperty(input, 'files', {
      value: [mockFile]
    });
    fireEvent.change(input);
    
    // Start analysis
    await userEvent.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Update progress using the slider
    const slider = screen.getByLabelText(/progress slider/i);
    fireEvent.change(slider, { target: { value: 50 } });
    await userEvent.click(screen.getByRole('button', { name: /update progress/i }));
    
    // Verify progress updated
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
    expect(screen.getByRole('progressbar')).toHaveTextContent('50%');
  });

  it('should stop analysis when stop button is clicked', async () => {
    render(<FormAnalysisTester />);
    
    // First, select a file
    const mockFile = createMockFile();
    const input = screen.getByLabelText(/video file selection/i);
    Object.defineProperty(input, 'files', {
      value: [mockFile]
    });
    fireEvent.change(input);
    
    // Start analysis
    await userEvent.click(screen.getByRole('button', { name: /start analysis/i }));
    
    // Stop analysis
    await userEvent.click(screen.getByRole('button', { name: /stop analysis/i }));
    
    // Verify analysis stopped
    expect(screen.getByRole('status')).toHaveTextContent(/ready/i);
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
  });

  it('should display analysis results', async () => {
    render(<FormAnalysisTester />);
    
    // Set example results
    await userEvent.click(screen.getByRole('button', { name: /set example results/i }));
    
    // Verify results are displayed
    expect(screen.getByRole('region', { name: /analysis results/i })).toBeInTheDocument();
    expect(screen.getByTestId('result-score')).toHaveTextContent('85');
    expect(screen.getByTestId('feedback-list')).toBeInTheDocument();
    expect(screen.getByTestId('feedback-item-0')).toHaveTextContent('Good form');
    expect(screen.getByTestId('feedback-item-1')).toHaveTextContent('Keep your back straight');
    expect(screen.getByTestId('result-video-link')).toHaveAttribute('href', 'https://example.com/analysis-video.mp4');
  });

  it('should reset the analysis state', async () => {
    render(<FormAnalysisTester />);
    
    // First, select a file
    const mockFile = createMockFile();
    const input = screen.getByLabelText(/video file selection/i);
    Object.defineProperty(input, 'files', {
      value: [mockFile]
    });
    fireEvent.change(input);
    
    // Set example results
    await userEvent.click(screen.getByRole('button', { name: /set example results/i }));
    
    // Verify we have file and results
    expect(screen.getByTestId('selected-file')).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /analysis results/i })).toBeInTheDocument();
    
    // Reset state
    await userEvent.click(screen.getByRole('button', { name: /reset/i }));
    
    // Verify state was reset
    expect(screen.queryByTestId('selected-file')).not.toBeInTheDocument();
    expect(screen.queryByRole('region', { name: /analysis results/i })).not.toBeInTheDocument();
  });
});

/**
 * Workout Hook Tests
 */
describe('useWorkout Hook', () => {
  // Define API handlers for Workout tests
  const workoutHandlers = [
    // GET /api/workouts - Get all workouts
    rest.get('/api/workouts', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json([
          {
            id: 1,
            user_id: 1,
            name: 'Full Body Workout',
            description: 'Complete full body routine',
            exercises: [
              { id: 101, name: 'Squats', sets: 3, reps: 10 },
              { id: 102, name: 'Push-ups', sets: 3, reps: 15 }
            ],
            created_at: '2023-01-01'
          },
          {
            id: 2,
            user_id: 1,
            name: 'Upper Body Focus',
            description: 'Chest, back and arms',
            exercises: [
              { id: 103, name: 'Bench Press', sets: 4, reps: 8 },
              { id: 104, name: 'Pull-ups', sets: 3, reps: 6 }
            ],
            created_at: '2023-01-02'
          }
        ])
      );
    }),

    // GET /api/workouts/:id - Get specific workout
    rest.get('/api/workouts/:id', (req, res, ctx) => {
      const { id } = req.params;
      return res(
        ctx.status(200),
        ctx.json({
          id: Number(id),
          user_id: 1,
          name: 'Targeted Workout',
          description: 'Custom workout details',
          exercises: [
            { id: 105, name: 'Deadlifts', sets: 3, reps: 5 },
            { id: 106, name: 'Shoulder Press', sets: 3, reps: 10 }
          ],
          created_at: '2023-01-03'
        })
      );
    }),

    // POST /api/workouts - Create new workout
    rest.post('/api/workouts', (req, res, ctx) => {
      const workoutData = req.body as any;
      return res(
        ctx.status(201),
        ctx.json({
          id: 999,
          user_id: 1,
          ...workoutData,
          created_at: '2023-01-05'
        })
      );
    }),

    // PUT /api/workouts/:id - Update workout
    rest.put('/api/workouts/:id', (req, res, ctx) => {
      const { id } = req.params;
      const updatedData = req.body as any;
      return res(
        ctx.status(200),
        ctx.json({
          id: Number(id),
          user_id: 1,
          ...updatedData,
          updated_at: '2023-01-06'
        })
      );
    }),

    // DELETE /api/workouts/:id - Delete workout
    rest.delete('/api/workouts/:id', (req, res, ctx) => {
      return res(
        ctx.status(200),
        ctx.json({ success: true })
      );
    }),

    // POST /api/workouts/:id/start - Start workout
    rest.post('/api/workouts/:id/start', (req, res, ctx) => {
      const { id } = req.params;
      return res(
        ctx.status(200),
        ctx.json({
          workout_id: Number(id),
          session_id: 'session-123',
          start_time: new Date().toISOString(),
          status: 'in_progress'
        })
      );
    }),

    // POST /api/workouts/:id/complete - Complete workout
    rest.post('/api/workouts/:id/complete', (req, res, ctx) => {
      const { id } = req.params;
      const { session_id } = req.body as any;
      return res(
        ctx.status(200),
        ctx.json({
          workout_id: Number(id),
          session_id,
          start_time: new Date(Date.now() - 3600000).toISOString(),
          end_time: new Date().toISOString(),
          status: 'completed',
          duration_seconds: 3600,
          calories_burned: 300
        })
      );
    })
  ];

  // Set up the server with Workout handlers for these tests
  beforeEach(() => {
    server.use(...workoutHandlers);
  });

  // Create a demo component to test the hook
  const WorkoutManager: React.FC = () => {
    const {
      workouts,
      currentWorkout,
      activeWorkoutSession,
      isLoading,
      error,
      fetchWorkouts,
      fetchWorkout,
      createWorkout,
      updateWorkout,
      deleteWorkout,
      startWorkout,
      completeWorkout
    } = useWorkout();

    const [workoutId, setWorkoutId] = useState<string>('');
    const [newWorkoutName, setNewWorkoutName] = useState<string>('');
    const [newWorkoutDesc, setNewWorkoutDesc] = useState<string>('');
    const [customExercises, setCustomExercises] = useState<any[]>([]);
    const [exerciseName, setExerciseName] = useState<string>('');
    const [exerciseSets, setExerciseSets] = useState<string>('3');
    const [exerciseReps, setExerciseReps] = useState<string>('10');

    // Add exercise to local state
    const addExercise = () => {
      if (exerciseName) {
        setCustomExercises([
          ...customExercises,
          {
            name: exerciseName,
            sets: parseInt(exerciseSets),
            reps: parseInt(exerciseReps)
          }
        ]);
        setExerciseName('');
        setExerciseSets('3');
        setExerciseReps('10');
      }
    };

    // Create a new workout
    const handleCreateWorkout = () => {
      if (newWorkoutName && customExercises.length > 0) {
        createWorkout({
          name: newWorkoutName,
          description: newWorkoutDesc,
          exercises: customExercises
        });
        setNewWorkoutName('');
        setNewWorkoutDesc('');
        setCustomExercises([]);
      }
    };

    // Update existing workout
    const handleUpdateWorkout = () => {
      if (currentWorkout && customExercises.length > 0) {
        updateWorkout(currentWorkout.id.toString(), {
          ...currentWorkout,
          name: newWorkoutName || currentWorkout.name,
          description: newWorkoutDesc || currentWorkout.description,
          exercises: customExercises
        });
      }
    };

    return (
      <div data-testid="workout-manager">
        <h1>Workout Manager</h1>
        
        {/* Status display */}
        {isLoading && <div data-testid="loading-indicator">Loading...</div>}
        {error && <div data-testid="error-message">Error: {error}</div>}
        
        {/* Fetch workouts section */}
        <section aria-labelledby="workouts-heading">
          <h2 id="workouts-heading">Your Workouts</h2>
          <button 
            onClick={() => fetchWorkouts()} 
            data-testid="fetch-workouts-btn"
          >
            Load All Workouts
          </button>
          
          {workouts.length > 0 && (
            <ul data-testid="workouts-list">
              {workouts.map(workout => (
                <li key={workout.id} data-testid={`workout-${workout.id}`}>
                  <h3>{workout.name}</h3>
                  <p>{workout.description}</p>
                  <p>Exercises: {workout.exercises.length}</p>
                  <button 
                    onClick={() => fetchWorkout(workout.id.toString())}
                    data-testid={`view-workout-${workout.id}`}
                  >
                    View Details
                  </button>
                  <button 
                    onClick={() => deleteWorkout(workout.id.toString())}
                    data-testid={`delete-workout-${workout.id}`}
                  >
                    Delete
                  </button>
                  <button 
                    onClick={() => startWorkout(workout.id.toString())}
                    data-testid={`start-workout-${workout.id}`}
                  >
                    Start Workout
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        
        {/* Individual workout details */}
        {currentWorkout && (
          <section aria-labelledby="current-workout-heading" data-testid="current-workout">
            <h2 id="current-workout-heading">Workout Details</h2>
            <div>
              <h3>{currentWorkout.name}</h3>
              <p>{currentWorkout.description}</p>
              
              <h4>Exercises:</h4>
              <ul>
                {currentWorkout.exercises.map((exercise, index) => (
                  <li key={index}>
                    {exercise.name} - {exercise.sets} sets x {exercise.reps} reps
                  </li>
                ))}
              </ul>
            </div>
          </section>
        )}
        
        {/* Active workout session */}
        {activeWorkoutSession && (
          <section aria-labelledby="active-session-heading" data-testid="active-session">
            <h2 id="active-session-heading">Active Workout Session</h2>
            <p>Status: {activeWorkoutSession.status}</p>
            <p>Started: {new Date(activeWorkoutSession.start_time).toLocaleTimeString()}</p>
            
            <button 
              onClick={() => completeWorkout(
                activeWorkoutSession.workout_id.toString(), 
                activeWorkoutSession.session_id
              )}
              data-testid="complete-workout-btn"
            >
              Complete Workout
            </button>
          </section>
        )}
        
        {/* Create new workout form */}
        <section aria-labelledby="create-workout-heading">
          <h2 id="create-workout-heading">
            {currentWorkout ? 'Update Workout' : 'Create New Workout'}
          </h2>
          
          <div>
            <label htmlFor="workout-name">Workout Name:</label>
            <input
              id="workout-name"
              type="text"
              value={newWorkoutName}
              onChange={(e) => setNewWorkoutName(e.target.value)}
              placeholder={currentWorkout?.name}
              data-testid="workout-name-input"
            />
          </div>
          
          <div>
            <label htmlFor="workout-desc">Description:</label>
            <input
              id="workout-desc"
              type="text"
              value={newWorkoutDesc}
              onChange={(e) => setNewWorkoutDesc(e.target.value)}
              placeholder={currentWorkout?.description}
              data-testid="workout-desc-input"
            />
          </div>
          
          {/* Exercises list */}
          <div>
            <h3>Exercises:</h3>
            <ul data-testid="custom-exercises-list">
              {customExercises.map((exercise, index) => (
                <li key={index} data-testid={`custom-exercise-${index}`}>
                  {exercise.name} - {exercise.sets} sets x {exercise.reps} reps
                </li>
              ))}
            </ul>
            
            {/* Add exercise form */}
            <div>
              <label htmlFor="exercise-name">Exercise Name:</label>
              <input
                id="exercise-name"
                type="text"
                value={exerciseName}
                onChange={(e) => setExerciseName(e.target.value)}
                data-testid="exercise-name-input"
              />
              
              <label htmlFor="exercise-sets">Sets:</label>
              <input
                id="exercise-sets"
                type="number"
                value={exerciseSets}
                onChange={(e) => setExerciseSets(e.target.value)}
                min="1"
                data-testid="exercise-sets-input"
              />
              
              <label htmlFor="exercise-reps">Reps:</label>
              <input
                id="exercise-reps"
                type="number"
                value={exerciseReps}
                onChange={(e) => setExerciseReps(e.target.value)}
                min="1"
                data-testid="exercise-reps-input"
              />
              
              <button 
                onClick={addExercise}
                disabled={!exerciseName}
                data-testid="add-exercise-btn"
              >
                Add Exercise
              </button>
            </div>
          </div>
          
          <button 
            onClick={currentWorkout ? handleUpdateWorkout : handleCreateWorkout}
            disabled={(!newWorkoutName && !currentWorkout) || customExercises.length === 0}
            data-testid="save-workout-btn"
          >
            {currentWorkout ? 'Update Workout' : 'Create Workout'}
          </button>
        </section>
      </div>
    );
  };

  it('should fetch and display all workouts', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // Click the load workouts button
    await userEvent.click(screen.getByTestId('fetch-workouts-btn'));
    
    // Loading indicator should appear temporarily
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for workouts to load
    await waitFor(() => {
      expect(screen.getByTestId('workouts-list')).toBeInTheDocument();
    });
    
    // Verify workouts are displayed
    expect(screen.getByTestId('workout-1')).toBeInTheDocument();
    expect(screen.getByTestId('workout-2')).toBeInTheDocument();
    
    // Verify workout content
    expect(screen.getByTestId('workout-1')).toHaveTextContent('Full Body Workout');
    expect(screen.getByTestId('workout-2')).toHaveTextContent('Upper Body Focus');
  });

  it('should fetch a specific workout by ID', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // First load all workouts
    await userEvent.click(screen.getByTestId('fetch-workouts-btn'));
    
    // Wait for workouts to load
    await waitFor(() => {
      expect(screen.getByTestId('workouts-list')).toBeInTheDocument();
    });
    
    // Click view details on the first workout
    await userEvent.click(screen.getByTestId('view-workout-1'));
    
    // Wait for current workout to load
    await waitFor(() => {
      expect(screen.getByTestId('current-workout')).toBeInTheDocument();
    });
    
    // Verify workout details
    expect(screen.getByTestId('current-workout')).toHaveTextContent('Targeted Workout');
    expect(screen.getByTestId('current-workout')).toHaveTextContent('Custom workout details');
    expect(screen.getByTestId('current-workout')).toHaveTextContent('Deadlifts');
    expect(screen.getByTestId('current-workout')).toHaveTextContent('Shoulder Press');
  });

  it('should create a new workout', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // Fill out the create workout form
    await userEvent.type(screen.getByTestId('workout-name-input'), 'Leg Day');
    await userEvent.type(screen.getByTestId('workout-desc-input'), 'Focus on lower body');
    
    // Add an exercise
    await userEvent.type(screen.getByTestId('exercise-name-input'), 'Squats');
    await userEvent.clear(screen.getByTestId('exercise-sets-input'));
    await userEvent.type(screen.getByTestId('exercise-sets-input'), '4');
    await userEvent.clear(screen.getByTestId('exercise-reps-input'));
    await userEvent.type(screen.getByTestId('exercise-reps-input'), '12');
    await userEvent.click(screen.getByTestId('add-exercise-btn'));
    
    // Add another exercise
    await userEvent.type(screen.getByTestId('exercise-name-input'), 'Lunges');
    await userEvent.click(screen.getByTestId('add-exercise-btn'));
    
    // Verify exercises were added to the list
    expect(screen.getByTestId('custom-exercise-0')).toHaveTextContent('Squats');
    expect(screen.getByTestId('custom-exercise-0')).toHaveTextContent('4 sets x 12 reps');
    expect(screen.getByTestId('custom-exercise-1')).toHaveTextContent('Lunges');
    
    // Create the workout
    await userEvent.click(screen.getByTestId('save-workout-btn'));
    
    // Loading indicator should appear
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for current workout to update
    await waitFor(() => {
      expect(screen.getByTestId('current-workout')).toBeInTheDocument();
    });
    
    // Verify the new workout details
    expect(screen.getByTestId('current-workout')).toHaveTextContent('Leg Day');
    expect(screen.getByTestId('current-workout')).toHaveTextContent('Focus on lower body');
  });

  it('should update an existing workout', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // First load all workouts
    await userEvent.click(screen.getByTestId('fetch-workouts-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('workouts-list')).toBeInTheDocument();
    });
    
    // View a specific workout
    await userEvent.click(screen.getByTestId('view-workout-1'));
    await waitFor(() => {
      expect(screen.getByTestId('current-workout')).toBeInTheDocument();
    });
    
    // Update the workout name and description
    await userEvent.type(screen.getByTestId('workout-name-input'), 'Updated Workout');
    await userEvent.type(screen.getByTestId('workout-desc-input'), 'New description');
    
    // Add a new exercise
    await userEvent.type(screen.getByTestId('exercise-name-input'), 'Pull-ups');
    await userEvent.click(screen.getByTestId('add-exercise-btn'));
    
    // Update the workout
    await userEvent.click(screen.getByTestId('save-workout-btn'));
    
    // Wait for the update to complete
    await waitFor(() => {
      expect(screen.getByTestId('current-workout')).toHaveTextContent('Updated Workout');
      expect(screen.getByTestId('current-workout')).toHaveTextContent('New description');
    });
  });

  it('should delete a workout', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // First load all workouts
    await userEvent.click(screen.getByTestId('fetch-workouts-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('workouts-list')).toBeInTheDocument();
    });
    
    // Delete the first workout
    await userEvent.click(screen.getByTestId('delete-workout-1'));
    
    // Loading indicator should appear
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for the operation to complete and verify the loading indicator is gone
    await waitFor(() => {
      expect(screen.queryByTestId('loading-indicator')).not.toBeInTheDocument();
    });
  });

  it('should start a workout session', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // First load all workouts
    await userEvent.click(screen.getByTestId('fetch-workouts-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('workouts-list')).toBeInTheDocument();
    });
    
    // Start the first workout
    await userEvent.click(screen.getByTestId('start-workout-1'));
    
    // Loading indicator should appear
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for active session to appear
    await waitFor(() => {
      expect(screen.getByTestId('active-session')).toBeInTheDocument();
    });
    
    // Verify session info
    expect(screen.getByTestId('active-session')).toHaveTextContent('Status: in_progress');
    expect(screen.getByTestId('complete-workout-btn')).toBeInTheDocument();
  });

  it('should complete a workout session', async () => {
    render(
      <TestWrapper>
        <WorkoutManager />
      </TestWrapper>
    );
    
    // First load all workouts
    await userEvent.click(screen.getByTestId('fetch-workouts-btn'));
    await waitFor(() => {
      expect(screen.getByTestId('workouts-list')).toBeInTheDocument();
    });
    
    // Start the first workout
    await userEvent.click(screen.getByTestId('start-workout-1'));
    await waitFor(() => {
      expect(screen.getByTestId('active-session')).toBeInTheDocument();
    });
    
    // Complete the workout
    await userEvent.click(screen.getByTestId('complete-workout-btn'));
    
    // Loading indicator should appear
    expect(screen.getByTestId('loading-indicator')).toBeInTheDocument();
    
    // Wait for the session to update
    await waitFor(() => {
      expect(screen.getByTestId('active-session')).toHaveTextContent('Status: completed');
    });
  });
});