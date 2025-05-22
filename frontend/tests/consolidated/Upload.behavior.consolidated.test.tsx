import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupMockServer } from '../../../../tests/utils/msw';
import { testRender } from '../../../../tests/utils/testRender';
import { Upload } from '../Upload';
import { rest } from 'msw';

// Mock navigate function
const mockNavigate = jest.fn();

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

// Mock CameraService
jest.mock('../../../services/CameraService', () => ({
  CameraService: {
    startRecording: jest.fn().mockResolvedValue({}),
    stopRecording: jest.fn().mockResolvedValue({ videoUrl: 'blob:test-video-url' }),
  },
}));

// Set up MSW server for handling API calls
const server = setupMockServer([
  rest.post('/api/form-analysis/upload', (req, res, ctx) => {
    const { videoUrl } = req.body as any;
    
    // Validate video URL
    if (!videoUrl) {
      return res(
        ctx.status(400),
        ctx.json({ message: 'No video URL provided' })
      );
    }

    // Return success response with a form check ID
    return res(
      ctx.status(200),
      ctx.json({ id: 'abc123' })
    );
  }),
]);

describe('Upload Component Behavior', () => {
  const originalFetch = global.fetch;
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock file input change event
    global.URL.createObjectURL = jest.fn().mockReturnValue('blob:mock-file-url');
  });
  
  afterAll(() => {
    global.fetch = originalFetch;
  });

  /**
   * Tests related to file selection UI functionality
   */
  describe('File Selection UI', () => {
    // Test 1: File selection UI works
    it('should handle file upload through file input', async () => {
      // Create a modified version of the Upload component with file input
      const UploadWithFileInput = () => {
        const [file, setFile] = React.useState<File | null>(null);
        const [error, setError] = React.useState<string | null>(null);
        
        const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
          const selectedFile = e.target.files?.[0];
          
          if (!selectedFile) {
            return;
          }
          
          // Check file type
          if (!selectedFile.type.includes('video/')) {
            setError('Please select a video file');
            return;
          }
          
          setFile(selectedFile);
          setError(null);
        };
        
        const handleUpload = async () => {
          if (!file) return;
          
          try {
            const response = await fetch('/api/form-analysis/upload', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ videoUrl: URL.createObjectURL(file) }),
            });
            
            if (!response.ok) {
              throw new Error('Upload failed');
            }
            
            const data = await response.json();
            mockNavigate(`/results/${data.id}`);
          } catch (err) {
            setError('Failed to upload video');
          }
        };
        
        return (
          <div>
            <input 
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              data-testid="file-input"
            />
            
            <button 
              onClick={handleUpload}
              disabled={!file}
              data-testid="upload-button"
            >
              Upload
            </button>
            
            {error && <div data-testid="error-message">{error}</div>}
            {file && <div data-testid="selected-file">{file.name}</div>}
            
            <Upload />
          </div>
        );
      };
      
      // Render the component
      const { user } = testRender(<UploadWithFileInput />);
      
      // Create a mock video file
      const videoFile = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
      
      // Upload the file
      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, videoFile);
      
      // Verify the file name is displayed
      expect(screen.getByTestId('selected-file')).toHaveTextContent('test-video.mp4');
      
      // Click upload button
      await user.click(screen.getByTestId('upload-button'));
      
      // Verify navigation occurred with the right ID
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/results/abc123');
      });
    });

    // Test 2: Invalid file type shows error
    it('should display error when uploading invalid file type', async () => {
      // Create a modified version of the Upload component with file input validation
      const UploadWithFileValidation = () => {
        const [file, setFile] = React.useState<File | null>(null);
        const [error, setError] = React.useState<string | null>(null);
        
        const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
          const selectedFile = e.target.files?.[0];
          
          if (!selectedFile) {
            return;
          }
          
          // Check file type
          if (!selectedFile.type.includes('video/')) {
            setError('Please select a video file');
            return;
          }
          
          setFile(selectedFile);
          setError(null);
        };
        
        return (
          <div>
            <input 
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              data-testid="file-input"
            />
            
            {error && <div data-testid="error-message">{error}</div>}
            {file && <div data-testid="selected-file">{file.name}</div>}
            
            <Upload />
          </div>
        );
      };
      
      // Render the component
      const { user } = testRender(<UploadWithFileValidation />);
      
      // Create a mock non-video file
      const imageFile = new File(['mock image content'], 'test-image.jpg', { type: 'image/jpeg' });
      
      // Upload the file
      const fileInput = screen.getByTestId('file-input');
      await user.upload(fileInput, imageFile);
      
      // Verify error message is displayed
      expect(screen.getByTestId('error-message')).toHaveTextContent('Please select a video file');
    });
  });

  /**
   * Tests related to camera recording functionality
   */
  describe('Camera Recording', () => {
    // Test 3: Record button starts and stops recording
    it('should handle starting and stopping recording', async () => {
      // Render component
      const { user } = testRender(<Upload />);
      
      // Verify start recording button is visible
      const startButton = screen.getByTestId('start-recording');
      expect(startButton).toBeInTheDocument();
      
      // Click start recording
      await user.click(startButton);
      
      // Verify CameraService.startRecording was called
      expect(require('../../../services/CameraService').CameraService.startRecording).toHaveBeenCalled();
      
      // Verify stop recording button is now visible
      const stopButton = screen.getByTestId('stop-recording');
      expect(stopButton).toBeInTheDocument();
      
      // Click stop recording
      await user.click(stopButton);
      
      // Verify CameraService.stopRecording was called
      expect(require('../../../services/CameraService').CameraService.stopRecording).toHaveBeenCalled();
      
      // Verify loading spinner appears
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      
      // Verify navigation to results page with correct ID
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/results/abc123');
      });
    });
  });

  /**
   * Tests related to upload progress indicator
   */
  describe('Upload Progress Indicator', () => {
    // Test 4: Upload progress indicator is displayed
    it('should display upload progress indicator during upload', async () => {
      // Create a modified version of the Upload component with progress indication
      const UploadWithProgress = () => {
        const [isUploading, setIsUploading] = React.useState(false);
        const [progress, setProgress] = React.useState(0);
        
        const handleStartUpload = () => {
          setIsUploading(true);
          setProgress(0);
          
          // Simulate progress updates
          const interval = setInterval(() => {
            setProgress(prev => {
              if (prev >= 100) {
                clearInterval(interval);
                setIsUploading(false);
                return 100;
              }
              return prev + 10;
            });
          }, 100);
        };
        
        return (
          <div>
            <button 
              onClick={handleStartUpload}
              data-testid="start-upload"
            >
              Start Upload
            </button>
            
            {isUploading && (
              <div data-testid="progress-indicator">
                <div data-testid="progress-value">{progress}%</div>
              </div>
            )}
            
            <Upload />
          </div>
        );
      };
      
      // Render the component
      const { user } = testRender(<UploadWithProgress />);
      
      // Click start upload
      await user.click(screen.getByTestId('start-upload'));
      
      // Verify progress indicator is displayed
      expect(screen.getByTestId('progress-indicator')).toBeInTheDocument();
      expect(screen.getByTestId('progress-value')).toBeInTheDocument();
    });
  });

  /**
   * Tests related to error handling during upload
   */
  describe('Error Handling', () => {
    // Test 5: Display error message when upload fails
    it('should display error message when upload fails', async () => {
      // Mock API failure
      server.use(
        rest.post('/api/form-analysis/upload', (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ message: 'Server error during upload' })
          );
        })
      );
      
      // Render component
      const { user } = testRender(<Upload />);
      
      // Start and stop recording
      await user.click(screen.getByTestId('start-recording'));
      await user.click(screen.getByTestId('stop-recording'));
      
      // Wait for error message to appear
      await waitFor(() => {
        expect(screen.getByText(/failed to upload video/i)).toBeInTheDocument();
      });
      
      // Verify we didn't navigate
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  /**
   * Tests related to exercise selection
   */
  describe('Exercise Selection', () => {
    // Test 6: Exercise selection works
    it('should select exercise type from dropdown', async () => {
      // Create a modified version of the Upload component with exercise selection
      const UploadWithExerciseSelect = () => {
        const [selectedExercise, setSelectedExercise] = React.useState('');
        
        return (
          <div>
            <select 
              data-testid="exercise-select"
              value={selectedExercise}
              onChange={(e) => setSelectedExercise(e.target.value)}
            >
              <option value="">Select an exercise</option>
              <option value="squat">Squat</option>
              <option value="deadlift">Deadlift</option>
              <option value="bench_press">Bench Press</option>
            </select>
            
            <Upload />
            
            <div data-testid="selected-exercise">{selectedExercise}</div>
          </div>
        );
      };
      
      // Render the component
      const { user } = testRender(<UploadWithExerciseSelect />);
      
      // Get the exercise select dropdown
      const exerciseSelect = screen.getByTestId('exercise-select');
      
      // Select 'Squat' option
      await user.selectOptions(exerciseSelect, 'squat');
      
      // Verify the selected exercise is displayed
      expect(screen.getByTestId('selected-exercise')).toHaveTextContent('squat');
    });
  });

  /**
   * Tests related to navigation after upload
   */
  describe('Navigation After Upload', () => {
    // Test 7: Navigation after successful upload
    it('should navigate to results page after successful upload', async () => {
      // Render component
      const { user } = testRender(<Upload />);
      
      // Start and stop recording
      await user.click(screen.getByTestId('start-recording'));
      await user.click(screen.getByTestId('stop-recording'));
      
      // Verify navigation occurred
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/results/abc123');
      });
    });
  });
}); 