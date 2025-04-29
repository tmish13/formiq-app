import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider } from 'styled-components';
import { CameraCapture } from '../CameraCapture';
import { FormAnalysis } from '../../FormAnalysis/FormAnalysis';
import { formAnalysisService } from '../../../services/formAnalysisService';
import { mockTheme } from '../../../theme/mockTheme';
import { Camera } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';

// Create a proper mock theme that matches DefaultTheme
const testTheme = {
  ...mockTheme,
  transitions: {
    duration: {
      shortest: '150ms',
      shorter: '200ms',
      short: '250ms',
      standard: '300ms',
      complex: '375ms',
      enteringScreen: '225ms',
      leavingScreen: '195ms',
      medium: '300ms'
    },
    easing: {
      easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
      easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
      easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
      sharp: 'cubic-bezier(0.4, 0, 0.6, 1)'
    }
  }
};

// Mock styled-components
jest.mock('styled-components', () => {
  const actual = jest.requireActual('styled-components');
  return {
    ...actual,
    ThemeProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="theme-provider">{children}</div>,
  };
});

// Mock the form analysis service
jest.mock('../../../services/formAnalysisService', () => ({
  formAnalysisService: {
    analyzeForm: jest.fn(),
    startAnalysis: jest.fn(),
    stopAnalysis: jest.fn()
  }
}));

// Mock pose detection
jest.mock('@tensorflow-models/pose-detection', () => ({
  SupportedModels: {
    MoveNet: 'movenet'
  },
  movenet: {
    modelType: {
      SINGLEPOSE_LIGHTNING: 'lightning'
    }
  },
  createDetector: jest.fn().mockResolvedValue({
    estimatePoses: jest.fn().mockResolvedValue([{
      keypoints: [
        { name: 'left_hip', x: 100, y: 100, score: 0.9 },
        { name: 'left_knee', x: 100, y: 200, score: 0.9 },
        { name: 'left_ankle', x: 100, y: 300, score: 0.9 }
      ],
      score: 0.9
    }])
  })
}));

// Mock MediaRecorder
class MockMediaRecorder {
  stream: MediaStream;
  state: string;
  ondataavailable: ((e: any) => void) | null;
  onstop: (() => void) | null;

  constructor(stream: MediaStream) {
    this.stream = stream;
    this.state = 'inactive';
    this.ondataavailable = null;
    this.onstop = null;
  }

  start() {
    this.state = 'recording';
    if (this.ondataavailable) {
      this.ondataavailable({ data: new Blob(['test'], { type: 'video/mp4' }) });
    }
  }

  stop() {
    this.state = 'inactive';
    if (this.onstop) this.onstop();
  }
}

// @ts-ignore - mock MediaRecorder globally
global.MediaRecorder = MockMediaRecorder;

