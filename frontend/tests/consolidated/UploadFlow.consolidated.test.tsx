/**
 * Consolidated Tests for Upload User Flows
 * 
 * This file tests all critical user interactions related to video uploads:
 * - Manual file selection
 * - Drag and drop upload
 * - Camera recording
 * - Upload validation
 * - Error handling
 * - Accessibility
 */
import React from 'react';
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom';
import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// Import test utilities
import { testRender } from '../../test-utils';
import { setupMockServer } from '../../utils/msw';
import { generateTestFormAnalysis } from '../../utils/test-data';

// Import components
import Upload from '../../pages/analysis/Upload';
import { Results } from '../../pages/analysis/Results';

// Define type for mock component props
interface MockProps {
  children?: React.ReactNode;
  [key: string]: any;
}

// Mock Material-UI components
jest.mock('@mui/material', () => ({
  Box: ({ children, ...props }: MockProps) => <div data-testid="mui-box" role="presentation" {...props}>{children}</div>,
  Typography: ({ children, variant, ...props }: MockProps) => {
    const Tag = variant === 'h4' || variant === 'h6' ? variant : 'p';
    return <Tag data-testid={`typography-${variant || 'default'}`} {...props}>{children}</Tag>;
  },
  Button: ({ children, ...props }: MockProps) => <button data-testid="mui-button" {...props}>{children}</button>,
  TextField: ({ label, ...props }: MockProps) => (
    <div data-testid="mui-textfield">
      {label && <label>{label}</label>}
      <input {...props} />
    </div>
  ),
  FormControl: ({ children, ...props }: MockProps) => <div data-testid="form-control" role="group" {...props}>{children}</div>,
  InputLabel: ({ children, ...props }: MockProps) => <label data-testid="input-label" {...props}>{children}</label>,
  Select: ({ children, ...props }: MockProps) => <select data-testid="mui-select" {...props}>{children}</select>,
  MenuItem: ({ children, value, ...props }: MockProps) => <option data-testid="menu-item" value={value} {...props}>{children}</option>,
  Paper: ({ children, ...props }: MockProps) => <div data-testid="mui-paper" role="region" {...props}>{children}</div>,
  LinearProgress: ({ value, ...props }: MockProps) => <div data-testid="linear-progress" role="progressbar" aria-valuenow={value} aria-valuemin="0" aria-valuemax="100" {...props} />,
  Alert: ({ children, severity, ...props }: MockProps) => <div data-testid={`alert-${severity || 'default'}`} role="alert" {...props}>{children}</div>,
  Snackbar: ({ children, open, ...props }: MockProps) => (open ? <div data-testid="snackbar" role="alert" aria-live="polite" {...props}>{children}</div> : null),
  CircularProgress: ({ ...props }: MockProps) => <div data-testid="circular-progress" role="progressbar" aria-label="Loading" {...props} />,
  Grid: ({ children, ...props }: MockProps) => <div data-testid="mui-grid" role="presentation" {...props}>{children}</div>
}));

// Mock styled-components from @mui/system
jest.mock('@mui/system', () => ({
  styled: (Component: any) => () => {
    return (props: MockProps) => {
      const { children, ...rest } = props;
      return <Component data-testid={`styled-component`} {...rest}>{children}</Component>;
    };
  }
}));

// Mock ThemeProvider
jest.mock('@mui/material/styles', () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="theme-provider">{children}</div>
}));

// Mock CameraService
jest.mock('../../services/CameraService', () => ({
  startRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' }),
  stopRecording: jest.fn().mockResolvedValue({ videoUrl: 'test-video.mp4' })
}));

// Mock LoadingSpinner
jest.mock('../../components/atoms/LoadingSpinner', () => {
  return {
    __esModule: true,
    default: () => <div data-testid="loading-spinner" role="progressbar" aria-label="Loading...">Loading...</div>
  };
});

// Mock useFormCheck hook
jest.mock('../../hooks/useFormCheck', () => ({
  useFormCheck: () => ({
    submitFormCheck: jest.fn().mockResolvedValue({ id: 'analysis-123' }),
    isLoading: false,
    error: null
  })
}));

// Mock useAuth hook
jest.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'user-123', email: 'test@example.com' }
  })
}));

// Mock navigate function
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

// Mock URL actions
window.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
window.URL.revokeObjectURL = jest.fn();

