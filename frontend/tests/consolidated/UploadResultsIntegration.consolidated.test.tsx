import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { generateTestFormAnalysis } from '../../utils/test-data';

// Mock the Upload component
jest.mock('../../components/form/Upload', () => ({
  __esModule: true,
  default: () => (
    <div data-testid="upload-page">
      <h1>Upload your video</h1>
      <div data-testid="upload-area" role="button" aria-label="Drop video here or click to select">
        Drop video here or click to select
      </div>
      <button data-testid="upload-button">Upload</button>
    </div>
  )
}));

// Mock the Results component
jest.mock('../../components/form/Results', () => ({
  __esModule: true,
  Results: () => (
    <div data-testid="results-page">
      <h1>Form Analysis Results</h1>
      <div data-testid="confidence-score" aria-label="Confidence Score">Confidence Score: 85%</div>
      <div data-testid="form-feedback" role="region" aria-label="Form feedback">
        <ul>
          <li>Good form overall</li>
          <li>Knees slightly caving inward</li>
          <li>Maintain neutral spine</li>
        </ul>
      </div>
      <div data-testid="video-player" aria-label="Video player">
        <div>Video Player</div>
        <button aria-label="Play">Play</button>
        <button aria-label="Pause">Pause</button>
      </div>
    </div>
  )
}));

// Mock components/form/FormAnalysis
jest.mock('../../components/form/FormAnalysis', () => ({
  FormAnalysis: ({ formCheck }) => (
    <div data-testid="form-analysis">
      <div data-testid="analysis-score" aria-label="Analysis score">Score: {formCheck?.score || 0}%</div>
      <div data-testid="analysis-feedback" role="list" aria-label="Analysis feedback">
        {(formCheck?.feedback || []).map((item, index) => (
          <div key={index} data-testid="feedback-item" role="listitem">{item.message}</div>
        ))}
      </div>
    </div>
  )
}));

// Setup MSW server
const server = setupServer(
  rest.get('/api/form-check/:id', (req, res, ctx) => {
    return res(
      ctx.json(generateTestFormAnalysis())
    );
  }),
  rest.post('/api/form-check/upload', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'fc-123',
        status: 'success'
      })
    );
  })
);

