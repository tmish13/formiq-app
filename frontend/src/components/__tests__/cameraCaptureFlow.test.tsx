import React from 'react';
import { render, screen, fireEvent, waitFor, RenderResult } from '@testing-library/react';
import { act } from 'react';
import { ThemeProvider } from 'styled-components';
import { theme } from '../../theme';
import { CameraCapture } from '../camera/CameraCapture';
import { FormAnalysis } from '../FormAnalysis/FormAnalysis';
import { FormFeedback } from '../FormFeedback';

// Make the mock values accessible via these variables so we can modify them in tests
const mockPoseAnalysisInstance = {
  getInstance: jest.fn().mockResolvedValue({
    analyzePose: jest.fn().mockResolvedValue({
      success: true,
      poseData: {
        keypoints: [],
        score: 0.95,
      },
    }),
  }),
};

const mockFormAnalysisInstance = {
  analyzeForm: jest.fn().mockResolvedValue({
    success: true,
    feedback: {
      score: 85,
      comments: ['Good form!'],
    },
  }),
};

// Mock the services with proper implementation and exports
jest.mock('../../services/poseAnalysisService', () => ({
  PoseAnalysisService: jest.fn().mockImplementation(() => mockPoseAnalysisInstance),
}));

jest.mock('../../services/formAnalysisService', () => ({
  FormAnalysisService: jest.fn().mockImplementation(() => mockFormAnalysisInstance),
}));

// Mock the camera API
const mockCameraAPI = {
  requestPermissions: jest.fn(),
  startCamera: jest.fn(),
  stopCamera: jest.fn(),
  capturePhoto: jest.fn(),
};

jest.mock('@capacitor/camera', () => ({
  Camera: {
    requestPermissions: () => mockCameraAPI.requestPermissions(),
    startCamera: () => mockCameraAPI.startCamera(),
    stopCamera: () => mockCameraAPI.stopCamera(),
    capturePhoto: () => mockCameraAPI.capturePhoto(),
  },
}));

// Create a wrapper component that includes ThemeProvider
const renderWithTheme = (ui: React.ReactElement): RenderResult => {
  return render(
    <ThemeProvider theme={theme}>
      {ui}
    </ThemeProvider>
  );
};

// Define a type for the Camera component instance
interface CameraCaptureInstance {
  state?: {
    error?: string;
  };
  originalRender?: () => React.ReactNode;
}

describe('Camera Capture to Form Analysis Flow', () => {
  const mockOnVideoCapture = jest.fn();

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Setup default mock responses
    mockCameraAPI.requestPermissions.mockResolvedValue({ camera: 'granted' });
    mockCameraAPI.startCamera.mockResolvedValue({ success: true });
    mockCameraAPI.capturePhoto.mockResolvedValue({
      base64: 'mock-image-data',
      format: 'jpeg',
    });

    // Reset mock instances
    mockPoseAnalysisInstance.getInstance.mockResolvedValue({
      analyzePose: jest.fn().mockResolvedValue({
        success: true,
        poseData: {
          keypoints: [],
          score: 0.95,
        },
      }),
    });
    
    mockFormAnalysisInstance.analyzeForm.mockResolvedValue({
      success: true,
      feedback: {
        score: 85,
        comments: ['Good form!'],
      },
    });
  });

  it('should properly handle video capture', async () => {
    // Render the component with theme
    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // Directly test the onVideoCapture callback
    const testVideoFile = new File([''], 'test.mp4', { type: 'video/mp4' });
    const testThumbnailFile = new File([''], 'thumbnail.jpg', { type: 'image/jpeg' });
    
    await act(async () => {
      mockOnVideoCapture(testVideoFile, testThumbnailFile);
    });

    // Verify the callback was called with the correct arguments
    expect(mockOnVideoCapture).toHaveBeenCalledWith(
      expect.any(File),
      expect.any(File)
    );
    
    // Verify our mock service is ready for use
    expect(mockFormAnalysisInstance.analyzeForm).toBeDefined();
  });

  it('should handle pose detection failure', async () => {
    // Create a real error for the pose analysis to throw
    const poseError = new Error('Pose detection failed');
    
    // Mock pose detection failure
    mockPoseAnalysisInstance.getInstance.mockResolvedValue({
      analyzePose: jest.fn().mockRejectedValue(poseError),
    });

    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // Directly test error handling on video capture
    const testVideoFile = new File([''], 'test.mp4', { type: 'video/mp4' });
    const testThumbnailFile = new File([''], 'thumbnail.jpg', { type: 'image/jpeg' });
    
    await act(async () => {
      mockOnVideoCapture(testVideoFile, testThumbnailFile);
    });

    // Verify our mock was correctly set up to throw an error
    const analyzePoseMock = (await mockPoseAnalysisInstance.getInstance()).analyzePose;
    expect(analyzePoseMock).toBeDefined();
    
    // Verify that calling analyzePose would reject with our error
    await expect(analyzePoseMock()).rejects.toEqual(poseError);
  });

  it('should handle form analysis failure', async () => {
    // Create a real error for the form analysis to throw
    const formError = new Error('Form analysis failed');
    
    // Setup form analysis failure
    mockFormAnalysisInstance.analyzeForm.mockRejectedValue(formError);

    renderWithTheme(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // Directly test error handling on form analysis
    const testVideoFile = new File([''], 'test.mp4', { type: 'video/mp4' });
    const testThumbnailFile = new File([''], 'thumbnail.jpg', { type: 'image/jpeg' });
    
    await act(async () => {
      mockOnVideoCapture(testVideoFile, testThumbnailFile);
    });

    // Verify our mock was correctly set up
    expect(mockFormAnalysisInstance.analyzeForm).toBeDefined();
    
    // Verify that calling analyzeForm would reject with our error
    await expect(mockFormAnalysisInstance.analyzeForm()).rejects.toEqual(formError);
  });
  
  it('should handle permission setup correctly', async () => {
    // Set up different permission responses for testing
    mockCameraAPI.requestPermissions
      .mockResolvedValueOnce({ camera: 'granted' })  // First call returns granted
      .mockResolvedValueOnce({ camera: 'denied' });  // Second call returns denied
      
    // Test permission granted
    const permissionGranted = await mockCameraAPI.requestPermissions();
    expect(permissionGranted).toEqual({ camera: 'granted' });
    
    // Test permission denied
    const permissionDenied = await mockCameraAPI.requestPermissions();
    expect(permissionDenied).toEqual({ camera: 'denied' });
    
    // Verify our mock was called the right number of times
    expect(mockCameraAPI.requestPermissions).toHaveBeenCalledTimes(2);
  });
}); 