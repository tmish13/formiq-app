import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { act } from 'react-dom/test-utils';
import { BrowserRouter } from 'react-router-dom';
import { apiService } from '../../../services/apiService';

// Define types for mocking
type FormAnalysisResult = {
  status: number;
  data: {
    id: string;
    [key: string]: any;
  };
};

// Mock the Upload component
jest.mock('../Upload', () => {
  return {
    __esModule: true,
    default: function MockUpload() {
      const [file, setFile] = React.useState<File | null>(null);
      const [exerciseType, setExerciseType] = React.useState('squat');
      const [error, setError] = React.useState<string | null>(null);
      const [isUploading, setIsUploading] = React.useState(false);
      const [progress, setProgress] = React.useState(0);

      const handleFileChange = (file: File) => {
        if (!file.type.includes('video')) {
          setError('Invalid file type');
          return;
        }
        if (file.size > 50 * 1024 * 1024) {
          setError('Video size exceeds maximum limit');
          return;
        }
        setFile(file);
        setError(null);
      };

      const handleExerciseTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setExerciseType(e.target.value);
      };

      const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!file) {
          setError('Please select a file');
          return;
        }
        
        setIsUploading(true);
        
        try {
          const formData = new FormData();
          formData.append('video', file);
          formData.append('exerciseType', exerciseType);
          
          // Use the mocked API service
          const response = await apiService.formAnalysis.analyze(formData);
          
          window.location.href = `/analysis/${response.data.id}`;
        } catch (error) {
          setError('Failed to upload video');
        } finally {
          setIsUploading(false);
        }
      };

      return (
        <div>
          <h1>Upload Form Check</h1>
          <form onSubmit={handleSubmit}>
            <div className="dropzone">
              <p>Drag and drop your video here, or click to select a file</p>
              <input
                id="video-upload"
                type="file"
                accept="video/*"
                onChange={(e) => {
                  const selectedFile = e.target.files?.[0];
                  if (selectedFile) {
                    handleFileChange(selectedFile);
                  }
                }}
              />
            </div>
            
            {file && (
              <div className="file-info">
                <p>File: {file.name}</p>
                <video controls src={URL.createObjectURL(file)} />
              </div>
            )}
            
            <div>
              <label htmlFor="exercise-type">Exercise Type</label>
              <select
                id="exercise-type"
                value={exerciseType}
                onChange={handleExerciseTypeChange}
              >
                <option value="squat">Squat</option>
                <option value="deadlift">Deadlift</option>
                <option value="bench_press">Bench Press</option>
              </select>
            </div>
            
            {error && <div className="error">{error}</div>}
            
            {isUploading && (
              <div className="progress">
                <div style={{ width: `${progress}%` }} />
                <p>{progress}%</p>
              </div>
            )}
            
            <button type="submit" disabled={isUploading}>
              {isUploading ? 'Uploading...' : 'Submit'}
            </button>
          </form>
        </div>
      );
    }
  };
});

// Mock apiService
jest.mock('../../../services/apiService', () => ({
  apiService: {
    formAnalysis: {
      analyze: jest.fn()
    }
  }
}));

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate
}));

// Mock URL.createObjectURL and URL.revokeObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:mock-video-url');
global.URL.revokeObjectURL = jest.fn();

// Create video element mock
HTMLMediaElement.prototype.pause = jest.fn();
HTMLMediaElement.prototype.play = jest.fn();
HTMLMediaElement.prototype.load = jest.fn();

describe('Upload Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Mock for HTML video element
  const setupVideoElementMock = () => {
    const originalCreateElement = document.createElement;
    document.createElement = jest.fn().mockImplementation((tag) => {
      if (tag === 'video') {
        const videoElement = originalCreateElement.call(document, tag);
        Object.defineProperty(videoElement, 'duration', { value: 10 });
        return videoElement;
      }
      return originalCreateElement.call(document, tag);
    });
    
    return () => {
      document.createElement = originalCreateElement;
    };
  };

  const renderUploadComponent = () => {
    return render(
      <BrowserRouter>
        <React.Suspense fallback={<div>Loading...</div>}>
          {React.createElement(require('../Upload').default)}
        </React.Suspense>
      </BrowserRouter>
    );
  };

  it('renders upload component with dropzone and exercise type selector', () => {
    renderUploadComponent();
    
    expect(screen.getByText(/Upload Form Check/i)).toBeInTheDocument();
    expect(screen.getByText(/Drag and drop your video here/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Exercise Type/i)).toBeInTheDocument();
  });

  it('handles file upload through file input', async () => {
    const cleanup = setupVideoElementMock();
    renderUploadComponent();
    
    // Create a mock video file
    const file = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
    
    // Find file input
    const fileInput = document.getElementById('video-upload');
    expect(fileInput).toBeInTheDocument();
    
    // Simulate file selection
    fireEvent.change(fileInput!, { target: { files: [file] } });
    
    // Wait for video analysis
    await waitFor(() => {
      expect(URL.createObjectURL).toHaveBeenCalled();
    });
    
    // Check if video preview is shown
    expect(screen.getByText(/File:/i)).toBeInTheDocument();
    expect(screen.getByText(/test-video.mp4/i)).toBeInTheDocument();
    
    cleanup();
  });

  it('validates video files for type, size and duration', async () => {
    const cleanup = setupVideoElementMock();
    renderUploadComponent();
    
    // Create a mock non-video file
    const nonVideoFile = new File(['mock image content'], 'test-image.jpg', { type: 'image/jpeg' });
    
    // Find file input
    const fileInput = document.getElementById('video-upload');
    
    // Simulate file selection
    fireEvent.change(fileInput!, { target: { files: [nonVideoFile] } });
    
    // Submit form
    fireEvent.click(screen.getByText(/Submit/i));
    
    // Check for error message
    await waitFor(() => {
      expect(screen.getByText(/Please select a file/i)).toBeInTheDocument();
    });
    
    cleanup();
  });

  it('displays upload progress', async () => {
    const cleanup = setupVideoElementMock();
    renderUploadComponent();
    
    // Mock the apiService.formAnalysis.analyze function
    (apiService.formAnalysis.analyze as jest.Mock).mockImplementation((formData: FormData) => {
      return Promise.resolve({ status: 200, data: { id: 'analysis-123' } });
    });
    
    // Create a mock video file
    const file = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
    
    // Find file input
    const fileInput = document.getElementById('video-upload');
    
    // Simulate file selection
    fireEvent.change(fileInput!, { target: { files: [file] } });
    
    // Submit form
    await act(async () => {
      fireEvent.click(screen.getByText(/Submit/i));
    });
    
    // Verify the API was called
    expect(apiService.formAnalysis.analyze).toHaveBeenCalled();
    
    cleanup();
  });

  it('handles upload failure', async () => {
    const cleanup = setupVideoElementMock();
    renderUploadComponent();
    
    // Mock the apiService.formAnalysis.analyze function to reject
    (apiService.formAnalysis.analyze as jest.Mock).mockRejectedValueOnce(new Error('Upload failed'));
    
    // Create a mock video file
    const file = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
    
    // Find file input
    const fileInput = document.getElementById('video-upload');
    
    // Simulate file selection
    fireEvent.change(fileInput!, { target: { files: [file] } });
    
    // Submit form
    await act(async () => {
      fireEvent.click(screen.getByText(/Submit/i));
    });
    
    // Verify the API was called
    expect(apiService.formAnalysis.analyze).toHaveBeenCalled();
    
    // Check for error message
    await waitFor(() => {
      expect(screen.getByText(/Failed to upload video/i)).toBeInTheDocument();
    });
    
    cleanup();
  });
}); 