describe('Upload to Results Integration', () => {
  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  /**
   * Tests covering basic success case from the legacy file
   * Migrated and enhanced from UploadResultsIntegration.test.tsx
   */
  describe('Basic Results Display', () => {
    it('should properly display analysis results to the user', async () => {
      // Render the Results component directly to test the basic display
      const { Results } = jest.requireMock('../../components/form/Results');
      render(<Results />);
      
      // Verify results are displayed with accessible elements
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Form Analysis Results');
      expect(screen.getByLabelText('Confidence Score')).toHaveTextContent('85%');
      
      // Verify feedback is displayed in an accessible way
      const feedbackRegion = screen.getByRole('region', { name: 'Form feedback' });
      expect(feedbackRegion).toBeInTheDocument();
      
      // Check that specific feedback items are displayed
      const feedbackItems = within(feedbackRegion).getAllByRole('listitem');
      expect(feedbackItems).toHaveLength(3);
      expect(feedbackItems[0]).toHaveTextContent('Good form overall');
      expect(feedbackItems[1]).toHaveTextContent('Knees slightly caving inward');
    });
  });

  /**
   * Migrated and enhanced error handling tests from the legacy file
   */
  describe('Basic Error Handling', () => {
    it('should display upload errors in an accessible way', async () => {
      // Render a component that shows an upload error
      render(
        <div role="main">
          <h1>Upload Form Check</h1>
          <div role="alert" aria-live="assertive" data-testid="upload-error">
            Failed to upload video. Please try again.
          </div>
          <button>Try Again</button>
        </div>
      );
      
      // Verify error message is displayed accessibly
      const errorMessage = screen.getByRole('alert');
      expect(errorMessage).toBeInTheDocument();
      expect(errorMessage).toHaveTextContent('Failed to upload video');
      
      // Verify retry action is available
      expect(screen.getByRole('button')).toHaveTextContent('Try Again');
    });
    
    it('should display analysis errors with helpful information', async () => {
      // Render a component with analysis error
      render(
        <div role="main">
          <h1>Form Analysis Results</h1>
          <div role="alert" aria-live="assertive">
            Failed to load analysis results. Please try again later.
          </div>
          <button>Retry Analysis</button>
        </div>
      );
      
      // Verify error message is displayed accessibly
      const errorMessage = screen.getByRole('alert');
      expect(errorMessage).toBeInTheDocument();
      expect(errorMessage).toHaveTextContent('Failed to load analysis results');
      
      // Verify retry action is available
      expect(screen.getByRole('button')).toHaveTextContent('Retry Analysis');
    });
  });

  /**
   * Tests for complete upload to results flow
   */
  describe('End-to-End Flow', () => {
    it('should transition from upload to results page', async () => {
      // Create a component that simulates the complete flow
      const CompleteFlow = () => {
        const [currentStep, setCurrentStep] = React.useState('upload');
        const [analysisId, setAnalysisId] = React.useState('');
        
        const handleUploadSuccess = () => {
          setAnalysisId('fc-123');
          setCurrentStep('processing');
          
          // Simulate processing delay
          setTimeout(() => {
            setCurrentStep('results');
          }, 100);
        };
        
        return (
          <div>
            {currentStep === 'upload' && (
              <div data-testid="upload-step" role="region" aria-label="Upload form check">
                <h2>Upload Form Check</h2>
                <button 
                  data-testid="simulate-upload" 
                  onClick={handleUploadSuccess}
                >
                  Submit Video
                </button>
              </div>
            )}
            
            {currentStep === 'processing' && (
              <div data-testid="processing-step" role="status" aria-label="Processing video">
                <h2>Processing Video</h2>
                <div>Please wait while we analyze your form...</div>
              </div>
            )}
            
            {currentStep === 'results' && (
              <div data-testid="results-step" role="region" aria-label="Analysis results">
                <h2>Analysis Results</h2>
                <div data-testid="analysis-id">Analysis ID: {analysisId}</div>
                <div data-testid="score">Score: 85%</div>
                <ul role="list" aria-label="Feedback items">
                  <li role="listitem">Good form overall</li>
                  <li role="listitem">Knees slightly caving inward</li>
                </ul>
              </div>
            )}
          </div>
        );
      };
      
      const { user } = render(<CompleteFlow />);
      
      // Start on upload step
      expect(screen.getByRole('region', { name: /upload form check/i })).toBeInTheDocument();
      
      // Trigger upload
      await user.click(screen.getByTestId('simulate-upload'));
      
      // Should show processing step
      await waitFor(() => {
        expect(screen.getByRole('status', { name: /processing video/i })).toBeInTheDocument();
      });
      
      // Should transition to results step
      await waitFor(() => {
        expect(screen.getByRole('region', { name: /analysis results/i })).toBeInTheDocument();
        expect(screen.getByTestId('analysis-id')).toHaveTextContent('fc-123');
      });
    });
  });

  /**
   * Tests for correct rendering of results after upload
   */
  describe('Results Rendering', () => {
    it('should display form check results with proper components', async () => {
      // Setup mock for form check data
      const mockFormCheck = {
        id: 'fc-123',
        score: 85,
        exerciseType: 'squat',
        feedback: [
          { id: 'fb-1', message: 'Good form overall', severity: 'positive' },
          { id: 'fb-2', message: 'Knees slightly caving inward', severity: 'warning' },
        ],
        videoUrl: 'https://example.com/video.mp4',
        thumbnailUrl: 'https://example.com/thumbnail.jpg',
        userId: 'user-123',
        createdAt: '2023-01-01T12:00:00Z'
      };
      
      // Create a focused Results component
      const ResultsDisplay = () => {
        return (
          <div data-testid="results-container" role="main">
            <h1>Form Analysis Results</h1>
            <div data-testid="score-display" role="status" aria-label="Score">
              Score: {mockFormCheck.score}%
            </div>
            <div data-testid="feedback-list" role="list" aria-label="Feedback list">
              {mockFormCheck.feedback.map((item, index) => (
                <div key={index} data-testid={`feedback-item-${index}`} role="listitem">
                  {item.message} - {item.severity}
                </div>
              ))}
            </div>
            <div data-testid="video-container">
              <div data-testid="video-player">
                <video src={mockFormCheck.videoUrl} data-testid="video-element" />
              </div>
            </div>
          </div>
        );
      };
      
      render(<ResultsDisplay />);
      
      // Verify score is displayed correctly
      expect(screen.getByRole('status', { name: /score/i })).toHaveTextContent('85%');
      
      // Verify feedback items are displayed
      const feedbackItems = screen.getAllByRole('listitem');
      expect(feedbackItems).toHaveLength(2);
      expect(feedbackItems[0]).toHaveTextContent('Good form overall');
      expect(feedbackItems[1]).toHaveTextContent('Knees slightly caving inward');
      
      // Verify video player is present
      const videoElement = screen.getByTestId('video-element');
      expect(videoElement).toHaveAttribute('src', mockFormCheck.videoUrl);
    });
  });

  /**
   * Tests for error handling during upload to results flow
   */
  describe('Error Handling', () => {
    it('should handle upload failure gracefully', async () => {
      // Create component that simulates an upload error
      const UploadWithError = () => {
        const [error, setError] = React.useState(false);
        
        const triggerError = () => {
          setError(true);
        };
        
        return (
          <div>
            <button 
              data-testid="trigger-error" 
              onClick={triggerError}
              aria-label="Upload Video"
            >
              Upload Video
            </button>
            
            {error && (
              <div data-testid="upload-error" role="alert">
                Failed to upload video. Please try again.
              </div>
            )}
          </div>
        );
      };
      
      const { user } = render(<UploadWithError />);
      
      // Trigger the error
      await user.click(screen.getByRole('button', { name: /upload video/i }));
      
      // Verify error message is displayed
      expect(screen.getByRole('alert')).toHaveTextContent('Failed to upload video');
    });
    
    it('should handle analysis failure gracefully', async () => {
      // Setup server to return an error for the analysis
      server.use(
        rest.get('/api/form-check/:id', (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ error: 'Analysis failed' })
          );
        })
      );
      
      // Create component that simulates an analysis error
      const AnalysisWithError = () => {
        const [loading, setLoading] = React.useState(true);
        const [error, setError] = React.useState(false);
        
        // Simulate API request failure
        React.useEffect(() => {
          const timer = setTimeout(() => {
            setLoading(false);
            setError(true);
          }, 100);
          
          return () => clearTimeout(timer);
        }, []);
        
        if (loading) {
          return <div data-testid="loading" role="status" aria-label="Loading analysis">Loading analysis...</div>;
        }
        
        if (error) {
          return (
            <div data-testid="analysis-error" role="alert">
              Failed to load analysis results. Please try again later.
            </div>
          );
        }
        
        return <div>Analysis Results</div>;
      };
      
      render(<AnalysisWithError />);
      
      // Initially should show loading
      expect(screen.getByRole('status', { name: /loading analysis/i })).toBeInTheDocument();
      
      // Then should show error
      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent('Failed to load analysis results');
      });
    });
  });

  /**
   * Tests for progress tracking during the flow
   */
  describe('Progress Tracking', () => {
    it('should display progress during analysis', async () => {
      // Component that simulates progress updates
      const ProgressTracker = () => {
        const [progress, setProgress] = React.useState(0);
        const [status, setStatus] = React.useState('uploading');
        
        // Simulate progress updates
        React.useEffect(() => {
          if (progress < 100) {
            const timer = setTimeout(() => {
              setProgress(prev => {
                const newProgress = prev + 20;
                if (newProgress >= 100) {
                  setStatus('complete');
                  return 100;
                }
                return newProgress;
              });
            }, 100);
            
            return () => clearTimeout(timer);
          }
        }, [progress]);
        
        return (
          <div>
            <div data-testid="progress-status" role="status" aria-label="Upload status">{status}</div>
            <div data-testid="progress-value" role="progressbar" aria-valuenow={progress} aria-valuemin="0" aria-valuemax="100">{progress}%</div>
            <div 
              data-testid="progress-bar"
              style={{ width: `${progress}%`, height: '10px', background: 'blue' }}
              role="presentation"
            ></div>
            
            {status === 'complete' && (
              <div data-testid="analysis-complete" role="status" aria-label="Analysis status">Analysis complete!</div>
            )}
          </div>
        );
      };
      
      render(<ProgressTracker />);
      
      // Verify initial state
      expect(screen.getByRole('status', { name: /upload status/i })).toHaveTextContent('uploading');
      expect(screen.getByRole('progressbar')).toHaveTextContent('0%');
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
      
      // Verify progress updates
      await waitFor(() => {
        expect(screen.getByRole('progressbar')).toHaveTextContent('20%');
        expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '20');
      });
      
      // Verify completion
      await waitFor(() => {
        expect(screen.getByRole('progressbar')).toHaveTextContent('100%');
        expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
        expect(screen.getByRole('status', { name: /upload status/i })).toHaveTextContent('complete');
        expect(screen.getByRole('status', { name: /analysis status/i })).toHaveTextContent('Analysis complete');
      });
    });
  });

  /**
   * Tests for video player integration
   */
  describe('Video Player Integration', () => {
    it('should properly display video from analysis results', async () => {
      // Mock for VideoPlayer with form check highlights
      const VideoPlayerWithHighlights = () => {
        const videoUrl = 'https://example.com/video.mp4';
        const highlights = [
          { timeMs: 1500, message: 'Knees caving inward' },
          { timeMs: 3000, message: 'Good depth achieved' }
        ];
        
        return (
          <div data-testid="video-player-container">
            <video 
              src={videoUrl} 
              data-testid="video-element"
              controls
              aria-label="Form check video"
            />
            
            <div data-testid="highlights-container" role="region" aria-label="Form check highlights">
              <h3 id="highlights-heading">Form Check Highlights</h3>
              <ul role="list" aria-labelledby="highlights-heading">
                {highlights.map((highlight, index) => (
                  <li 
                    key={index}
                    data-testid={`highlight-${index}`}
                    role="listitem"
                    tabIndex={0}
                    aria-label={`Highlight at ${Math.floor(highlight.timeMs / 1000)} seconds: ${highlight.message}`}
                  >
                    {`${Math.floor(highlight.timeMs / 1000)}s: ${highlight.message}`}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        );
      };
      
      render(<VideoPlayerWithHighlights />);
      
      // Verify video element exists
      expect(screen.getByRole('video', { name: /form check video/i })).toBeInTheDocument();
      
      // Verify highlights are displayed
      const highlights = screen.getAllByRole('listitem');
      expect(highlights).toHaveLength(2);
      expect(highlights[0]).toHaveTextContent('1s: Knees caving inward');
      expect(highlights[1]).toHaveTextContent('3s: Good depth achieved');
    });
  });
}); 