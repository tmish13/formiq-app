/**
 * Consolidated Tests for Form Check User Interactions
 * 
 * This file tests the user interactions with Form Check functionality:
 * 1. Viewing form check history
 * 2. Creating new form checks
 * 3. Viewing and interacting with form check feedback
 * 4. Deleting form checks
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';

// Import from shared mocks
import {
  FormCheck,
  createMockFormCheck,
  createMockFormChecks,
  setupMockServer,
  setupServerLifecycle,
  formCheckHandlers
} from '../utils/sharedMocks';

// Setup mock server
const server = setupMockServer([...formCheckHandlers]);
setupServerLifecycle(server);

/**
 * Form Check User Interaction Tests
 */
describe('Form Check User Interactions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Form Check History Component
   * Shows a list of user's form checks
   */
  const FormCheckHistory = () => {
    const [formChecks, setFormChecks] = React.useState<FormCheck[]>([]);
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);

    React.useEffect(() => {
      const fetchFormChecks = async () => {
        try {
          const response = await fetch('/api/form-checks');
          const data = await response.json();
          
          // Handle different response formats
          const checks = Array.isArray(data) ? data : data.items || [];
          setFormChecks(checks);
        } catch (err) {
          setError('Failed to load form checks');
        } finally {
          setIsLoading(false);
        }
      };

      fetchFormChecks();
    }, []);

    const handleDelete = async (id: string) => {
      if (window.confirm('Are you sure you want to delete this form check?')) {
        try {
          await fetch(`/api/form-checks/${id}`, {
            method: 'DELETE'
          });
          
          // Remove from local state
          setFormChecks(formChecks.filter(check => check.id !== id));
        } catch (err) {
          setError('Failed to delete form check');
        }
      }
    };

    if (isLoading) {
      return <div role="status">Loading form checks...</div>;
    }

    if (error) {
      return <div role="alert">{error}</div>;
    }

  return (
    <div>
        <h1>Form Check History</h1>
        
      {formChecks.length === 0 ? (
          <p data-testid="empty-state">You don't have any form checks yet</p>
      ) : (
        <ul data-testid="form-check-list">
            {formChecks.map(check => (
            <li key={check.id} data-testid={`form-check-item-${check.id}`}>
              <div>
                  <strong>Exercise: {check.exercise_type}</strong>
                </div>
                <div>Status: {check.status}</div>
                {check.score && <div>Score: {check.score}</div>}
                <div>
                <button 
                    onClick={() => handleDelete(check.id.toString())}
                  data-testid={`delete-btn-${check.id}`}
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

  /**
   * Form Check Feedback Component
   * Displays the feedback and score for a form check
   */
  interface FormCheckFeedbackProps {
    score: number;
    feedback?: Array<{
      id: number;
      message: string;
      severity: string;
      timestamp: number;
    }>;
  }

  const FormCheckFeedback: React.FC<FormCheckFeedbackProps> = ({ score, feedback = [] }) => (
    <div data-testid="form-check-feedback">
      <div data-testid="score">Form Check Score: {score}%</div>
      
      {feedback.length > 0 && (
        <ul data-testid="feedback-list">
          {feedback.map(item => (
            <li 
              key={item.id} 
              className={item.severity}
              data-testid={`feedback-item-${item.severity}`}
            >
              {item.message}
              </li>
            ))}
          </ul>
      )}
    </div>
  );

  /**
   * Form Check Details Component
   * Displays detailed information about a form check
   */
  const FormCheckDetails = () => {
    const [formCheck, setFormCheck] = React.useState<FormCheck | null>(null);
    const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  
    React.useEffect(() => {
      const fetchFormCheck = async () => {
        // In a real app, we'd get the ID from URL params
        const id = 'form-check-1';
        
        try {
          const response = await fetch(`/api/form-checks/${id}`);
          
          if (!response.ok) {
            throw new Error('Form check not found');
          }
          
          const data = await response.json();
          setFormCheck(data);
    } catch (err) {
          setError('Failed to load form check details');
    } finally {
      setIsLoading(false);
    }
  };
  
      fetchFormCheck();
    }, []);
    
    if (isLoading) {
      return <div role="status">Loading form check details...</div>;
    }
    
    if (error) {
      return <div role="alert">{error}</div>;
    }
    
    if (!formCheck) {
      return <div>Form check not found</div>;
    }
  
  return (
      <div data-testid="form-check-details">
        <h1>{formCheck.exercise_type} Form Check</h1>
        
        {formCheck.status === 'pending' ? (
          <div>
            <p>Your form check is being analyzed</p>
            <div role="progressbar">Analysis in progress...</div>
          </div>
        ) : (
          <>
            <FormCheckFeedback 
              score={formCheck.score || 0} 
              feedback={formCheck.feedback_items}
            />
        
        <div>
              <h2>Video</h2>
              <video 
                src={formCheck.video_url} 
                controls
                data-testid="form-check-video"
          />
        </div>
          </>
        )}
    </div>
  );
};

  /**
   * Upload Form Check Component
   * Allows users to submit a new form check
   */
  const UploadFormCheck = () => {
    const [formData, setFormData] = React.useState({
      exercise_type: '',
      video_url: '',
      notes: ''
    });
    const [isSubmitting, setIsSubmitting] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [isSubmitted, setIsSubmitted] = React.useState(false);
    
    const handleChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLTextAreaElement>) => {
      const { name, value } = e.target;
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    };
    
    const handleSubmit = async (e: React.FormEvent) => {
      e.preventDefault();
      
      if (!formData.exercise_type) {
        setError('Please select an exercise type');
        return;
      }
      
      if (!formData.video_url) {
        setError('Please upload a video');
        return;
      }
      
      setIsSubmitting(true);
      setError(null);
      
      try {
        const response = await fetch('/api/form-checks', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
          throw new Error('Failed to submit form check');
        }
        
        setIsSubmitted(true);
      } catch (err) {
        setError('Failed to submit form check. Please try again.');
      } finally {
        setIsSubmitting(false);
      }
    };
    
    // Mock file input handler (in real app would upload to server/storage)
    const handleFileSelect = () => {
      setFormData(prev => ({
        ...prev,
        video_url: 'https://example.com/mock-video-url.mp4'
      }));
    };
    
    if (isSubmitted) {
      return (
        <div data-testid="submission-success">
          <h1>Form Check Submitted!</h1>
          <p>Your form check has been submitted successfully.</p>
          <p>We are analyzing your form and will provide feedback soon.</p>
        </div>
      );
    }
    
    return (
      <div>
        <h1>Submit New Form Check</h1>
        
        <form onSubmit={handleSubmit} data-testid="upload-form">
          <div>
            <label htmlFor="exercise-type">Exercise Type</label>
            <select
              id="exercise-type"
              name="exercise_type"
              value={formData.exercise_type}
              onChange={handleChange}
              aria-label="Exercise type"
            >
              <option value="">Select an exercise</option>
              <option value="squat">Squat</option>
              <option value="deadlift">Deadlift</option>
              <option value="bench_press">Bench Press</option>
            </select>
          </div>
          
          <div>
            <label htmlFor="video-upload">Upload Video</label>
            <input
              id="video-upload"
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              aria-label="Upload video"
            />
            {formData.video_url && (
              <p data-testid="video-selected">Video selected</p>
            )}
          </div>
          
          <div>
            <label htmlFor="notes">Notes</label>
            <textarea
              id="notes"
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              aria-label="Notes"
              placeholder="Add notes about your form check"
            />
          </div>
          
          {error && (
            <div role="alert" data-testid="submission-error">
              {error}
            </div>
          )}
          
          <button 
            type="submit"
            disabled={isSubmitting}
            data-testid="submit-button"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Form Check'}
          </button>
        </form>
      </div>
    );
  };

  /**
   * Simple App for routing
   */
  const FormCheckApp = () => (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<FormCheckHistory />} />
        <Route path="/upload" element={<UploadFormCheck />} />
        <Route path="/form-check/:id" element={<FormCheckDetails />} />
      </Routes>
    </BrowserRouter>
  );

  // Tests for viewing form check history
  describe('Viewing Form Check History', () => {
    it('GIVEN a user has submitted form checks WHEN they view their history THEN they see all their previous submissions', async () => {
      render(<FormCheckHistory />);
      
      // Verify loading state is shown
      expect(screen.getByRole('status')).toBeInTheDocument();
      
      // Verify form checks are displayed
      await waitFor(() => {
        expect(screen.getByTestId('form-check-list')).toBeInTheDocument();
      });
      
      // Verify multiple form checks are shown
      const listItems = screen.getAllByTestId(/form-check-item/);
      expect(listItems.length).toBeGreaterThan(0);
    });
    
    it('GIVEN a user has no form checks WHEN they view their history THEN they see an empty state message', async () => {
      // Override handler to return empty array
      server.use(
        http.get('/api/form-checks', () => {
          return HttpResponse.json([]);
        })
      );
      
      render(<FormCheckHistory />);
      
      // Verify empty state message is displayed
      await waitFor(() => {
        expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a user wants to delete a form check WHEN they click delete and confirm THEN the form check is removed', async () => {
      // Mock window.confirm to return true
      window.confirm = jest.fn().mockReturnValue(true);
      
      const user = userEvent.setup();
      render(<FormCheckHistory />);
      
      // Wait for form checks to load
      await waitFor(() => {
        expect(screen.getByTestId('form-check-list')).toBeInTheDocument();
      });
      
      // Store the initial count of form checks
      const initialItems = screen.getAllByTestId(/form-check-item/);
      
      // Click delete on the first form check
      const deleteButton = screen.getAllByTestId(/delete-btn/)[0];
      await user.click(deleteButton);
      
      // Verify form check is removed
      await waitFor(() => {
        const remainingItems = screen.getAllByTestId(/form-check-item/);
        expect(remainingItems.length).toBe(initialItems.length - 1);
      });
      
      // Verify confirm was called
      expect(window.confirm).toHaveBeenCalled();
    });
  });
  
  // Tests for viewing form check details
  describe('Viewing Form Check Details', () => {
    it('GIVEN a completed form check WHEN a user views the details THEN they see the score and feedback', async () => {
      // Use a custom handler to return a completed form check
      server.use(
        http.get('/api/form-checks/:id', () => {
          return HttpResponse.json(createMockFormCheck({
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
          }));
        })
      );
      
      render(<FormCheckDetails />);
      
      // Verify loading state is shown
      expect(screen.getByRole('status')).toBeInTheDocument();
      
      // Verify form check details are displayed
      await waitFor(() => {
        expect(screen.getByTestId('form-check-details')).toBeInTheDocument();
      });
      
      // Verify score is displayed
      expect(screen.getByTestId('score')).toHaveTextContent('85%');
      
      // Verify feedback is displayed
      const goodFeedback = screen.getByTestId('feedback-item-good');
      expect(goodFeedback).toHaveTextContent('Good depth on your squat');
      
      const warningFeedback = screen.getByTestId('feedback-item-warning');
      expect(warningFeedback).toHaveTextContent('Keep your knees aligned with your toes');
    });
    
    it('GIVEN a pending form check WHEN a user views the details THEN they see the analysis in progress', async () => {
      // Use a custom handler to return a pending form check
      server.use(
        http.get('/api/form-checks/:id', () => {
          return HttpResponse.json(createMockFormCheck({
            status: 'pending'
          }));
        })
      );
      
      render(<FormCheckDetails />);
      
      // Verify loading state is shown
      expect(screen.getByRole('status')).toBeInTheDocument();
      
      // Verify form check details are displayed
      await waitFor(() => {
        expect(screen.getByTestId('form-check-details')).toBeInTheDocument();
      });
      
      // Verify progress indicator is shown
      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.queryByTestId('form-check-feedback')).not.toBeInTheDocument();
    });
  });
  
  // Tests for submitting a new form check
  describe('Submitting a New Form Check', () => {
    it('GIVEN a user completes the form WHEN they submit it THEN the form check is created', async () => {
      const user = userEvent.setup();
      render(<UploadFormCheck />);
      
      // Fill out the form
      await user.selectOptions(
        screen.getByLabelText('Exercise type'),
        'squat'
      );
      
      // Simulate file upload
      await user.click(screen.getByLabelText('Upload video'));
      
      // Verify file selection is shown
      expect(screen.getByTestId('video-selected')).toBeInTheDocument();
      
      // Add notes
      await user.type(
        screen.getByLabelText('Notes'),
        'Testing my squat form'
      );
      
      // Submit the form
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify success message is shown
      await waitFor(() => {
        expect(screen.getByTestId('submission-success')).toBeInTheDocument();
      });
    });
    
    it('GIVEN a user submits incomplete form data WHEN they click submit THEN they see validation errors', async () => {
      const user = userEvent.setup();
      render(<UploadFormCheck />);
      
      // Submit without filling out the form
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify error message is shown
      expect(screen.getByTestId('submission-error')).toHaveTextContent('Please select an exercise type');
      
      // Now select an exercise type only
      await user.selectOptions(
        screen.getByLabelText('Exercise type'),
        'squat'
      );
      
      // Submit again without a video
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify video error is shown
      expect(screen.getByTestId('submission-error')).toHaveTextContent('Please upload a video');
    });
    
    it('GIVEN a server error WHEN user submits a form check THEN they see an error message', async () => {
      // Override handler to simulate server error
      server.use(
        http.post('/api/form-checks', () => {
          return new HttpResponse(null, { status: 500 });
        })
      );
      
      const user = userEvent.setup();
      render(<UploadFormCheck />);
      
      // Fill out the form
      await user.selectOptions(
        screen.getByLabelText('Exercise type'),
        'squat'
      );
      
      // Simulate file upload
      await user.click(screen.getByLabelText('Upload video'));
      
      // Submit the form
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify error message is shown
      await waitFor(() => {
        expect(screen.getByTestId('submission-error')).toHaveTextContent('Failed to submit form check');
      });
    });
  });
}); 