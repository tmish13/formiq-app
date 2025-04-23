import React, { ReactNode } from 'react';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider } from 'styled-components';
import { CameraCapture } from '../CameraCapture';
import { mockThemeWithFallbacks as mockTheme } from '../../../../tests/__mocks__/mockTheme';

// Create mock for Capacitor
jest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: jest.fn().mockReturnValue(false),
    getPlatform: jest.fn().mockReturnValue('web')
  }
}));

// Mock the camera API
jest.mock('@capacitor/camera', () => ({
  Camera: {
    getPhoto: jest.fn().mockResolvedValue({
      webPath: 'mock-video-path',
      path: 'mock-video-path',
      format: 'mp4'
    })
  },
  CameraResultType: {
    Uri: 'uri'
  },
  CameraSource: {
    Prompt: 'prompt'
  }
}));

// Mock File API for thumbnail creation
global.URL.createObjectURL = jest.fn(() => 'mock-video-url');
global.URL.revokeObjectURL = jest.fn();

// Components that we are testing
const MockVideoPreview = (props: any) => <video data-testid="video-preview" {...props} />;
const MockCaptureButton = (props: any) => <button data-testid="capture-button" {...props}>{props.children}</button>;
const MockActionButton = (props: any) => <button data-testid="action-button" {...props}>{props.children}</button>;
const MockErrorMessage = (props: any) => <div data-testid="error-message" {...props}>{props.children}</div>;

// Mock FileInput component
const MockFileInput = (props: any) => <input data-testid="file-input" {...props} />;

// Mock styled-components
jest.mock('styled-components', () => {
  const actual = jest.requireActual('styled-components');
  return {
    ...actual,
    styled: {
      div: () => (props: any) => <div {...props} />,
      video: () => MockVideoPreview,
      button: (_: any) => MockCaptureButton,
      input: () => MockFileInput
    },
    ThemeProvider: ({ children }: { children: ReactNode }) => <div data-testid="theme-provider">{children}</div>,
  };
});

// Mock FormTipsOverlay
jest.mock('../FormTipsOverlay', () => ({
  FormTipsOverlay: ({ tips, score }: { tips: any[], score: number }) => (
    <div data-testid="form-tips-overlay">
      <div data-testid="form-tips">{JSON.stringify(tips)}</div>
      <div data-testid="form-score">{score}</div>
    </div>
  ),
  FormTip: ({ message }: { message: string }) => <div data-testid="form-tip">{message}</div>
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

describe('CameraCapture Component', () => {
  const mockOnVideoCapture = jest.fn();
  const defaultProps = {
    onVideoCapture: mockOnVideoCapture,
    maxDuration: 30,
    formTips: [{ id: '1', message: 'Keep your back straight', timingMs: 1000 }],
    formScore: 85
  };

  beforeEach(() => {
    jest.clearAllMocks();
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

  it('renders the camera capture component correctly', () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );

    expect(screen.getByTestId('capture-button')).toBeInTheDocument();
    expect(screen.getByTestId('capture-button')).toHaveTextContent('Start Recording');
  });

  it('starts recording when clicking the capture button on web platform', async () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );

    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
      video: true,
      audio: true
    });

    // Wait for the MediaRecorder to be created and start recording
    await waitFor(() => {
      expect(screen.getByTestId('video-preview')).toBeInTheDocument();
    });
  });

  it('shows error message when camera access is denied', async () => {
    // Mock getUserMedia to reject with an error
    navigator.mediaDevices.getUserMedia = jest.fn().mockRejectedValue(
      new Error('Permission denied')
    );

    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );

    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByText(/Failed to access camera/)).toBeInTheDocument();
    });
  });

  it('handles file upload when selecting a video file', async () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );

    // Find the file input
    const fileInput = screen.getByTestId('file-input');
    
    // Create a mock video file
    const file = new File(['test video content'], 'test-video.mp4', { type: 'video/mp4' });
    
    // Simulate file selection
    fireEvent.change(fileInput, { target: { files: [file] } });

    // Mock the video element and create functions for loading
    const videoElement = document.createElement('video');
    
    // Force videoElement behaviors
    Object.defineProperty(HTMLVideoElement.prototype, 'videoWidth', { configurable: true, value: 640 });
    Object.defineProperty(HTMLVideoElement.prototype, 'videoHeight', { configurable: true, value: 480 });
    
    // Wait for the onVideoCapture to be called with the file
    await waitFor(() => {
      expect(mockOnVideoCapture).toHaveBeenCalledWith(
        expect.any(File),
        expect.any(File)
      );
    });
  });

  it('allows canceling the recording', async () => {
    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );

    // First click to start recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Wait for the video to be captured
    await waitFor(() => {
      expect(screen.getByTestId('video-preview')).toBeInTheDocument();
    });

    // Find the cancel button and click it
    const cancelButton = screen.getByText('Cancel');
    fireEvent.click(cancelButton);

    // Check that the video preview is reset
    expect(URL.revokeObjectURL).toHaveBeenCalled();
    expect(screen.getByTestId('capture-button')).toHaveTextContent('Start Recording');
  });

  it('shows form tips overlay during recording', async () => {
    // Mock the Capacitor platform to be native (mobile)
    const CapacitorModule = require('@capacitor/core');
    CapacitorModule.Capacitor.isNativePlatform.mockReturnValueOnce(true);

    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} isRecording={true} />
      </ThemeProvider>
    );

    // Start recording
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Check for form tips overlay during recording
    expect(screen.getByTestId('form-tips-overlay')).toBeInTheDocument();
  });

  it('handles retry after an error', async () => {
    // Mock getUserMedia to reject with an error
    navigator.mediaDevices.getUserMedia = jest.fn()
      .mockRejectedValueOnce(new Error('Permission denied'))
      .mockResolvedValueOnce({
        getTracks: () => [{
          stop: jest.fn()
        }]
      });

    render(
      <ThemeProvider theme={mockTheme}>
        <CameraCapture {...defaultProps} />
      </ThemeProvider>
    );

    // Click to start recording, which will fail
    const captureButton = screen.getByTestId('capture-button');
    fireEvent.click(captureButton);

    // Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByText(/Failed to access camera/)).toBeInTheDocument();
    });

    // Click the button again to retry
    fireEvent.click(captureButton);

    // Verify that getUserMedia was called again
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledTimes(2);
  });
}); 