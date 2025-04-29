import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import { CameraCapture } from '../camera/CameraCapture';
import { FormAnalysis } from '../FormAnalysis/FormAnalysis';
import { FormFeedback } from '../FormFeedback';
import { PoseAnalysisService } from '../../services/poseAnalysisService';
import { FormAnalysisService } from '../../services/formAnalysisService';

// Mock the services
jest.mock('../../services/poseAnalysisService', () => ({
  PoseAnalysisService: jest.fn().mockImplementation(() => ({
    getInstance: jest.fn().mockResolvedValue({
      analyzePose: jest.fn().mockResolvedValue({
        success: true,
        poseData: {
          keypoints: [],
          score: 0.95,
        },
      }),
    }),
  })),
}));

jest.mock('../../services/formAnalysisService', () => ({
  FormAnalysisService: jest.fn().mockImplementation(() => ({
    analyzeForm: jest.fn().mockResolvedValue({
      success: true,
      feedback: {
        score: 85,
        comments: ['Good form!'],
      },
    }),
  })),
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
  });

  it('should complete the full camera capture to form analysis flow', async () => {
    // Render the camera capture component
    render(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // 1. Check camera permissions
    await waitFor(() => {
      expect(mockCameraAPI.requestPermissions).toHaveBeenCalled();
    });

    // 2. Start camera
    const startButton = screen.getByRole('button', { name: /start camera/i });
    await act(async () => {
      fireEvent.click(startButton);
    });

    await waitFor(() => {
      expect(mockCameraAPI.startCamera).toHaveBeenCalled();
    });

    // 3. Capture photo
    const captureButton = screen.getByRole('button', { name: /capture/i });
    await act(async () => {
      fireEvent.click(captureButton);
    });

    await waitFor(() => {
      expect(mockCameraAPI.capturePhoto).toHaveBeenCalled();
    });

    // 4. Verify video capture callback was called
    await waitFor(() => {
      expect(mockOnVideoCapture).toHaveBeenCalledWith(
        expect.any(File),
        expect.any(File)
      );
    });

    // 5. Verify form analysis was triggered
    const formAnalysisInstance = (FormAnalysisService as unknown as jest.Mock).mock.results[0].value;
    await waitFor(() => {
      expect(formAnalysisInstance.analyzeForm).toHaveBeenCalledWith(
        expect.any(Object)
      );
    });

    // 6. Verify feedback is displayed
    await waitFor(() => {
      expect(screen.getByText(/Good form!/i)).toBeInTheDocument();
      expect(screen.getByText(/85/i)).toBeInTheDocument();
    });
  });

  it('should handle camera permission denied', async () => {
    // Mock camera permission denied
    mockCameraAPI.requestPermissions.mockResolvedValue({ camera: 'denied' });

    render(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    await waitFor(() => {
      expect(screen.getByText(/camera permission denied/i)).toBeInTheDocument();
    });
  });

  it('should handle pose detection failure', async () => {
    // Mock pose detection failure
    const poseAnalysisInstance = (PoseAnalysisService as unknown as jest.Mock).mock.results[0].value;
    poseAnalysisInstance.getInstance.mockResolvedValue({
      analyzePose: jest.fn().mockRejectedValue(new Error('Pose detection failed')),
    });

    render(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // Complete camera capture
    const startButton = screen.getByRole('button', { name: /start camera/i });
    await act(async () => {
      fireEvent.click(startButton);
    });

    const captureButton = screen.getByRole('button', { name: /capture/i });
    await act(async () => {
      fireEvent.click(captureButton);
    });

    // Verify error handling
    await waitFor(() => {
      expect(screen.getByText(/pose detection failed/i)).toBeInTheDocument();
    });
  });

  it('should handle form analysis failure', async () => {
    // Mock form analysis failure
    const formAnalysisInstance = (FormAnalysisService as unknown as jest.Mock).mock.results[0].value;
    formAnalysisInstance.analyzeForm.mockRejectedValue(
      new Error('Form analysis failed')
    );

    render(<CameraCapture onVideoCapture={mockOnVideoCapture} />);

    // Complete camera capture and pose detection
    const startButton = screen.getByRole('button', { name: /start camera/i });
    await act(async () => {
      fireEvent.click(startButton);
    });

    const captureButton = screen.getByRole('button', { name: /capture/i });
    await act(async () => {
      fireEvent.click(captureButton);
    });

    // Verify error handling
    await waitFor(() => {
      expect(screen.getByText(/form analysis failed/i)).toBeInTheDocument();
    });
  });
}); 