describe('Camera Capture → Form Analysis Flow', () => {
  const mockOnVideoCapture = jest.fn();
  const defaultProps = {
    onVideoCapture: mockOnVideoCapture,
    maxDuration: 30,
    formTips: [{ id: '1', message: 'Keep your back straight', timingMs: 1000 }],
    formScore: 85
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset mock implementations
    (formAnalysisService.analyzeForm as jest.Mock).mockResolvedValue({
      score: 0.95,
      feedback: [
        {
          type: 'posture',
          message: 'Good form!',
          severity: 'success',
        },
        {
          type: 'alignment',
          message: 'Keep your back straight',
          severity: 'info',
        },
      ],
      poseAnalysis: {
        keypoints: [
          { x: 0, y: 0, score: 1, name: 'nose' },
          { x: 10, y: 10, score: 1, name: 'left_shoulder' },
          { x: -10, y: 10, score: 1, name: 'right_shoulder' },
        ],
        score: 0.9,
        angles: {
          leftElbow: 90,
          rightElbow: 90,
          leftShoulder: 45,
          rightShoulder: 45,
          leftHip: 180,
          rightHip: 180,
          leftKnee: 180,
          rightKnee: 180,
          leftAnkle: 90,
          rightAnkle: 90,
        },
      },
    });

    // Mock navigator.mediaDevices.getUserMedia
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: {
        getUserMedia: jest.fn().mockResolvedValue({
          getTracks: () => [{
            stop: jest.fn()
          }]
        })
      },
      writable: true
    });
  });

  it('completes full camera capture to form analysis flow', async () => {
    render(
      <ThemeProvider theme={testTheme}>
        <div>
          <CameraCapture {...defaultProps} />
          <FormAnalysis />
        </div>
      </ThemeProvider>
    );

    // Start recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Wait for video preview
    await waitFor(() => {
      expect(screen.getByTestId('video-preview')).toBeInTheDocument();
    });

    // Stop recording after 2 seconds
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      fireEvent.click(captureButton);
    });

    // Verify video capture callback
    expect(mockOnVideoCapture).toHaveBeenCalledWith(expect.any(Blob));

    // Verify form analysis was triggered
    expect(formAnalysisService.analyzeForm).toHaveBeenCalled();

    // Verify feedback is displayed
    await waitFor(() => {
      expect(screen.getByText('Good form!')).toBeInTheDocument();
      expect(screen.getByText('Keep your back straight')).toBeInTheDocument();
    });
  });

  it('handles camera permission denial gracefully', async () => {
    // Mock getUserMedia to reject with permission denied error
    Object.defineProperty(global.navigator, 'mediaDevices', {
      value: {
        getUserMedia: jest.fn().mockRejectedValue(new Error('Permission denied'))
      },
      writable: true
    });
    
    render(
      <ThemeProvider theme={testTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );
    
    // Start recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);
    
    // Should show permission denied message
    await waitFor(() => {
      expect(screen.getByText(/camera permission/i)).toBeInTheDocument();
    });
  });

  it('handles form analysis failure gracefully', async () => {
    // Mock form analysis to fail
    (formAnalysisService.analyzeForm as jest.Mock).mockRejectedValueOnce(
      new Error('Analysis failed')
    );
    
    render(
      <ThemeProvider theme={testTheme}>
        <div>
          <CameraCapture {...defaultProps} />
          <FormAnalysis />
        </div>
      </ThemeProvider>
    );
    
    // Start and stop recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      fireEvent.click(captureButton);
    });
    
    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/analysis failed/i)).toBeInTheDocument();
    });
  });

  it('saves analysis results correctly', async () => {
    // Mock successful form analysis
    (formAnalysisService.analyzeForm as jest.Mock).mockResolvedValueOnce({
      score: 0.95,
      feedback: [
        {
          type: 'posture',
          message: 'Good form!',
          severity: 'success',
        }
      ],
      poseAnalysis: {
        keypoints: [
          { x: 0, y: 0, score: 1, name: 'nose' },
          { x: 10, y: 10, score: 1, name: 'left_shoulder' },
          { x: -10, y: 10, score: 1, name: 'right_shoulder' },
        ],
        score: 0.9,
        angles: {
          leftElbow: 90,
          rightElbow: 90,
          leftShoulder: 45,
          rightShoulder: 45,
          leftHip: 180,
          rightHip: 180,
          leftKnee: 180,
          rightKnee: 180,
          leftAnkle: 90,
          rightAnkle: 90,
        },
      },
    });

    // Mock save function
    const mockSaveAnalysis = jest.fn().mockResolvedValue({ success: true });
    (formAnalysisService.saveAnalysis as jest.Mock) = mockSaveAnalysis;
    
    render(
      <ThemeProvider theme={testTheme}>
        <div>
          <CameraCapture {...defaultProps} />
          <FormAnalysis />
        </div>
      </ThemeProvider>
    );
    
    // Start and stop recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 2000));
      fireEvent.click(captureButton);
    });
    
    // Wait for analysis to complete
    await waitFor(() => {
      expect(screen.getByText('Good form!')).toBeInTheDocument();
    });
    
    // Click save button
    const saveButton = screen.getByRole('button', { name: /save analysis/i });
    fireEvent.click(saveButton);
    
    // Verify save was called
    expect(mockSaveAnalysis).toHaveBeenCalledWith(expect.objectContaining({
      confidence: expect.any(Number),
      isReliable: expect.any(Boolean),
      keypoints: expect.any(Array),
      angles: expect.any(Object),
      feedback: expect.any(Array),
      timestamp: expect.any(Number)
    }));
  });

  it('completes camera capture and pose detection within performance budget', async () => {
    const startTime = performance.now();
    
    render(
      <ThemeProvider theme={testTheme}>
        <div>
          <CameraCapture {...defaultProps} />
          <FormAnalysis />
        </div>
      </ThemeProvider>
    );

    // Start recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Wait for video preview and pose detection
    await waitFor(() => {
      expect(screen.getByTestId('video-preview')).toBeInTheDocument();
      expect(formAnalysisService.analyzeForm).toHaveBeenCalled();
    });

    const endTime = performance.now();
    const duration = endTime - startTime;
    
    expect(duration).toBeLessThan(2000); // 2 seconds budget
  });

  it('completes form submission within performance budget', async () => {
    render(
      <ThemeProvider theme={testTheme}>
        <div>
          <CameraCapture {...defaultProps} />
          <FormAnalysis />
        </div>
      </ThemeProvider>
    );

    // Start recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Wait for video preview
    await waitFor(() => {
      expect(screen.getByTestId('video-preview')).toBeInTheDocument();
    });

    // Stop recording and measure form submission time
    const startTime = performance.now();
    fireEvent.click(captureButton);

    await waitFor(() => {
      expect(formAnalysisService.analyzeForm).toHaveBeenCalled();
    });

    const endTime = performance.now();
    const duration = endTime - startTime;
    
    expect(duration).toBeLessThan(500); // 500ms budget
  });

  it('renders form analysis within performance budget', async () => {
    render(
      <ThemeProvider theme={testTheme}>
        <div>
          <CameraCapture {...defaultProps} />
          <FormAnalysis />
        </div>
      </ThemeProvider>
    );

    // Start and stop recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);
    
    await waitFor(() => {
      expect(screen.getByTestId('video-preview')).toBeInTheDocument();
    });

    const startTime = performance.now();
    fireEvent.click(captureButton);

    // Wait for form analysis to render
    await waitFor(() => {
      expect(screen.getByText('Good form!')).toBeInTheDocument();
      expect(screen.getByText('Keep your back straight')).toBeInTheDocument();
    });

    const endTime = performance.now();
    const duration = endTime - startTime;
    
    expect(duration).toBeLessThan(3000); // 3 seconds budget
  });
}); 