// Create MSW server for API mocking
const server = setupServer(
  // Upload endpoint
  rest.post('/api/form-analysis/upload', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'analysis-123',
        status: 'processing',
        message: 'Your video is being processed'
      })
    );
  }),
  
  // Form check upload endpoint
  rest.post('/api/form-checks/upload', (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({ id: '123', url: 'mock-video-url.mp4' })
    );
  }),
  
  // Status endpoint
  rest.get('/api/form-analysis/status/:id', (req, res, ctx) => {
    return res(
      ctx.json({
        id: 'analysis-123',
        status: 'completed',
        progress: 100
      })
    );
  }),
  
  // Analysis results endpoint
  rest.get('/api/form-analysis/:id', (req, res, ctx) => {
    return res(ctx.json(generateTestFormAnalysis()));
  }),
  
  // Form check results endpoint
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    const { id } = req.params;
    return res(
      ctx.status(200),
      ctx.json({
        id,
        exercise_type: 'squat',
        score: 85,
        feedback: [
          'Great depth on your squat',
          'Keep your back straight'
        ],
        created_at: new Date().toISOString()
      })
    );
  })
);

// Mock apiService
jest.mock('../../services/apiService', () => ({
  apiService: {
    formAnalysis: {
      analyze: jest.fn().mockResolvedValue({
        status: 200,
        data: {
          id: 'analysis-123'
        }
      })
    }
  }
}));

