/**
 * Consolidated behaviour-first test for Camera Upload Flow
 *
 * Uses:
 *   - testRender() utility for full providers
 *   - MSW handlers for network
 *   - userEvent for interactions
 */
import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { rest } from 'msw';
import { server } from '../../tests/utils/server';
import { testRender } from '../../tests/utils/testRender';
import UploadComponent from '../../src/components/Upload';
import CameraCapture from '../../src/components/camera/CameraCapture';
import UploadPage from '../../src/pages/Upload';

// Mock video elements and MediaStream
const mockMediaStream = {} as MediaStream;
const mockVideoElement = {
  play: jest.fn(),
  pause: jest.fn(),
  srcObject: null,
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
};

// Mock navigator.mediaDevices
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: jest.fn().mockResolvedValue(mockMediaStream),
    enumerateDevices: jest.fn().mockResolvedValue([{ kind: 'videoinput', deviceId: 'mock-id' }]),
  },
  writable: true,
});

// Mock the file upload mechanism
const mockFileUpload = (file = new File(['test'], 'test.mp4', { type: 'video/mp4' })) => {
  return {
    target: {
      files: [file],
    },
  };
};

// Mock the upload service
jest.mock('../../src/services/uploadService', () => ({
  uploadService: {
    uploadVideo: jest.fn().mockResolvedValue({ id: 'mock-video-id', url: 'mock-url' }),
    getUploadStatus: jest.fn().mockResolvedValue({ status: 'completed' }),
  },
}));

// SETUP MSW
server.use(
  rest.post('/api/upload', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: 'mock-upload-id',
        status: 'processing',
      })
    );
  }),
  rest.get('/api/upload/:id/status', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        id: req.params.id,
        status: 'completed',
        url: 'https://example.com/video.mp4',
      })
    );
  })
);

describe('Camera Upload Flow', () => {
  // Reset mocks between tests
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock element access
    global.document.createElement = jest.fn().mockImplementation((tag) => {
      if (tag === 'video') {
        return mockVideoElement as unknown as HTMLVideoElement;
      }
      return document.createElement(tag);
    });
  });

  describe('File Selection UI', () => {
    it('should allow user to select a video file', async () => {
      const { user } = testRender(<UploadComponent />);
      const fileInput = screen.getByLabelText(/select video/i);
      await user.upload(fileInput, new File(['test'], 'test.mp4', { type: 'video/mp4' }));
      
      expect(fileInput.files?.[0]?.name).toBe('test.mp4');
    });

    it('should show error for invalid file type', async () => {
      const { user } = testRender(<UploadComponent />);
      const fileInput = screen.getByLabelText(/select video/i);
      await user.upload(fileInput, new File(['test'], 'test.txt', { type: 'text/plain' }));
      
      expect(await screen.findByText(/invalid file type/i)).toBeInTheDocument();
    });

    it('should display video preview after selection', async () => {
      const { user } = testRender(<UploadComponent />);
      const fileInput = screen.getByLabelText(/select video/i);
      await user.upload(fileInput, new File(['test'], 'test.mp4', { type: 'video/mp4' }));
      
      expect(await screen.findByTestId('video-preview')).toBeInTheDocument();
    });
  });

  describe('Camera Capture', () => {
    it('should initialize camera on component mount', async () => {
      testRender(<CameraCapture />);
      
      await waitFor(() => {
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      });
    });

    it('should start recording when record button is clicked', async () => {
      const { user } = testRender(<CameraCapture />);
      
      // Wait for camera initialization
      await waitFor(() => {
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      });
      
      // Find and click record button
      const recordButton = screen.getByRole('button', { name: /record/i });
      await user.click(recordButton);
      
      // Expect recording state to be active
      expect(await screen.findByText(/recording/i)).toBeInTheDocument();
    });

    it('should stop recording when stop button is clicked', async () => {
      const { user } = testRender(<CameraCapture />);
      
      // Wait for camera initialization
      await waitFor(() => {
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      });
      
      // Start recording
      const recordButton = screen.getByRole('button', { name: /record/i });
      await user.click(recordButton);
      
      // Stop recording
      const stopButton = await screen.findByRole('button', { name: /stop/i });
      await user.click(stopButton);
      
      // Expect preview state
      expect(await screen.findByText(/preview/i)).toBeInTheDocument();
    });

    it('should display pose overlay during recording', async () => {
      const { user } = testRender(<CameraCapture poseDetection={true} />);
      
      // Wait for camera initialization
      await waitFor(() => {
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      });
      
      // Start recording
      const recordButton = screen.getByRole('button', { name: /record/i });
      await user.click(recordButton);
      
      // Check for pose overlay
      expect(await screen.findByTestId('pose-overlay')).toBeInTheDocument();
    });
  });

  describe('Upload Progress', () => {
    it('should show progress indicator during upload', async () => {
      const { user } = testRender(<UploadPage />);
      
      // Select file
      const fileInput = screen.getByLabelText(/select video/i);
      await user.upload(fileInput, new File(['test'], 'test.mp4', { type: 'video/mp4' }));
      
      // Upload file
      const uploadButton = screen.getByRole('button', { name: /upload/i });
      await user.click(uploadButton);
      
      // Check for progress indicator
      expect(await screen.findByRole('progressbar')).toBeInTheDocument();
    });

    it('should navigate to results page after successful upload', async () => {
      const mockNavigate = jest.fn();
      jest.mock('react-router-dom', () => ({
        ...jest.requireActual('react-router-dom'),
        useNavigate: () => mockNavigate,
      }));
      
      const { user } = testRender(<UploadPage />);
      
      // Select file
      const fileInput = screen.getByLabelText(/select video/i);
      await user.upload(fileInput, new File(['test'], 'test.mp4', { type: 'video/mp4' }));
      
      // Upload file
      const uploadButton = screen.getByRole('button', { name: /upload/i });
      await user.click(uploadButton);
      
      // Wait for upload completion
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/results/mock-upload-id');
      });
    });
  });

  describe('Camera Permission Flow', () => {
    it('should show fallback UI when camera permission is denied', async () => {
      // Mock permission denied
      Object.defineProperty(global.navigator, 'mediaDevices', {
        value: {
          getUserMedia: jest.fn().mockRejectedValue(new Error('Permission denied')),
          enumerateDevices: jest.fn().mockResolvedValue([]),
        },
        writable: true,
      });
      
      testRender(<CameraCapture />);
      
      // Check for fallback UI
      expect(await screen.findByText(/camera access denied/i)).toBeInTheDocument();
    });
  });

  describe('Recording Timer', () => {
    it('should display recording timer during active recording', async () => {
      const { user } = testRender(<CameraCapture />);
      
      // Wait for camera initialization
      await waitFor(() => {
        expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
      });
      
      // Start recording
      const recordButton = screen.getByRole('button', { name: /record/i });
      await user.click(recordButton);
      
      // Check for timer
      expect(await screen.findByTestId('recording-timer')).toBeInTheDocument();
    });
  });
}); 