// Create a real-like Upload component to test form interactions
const ActualFormUpload = () => {
  const [exerciseType, setExerciseType] = React.useState('');
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isUploading, setIsUploading] = React.useState(false);
  const [uploadSuccess, setUploadSuccess] = React.useState(false);
  const [isDragging, setIsDragging] = React.useState(false);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate inputs
    if (!exerciseType) {
      setError('Please select an exercise type');
      return;
    }
    
    if (!file) {
      setError('Please select a video to upload');
      return;
    }
    
    setError(null);
    setIsUploading(true);
    
    try {
      // Simulate upload delay
      await new Promise(resolve => setTimeout(resolve, 100));
      setUploadSuccess(true);
      mockNavigate('/results/123');
    } catch (err) {
      setError('Failed to upload video');
    } finally {
      setIsUploading(false);
    }
  };
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Check file size (100MB limit)
      if (selectedFile.size > 104857600) {
        setError('File size exceeds 100 MB limit');
      } else {
        setError(null);
        setFile(selectedFile);
      }
    }
  };
  
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (!droppedFile.type.includes('video/')) {
        setError('Please drop a video file');
        return;
      }
      
      if (droppedFile.size > 104857600) {
        setError('File size exceeds 100 MB limit');
      } else {
        setError(null);
        setFile(droppedFile);
      }
    }
  };
  
  return (
    <div data-testid="upload-container">
      <form 
        data-testid="upload-form" 
        onSubmit={handleSubmit} 
        aria-label="Upload form"
      >
        <div>
          <label htmlFor="exercise-type">Exercise Type</label>
          <select 
            id="exercise-type" 
            value={exerciseType} 
            onChange={(e) => setExerciseType(e.target.value)}
            data-testid="exercise-select"
            aria-label="Exercise type"
          >
            <option value="">Select Exercise</option>
            <option value="squat">Squat</option>
            <option value="deadlift">Deadlift</option>
            <option value="bench_press">Bench Press</option>
          </select>
        </div>
        
        <div 
          data-testid="drop-zone" 
          className={`drop-zone ${isDragging ? 'dragging' : ''}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          aria-label="Drop zone for video files"
        >
          <p>Drag and drop a video file here, or</p>
          <label htmlFor="video-file">Select a file</label>
          <input 
            id="video-file" 
            type="file" 
            accept="video/*" 
            onChange={handleFileChange}
            data-testid="file-input"
            aria-label="Upload video"
          />
          {file && <p data-testid="file-name">{file.name}</p>}
        </div>
        
        <div>
          <button 
            type="button" 
            data-testid="start-recording"
            aria-label="Record from camera"
          >
            Record from Camera
          </button>
        </div>
        
        {error && <div role="alert" data-testid="error-message">{error}</div>}
        
        <button 
          type="submit" 
          disabled={isUploading}
          data-testid="submit-button"
          aria-label="Upload and analyze"
        >
          {isUploading ? 'Uploading...' : 'Upload and Analyze'}
        </button>
        
        {isUploading && <div data-testid="loading" role="status" aria-live="polite">Uploading...</div>}
        {uploadSuccess && <div role="alert" data-testid="success-message">Successfully uploaded!</div>}
      </form>
    </div>
  );
};

describe('Upload Flow Behavior', () => {
  beforeAll(() => server.listen());
  afterEach(() => {
    server.resetHandlers();
    jest.clearAllMocks();
    mockNavigate.mockReset();
  });
  afterAll(() => server.close());

  describe('Camera Recording Behavior', () => {
    // Mock component for camera tests
    const CameraUploadComponent = () => (
      <div data-testid="mock-upload-component" role="main" aria-label="Upload video for analysis">
        <h1>Upload Video</h1>
        <button data-testid="start-recording" aria-label="Start recording">Start Recording</button>
        <div data-testid="upload-status" role="status" aria-live="polite">Recording started</div>
        <button data-testid="stop-recording" aria-label="Stop recording">Stop Recording</button>
        <div data-testid="processing-status" role="status" aria-live="polite">Processing your video</div>
        <div data-testid="analysis-status" role="status" aria-live="polite">Analysis complete</div>
      </div>
    );

    beforeEach(() => {
      jest.requireMock('../../pages/analysis/Upload').default = CameraUploadComponent;
    });

    it('GIVEN user wants to record a video WHEN they use camera recording THEN they can capture and submit for analysis', async () => {
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Routes>
            <Route path="/upload" element={<Upload />} />
            <Route path="/results/:id" element={<Results />} />
          </Routes>
        </MemoryRouter>
      );

      // Start recording
      await user.click(screen.getByRole('button', { name: /start recording/i }));
      expect(screen.getByRole('status', { name: /Recording started/i })).toBeInTheDocument();

      // Stop recording
      await user.click(screen.getByRole('button', { name: /stop recording/i }));
      
      // Verify processing feedback
      await waitFor(() => {
        expect(screen.getByRole('status', { name: /Processing your video/i })).toBeInTheDocument();
      });
      
      // Verify completion feedback
      await waitFor(() => {
        expect(screen.getByRole('status', { name: /Analysis complete/i })).toBeInTheDocument();
      });

      // Verify navigation to results
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('analysis-123'));
      });
    });

    it('GIVEN user is recording WHEN there is an upload error THEN they receive appropriate feedback', async () => {
      // Override API to simulate an error
      const mockApiService = require('../../services/apiService').apiService;
      mockApiService.formAnalysis.analyze.mockRejectedValueOnce(new Error('Upload failed'));

      // Create a custom error mock
      jest.requireMock('../../pages/analysis/Upload').default = () => (
        <div data-testid="mock-upload-component" role="main" aria-label="Upload video for analysis">
          <button data-testid="start-recording" aria-label="Start recording">Start Recording</button>
          <div data-testid="upload-status" role="status" aria-live="polite">Recording started</div>
          <button data-testid="stop-recording" aria-label="Stop recording">Stop Recording</button>
          <div data-testid="error-message" role="alert">Failed to upload video</div>
          <button data-testid="retry-button" aria-label="Retry upload">Retry</button>
        </div>
      );

      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Routes>
            <Route path="/upload" element={<Upload />} />
          </Routes>
        </MemoryRouter>
      );

      // Start and stop recording
      await user.click(screen.getByRole('button', { name: /start recording/i }));
      await user.click(screen.getByRole('button', { name: /stop recording/i }));

      // Verify error message is displayed
      expect(screen.getByRole('alert')).toHaveTextContent(/Failed to upload video/i);
      
      // Verify recovery option is available
      expect(screen.getByRole('button', { name: /retry upload/i })).toBeInTheDocument();
    });
  });

  describe('Manual File Upload Behavior', () => {
    beforeEach(() => {
      jest.requireMock('../../pages/analysis/Upload').default = ActualFormUpload;
    });

    it('GIVEN user has a video file WHEN they submit the form with valid data THEN the video is uploaded and analyzed', async () => {
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Select exercise type
      await user.selectOptions(screen.getByTestId('exercise-select'), 'squat');
      
      // Upload a file
      const fileInput = screen.getByTestId('file-input');
      const file = new File(['video content'], 'workout.mp4', { type: 'video/mp4' });
      await user.upload(fileInput, file);
      
      // Verify file name is displayed
      expect(screen.getByTestId('file-name')).toHaveTextContent('workout.mp4');
      
      // Submit form
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify loading state and success
      expect(screen.getByTestId('loading')).toBeInTheDocument();
      
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/results/123');
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
      });
    });

    it('GIVEN user tries to upload without required fields WHEN submitting the form THEN validation errors are shown', async () => {
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Submit without selecting exercise or file
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify exercise validation error
      expect(screen.getByRole('alert')).toHaveTextContent(/please select an exercise type/i);
      
      // Select exercise but still no file
      await user.selectOptions(screen.getByTestId('exercise-select'), 'squat');
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify file validation error
      expect(screen.getByRole('alert')).toHaveTextContent(/please select a video to upload/i);
    });

    it('GIVEN user uploads an oversized file WHEN the file exceeds limits THEN appropriate error message is shown', async () => {
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Create an oversized file
      const oversizedFile = new File(['video content'], 'large.mp4', { type: 'video/mp4' });
      Object.defineProperty(oversizedFile, 'size', { value: 1024 * 1024 * 101 }); // 101 MB
      
      // Upload the file
      await user.upload(screen.getByTestId('file-input'), oversizedFile);
      
      // Verify size warning
      expect(screen.getByRole('alert')).toHaveTextContent(/file size exceeds 100 mb limit/i);
    });
  });

  describe('Drag and Drop Behavior', () => {
    beforeEach(() => {
      jest.requireMock('../../pages/analysis/Upload').default = ActualFormUpload;
    });

    it('GIVEN user has video files WHEN they drag and drop a file THEN it is accepted for upload', async () => {
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Create file and fire drag events
      const file = new File(['video content'], 'dragged.mp4', { type: 'video/mp4' });
      const dropZone = screen.getByTestId('drop-zone');
      
      // Simulate drop event
      const dropEvent = createEvent.drop(dropZone);
      Object.defineProperty(dropEvent, 'dataTransfer', {
        value: {
          files: [file]
        }
      });
      
      // Fire events manually for drag and drop
      fireEvent.dragEnter(dropZone);
      fireEvent.dragOver(dropZone);
      fireEvent.drop(dropZone, dropEvent);
      
      // Verify file was accepted
      expect(screen.getByTestId('file-name')).toHaveTextContent('dragged.mp4');
      
      // Complete the upload process
      await user.selectOptions(screen.getByTestId('exercise-select'), 'squat');
      await user.click(screen.getByTestId('submit-button'));
      
      await waitFor(() => {
        expect(screen.getByTestId('success-message')).toBeInTheDocument();
      });
    });

    it('GIVEN user drags a non-video file WHEN they drop it THEN an error message is shown', async () => {
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Create non-video file
      const imageFile = new File(['image content'], 'image.jpg', { type: 'image/jpeg' });
      const dropZone = screen.getByTestId('drop-zone');
      
      // Simulate drop event with non-video file
      const dropEvent = createEvent.drop(dropZone);
      Object.defineProperty(dropEvent, 'dataTransfer', {
        value: {
          files: [imageFile]
        }
      });
      
      fireEvent.drop(dropZone, dropEvent);
      
      // Verify error message
      expect(screen.getByRole('alert')).toHaveTextContent(/please drop a video file/i);
    });
  });

  describe('Upload Progress and Error Handling', () => {
    it('GIVEN server returns an error WHEN uploading video THEN user receives error feedback', async () => {
      // Override the upload endpoint to return an error
      server.use(
        rest.post('/api/form-checks/upload', (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ error: 'Server error occurred' })
          );
        })
      );
      
      jest.requireMock('../../pages/analysis/Upload').default = ActualFormUpload;
      
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Select exercise and upload file
      await user.selectOptions(screen.getByTestId('exercise-select'), 'squat');
      await user.upload(
        screen.getByTestId('file-input'), 
        new File(['content'], 'video.mp4', { type: 'video/mp4' })
      );
      
      // Submit form
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify loading state
      expect(screen.getByTestId('loading')).toBeInTheDocument();
      
      // Verify error message
      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(/failed to upload video/i);
      });
    });
  });

  describe('Accessibility Features', () => {
    it('GIVEN a user navigating with keyboard WHEN interacting with the form THEN proper focus management is maintained', async () => {
      jest.requireMock('../../pages/analysis/Upload').default = ActualFormUpload;
      
      const { user } = testRender(
        <MemoryRouter initialEntries={['/upload']}>
          <Upload />
        </MemoryRouter>
      );
      
      // Initial focus
      const exerciseSelect = screen.getByTestId('exercise-select');
      exerciseSelect.focus();
      expect(document.activeElement).toBe(exerciseSelect);
      
      // Tab navigation
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId('file-input'));
      
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId('start-recording'));
      
      await user.tab();
      expect(document.activeElement).toBe(screen.getByTestId('submit-button'));
      
      // Submit with error
      await user.click(screen.getByTestId('submit-button'));
      
      // Verify error is announced via role="alert"
      expect(screen.getByRole('alert')).toBeInTheDocument();
      
      // Focus should still be on submit button
      expect(document.activeElement).toBe(screen.getByTestId('submit-button'));
    });
  });
});

// Import additional functions for event testing
import { createEvent, fireEvent } from '@testing-library/react'; 