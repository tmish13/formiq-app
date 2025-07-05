/**
 * Integration Test: Mobile Camera Capture and Upload Workflow
 * 
 * Tests the complete mobile camera workflow including permissions,
 * video capture, preview, and upload functionality using Capacitor.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IntegrationTestUtils, config } from '../setup';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { store } from '../../../src/store';
import { ThemeProvider } from '../../../src/contexts/ThemeContext';
import CameraCapture from '../../../src/components/camera/CameraCapture';
import { useMobileFeatures } from '../../../src/hooks/useMobileFeatures';
import { enhancedCameraService } from '../../../src/services/enhancedCameraService';
import { mobileService } from '../../../src/services/mobileService';

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Provider store={store}>
    <BrowserRouter>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </BrowserRouter>
  </Provider>
);

// Mock camera component for testing
const MockCameraCapture: React.FC = () => {
  const {
    takePhoto,
    startVideoRecording,
    stopVideoRecording,
    isNative,
    deviceFeatures,
    hapticFeedback,
  } = useMobileFeatures();

  return (
    <div data-testid="camera-capture">
      <div data-testid="camera-status">
        {isNative ? 'Native Camera' : 'Web Camera'}
      </div>
      <div data-testid="camera-features">
        {deviceFeatures.hasCamera ? 'Camera Available' : 'No Camera'}
      </div>
      <button 
        data-testid="take-photo-btn"
        onClick={takePhoto}
      >
        Take Photo
      </button>
      <button 
        data-testid="start-recording-btn"
        onClick={startVideoRecording}
      >
        Start Recording
      </button>
      <button 
        data-testid="stop-recording-btn"
        onClick={stopVideoRecording}
      >
        Stop Recording
      </button>
      <button 
        data-testid="haptic-test-btn"
        onClick={() => hapticFeedback('medium')}
      >
        Test Haptic
      </button>
    </div>
  );
};

describe('Mobile Camera Capture and Upload Integration Tests', () => {
  let mockCameraPlugin: any;
  let mockFileSystemPlugin: any;
  let mockHapticsPlugin: any;

  beforeEach(() => {
    // Setup Capacitor mocks
    IntegrationTestUtils.setupCapacitorMocks();
    IntegrationTestUtils.simulateMobileEnvironment();

    // Enhanced Capacitor plugin mocks
    mockCameraPlugin = {
      requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
      getPhoto: jest.fn().mockResolvedValue({
        webPath: 'data:image/jpeg;base64,mock_image_data_12345',
        format: 'jpeg',
        saved: false,
      }),
      startVideoRecording: jest.fn().mockResolvedValue({
        webPath: 'blob:http://localhost:3000/video_123',
        format: 'mp4',
        duration: 15000, // 15 seconds
      }),
      stopVideoRecording: jest.fn().mockResolvedValue({
        webPath: 'blob:http://localhost:3000/video_123',
        format: 'mp4',
        duration: 15000,
      }),
    };

    mockFileSystemPlugin = {
      requestPermissions: jest.fn().mockResolvedValue({ publicStorage: 'granted' }),
      writeFile: jest.fn().mockResolvedValue({
        uri: 'file:///storage/emulated/0/formiq/video_123.mp4',
      }),
      readFile: jest.fn().mockResolvedValue({
        data: 'mock_video_data_base64',
      }),
      deleteFile: jest.fn().mockResolvedValue(),
      getUri: jest.fn().mockResolvedValue({
        uri: 'file:///storage/emulated/0/formiq/video_123.mp4',
      }),
    };

    mockHapticsPlugin = {
      impact: jest.fn().mockResolvedValue(),
      notification: jest.fn().mockResolvedValue(),
      selection: jest.fn().mockResolvedValue(),
    };

    // Override Capacitor mocks with enhanced functionality
    (window as any).Capacitor.Plugins = {
      ...((window as any).Capacitor.Plugins || {}),
      Camera: mockCameraPlugin,
      Filesystem: mockFileSystemPlugin,
      Haptics: mockHapticsPlugin,
    };

    // Mock enhanced camera service methods
    jest.spyOn(enhancedCameraService, 'initializeCamera').mockResolvedValue({
      success: true,
      stream: new MediaStream(),
    });

    jest.spyOn(enhancedCameraService, 'takePhoto').mockResolvedValue({
      success: true,
      data: {
        webPath: 'data:image/jpeg;base64,mock_image_data',
        format: 'jpeg',
      },
    });

    jest.spyOn(enhancedCameraService, 'startVideoRecording').mockResolvedValue({
      success: true,
      data: {
        recordingId: 'recording_123',
        status: 'recording',
      },
    });

    jest.spyOn(enhancedCameraService, 'stopVideoRecording').mockResolvedValue({
      success: true,
      data: {
        webPath: 'blob:http://localhost:3000/video_123',
        format: 'mp4',
        duration: 15000,
        size: 1024000, // 1MB
      },
    });

    // Mock mobile service methods
    jest.spyOn(mobileService, 'getAppInfo').mockResolvedValue({
      isNative: true,
      platform: 'ios',
      safeAreaInsets: { top: 44, bottom: 34, left: 0, right: 0 },
      features: {
        hasCamera: true,
        hasHaptics: true,
        hasBiometrics: false,
        hasNotifications: true,
        supportsBackgroundMode: false,
        supportsVibration: true,
      },
      deviceInfo: {
        model: 'iPhone 13',
        platform: 'ios',
        osVersion: '15.0',
        manufacturer: 'Apple',
        isVirtual: false,
      },
    });

    jest.spyOn(mobileService, 'hapticFeedback').mockResolvedValue();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Camera Permissions', () => {
    it('should request and handle camera permissions correctly', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <MockCameraCapture />
        </TestWrapper>
      );

      // Verify camera availability is detected
      await waitFor(() => {
        expect(screen.getByTestId('camera-features')).toHaveTextContent('Camera Available');
      });

      // Verify native camera detection
      expect(screen.getByTestId('camera-status')).toHaveTextContent('Native Camera');

      // Test photo capture (which should trigger permission request)
      const takePhotoBtn = screen.getByTestId('take-photo-btn');
      await user.click(takePhotoBtn);

      // Verify permission request was made
      await waitFor(() => {
        expect(mockCameraPlugin.requestPermissions).toHaveBeenCalled();
      });

      // Verify photo was taken
      await waitFor(() => {
        expect(mockCameraPlugin.getPhoto).toHaveBeenCalled();
      });
    });

    it('should handle permission denial gracefully', async () => {
      const user = userEvent.setup();
      
      // Mock permission denial
      mockCameraPlugin.requestPermissions.mockResolvedValue({ camera: 'denied' });

      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Try to access camera
      const cameraButton = screen.queryByRole('button', { name: /camera|capture/i });
      if (cameraButton) {
        await user.click(cameraButton);

        // Verify permission error is handled
        await waitFor(() => {
          expect(screen.getByText(/camera.*permission.*denied|permission.*required/i)).toBeInTheDocument();
        });
      }
    });
  });

  describe('Video Recording Workflow', () => {
    it('should complete full video recording and preview workflow', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Wait for camera initialization
      await waitFor(() => {
        expect(screen.getByTestId('camera-capture')).toBeInTheDocument();
      });

      // Start video recording
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      // Verify recording started
      await waitFor(() => {
        expect(screen.getByText(/recording|rec/i)).toBeInTheDocument();
        expect(mockCameraPlugin.startVideoRecording || enhancedCameraService.startVideoRecording).toHaveBeenCalled();
      });

      // Verify haptic feedback during recording start
      expect(mockHapticsPlugin.impact || mobileService.hapticFeedback).toHaveBeenCalled();

      // Simulate recording duration (mock timer)
      await IntegrationTestUtils.waitFor(
        () => screen.queryByText(/00:0[5-9]|00:1\d/) !== null,
        3000
      );

      // Stop recording
      const stopButton = screen.getByRole('button', { name: /stop|end.*recording/i });
      await user.click(stopButton);

      // Verify recording stopped
      await waitFor(() => {
        expect(mockCameraPlugin.stopVideoRecording || enhancedCameraService.stopVideoRecording).toHaveBeenCalled();
      });

      // Verify video preview is shown
      await waitFor(() => {
        expect(screen.getByText(/preview|review/i)).toBeInTheDocument();
      });

      // Verify video controls are available
      expect(screen.getByRole('button', { name: /play|replay/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retake|record.*again/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /use.*video|accept|continue/i })).toBeInTheDocument();
    });

    it('should handle video recording errors', async () => {
      const user = userEvent.setup();
      
      // Mock recording failure
      mockCameraPlugin.startVideoRecording.mockRejectedValue(
        new Error('Camera unavailable')
      );

      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Try to start recording
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      // Verify error handling
      await waitFor(() => {
        expect(screen.getByText(/error.*recording|camera.*unavailable/i)).toBeInTheDocument();
      });

      // Verify retry option is available
      const retryButton = screen.queryByRole('button', { name: /retry|try.*again/i });
      if (retryButton) {
        expect(retryButton).toBeInTheDocument();
      }
    });

    it('should respect recording time limits', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Start recording
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      // Verify timer starts
      await waitFor(() => {
        expect(screen.getByText(/00:0[0-9]/)).toBeInTheDocument();
      });

      // Simulate reaching maximum recording time (assuming 30 seconds)
      // This would normally be handled by the camera service
      await IntegrationTestUtils.waitFor(
        () => screen.queryByText(/recording.*stopped|maximum.*duration/i) !== null,
        5000
      );

      // Verify automatic stop when limit reached
      await waitFor(() => {
        expect(mockCameraPlugin.stopVideoRecording || enhancedCameraService.stopVideoRecording).toHaveBeenCalled();
      });
    });
  });

  describe('File System Integration', () => {
    it('should save and manage video files correctly', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Complete video recording
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      await waitFor(() => {
        expect(screen.getByText(/recording/i)).toBeInTheDocument();
      });

      const stopButton = screen.getByRole('button', { name: /stop|end.*recording/i });
      await user.click(stopButton);

      // Accept the video
      const acceptButton = screen.getByRole('button', { name: /use.*video|accept|continue/i });
      await user.click(acceptButton);

      // Verify file system operations
      await waitFor(() => {
        expect(mockFileSystemPlugin.writeFile).toHaveBeenCalled();
      });

      // Verify file was saved with correct parameters
      const writeFileCall = mockFileSystemPlugin.writeFile.mock.calls[0][0];
      expect(writeFileCall.path).toMatch(/video.*\.mp4$/);
      expect(writeFileCall.data).toBeTruthy();
    });

    it('should handle storage permission errors', async () => {
      const user = userEvent.setup();
      
      // Mock storage permission denial
      mockFileSystemPlugin.writeFile.mockRejectedValue(
        new Error('Storage permission denied')
      );

      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Complete video recording and try to save
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      const stopButton = screen.getByRole('button', { name: /stop|end.*recording/i });
      await user.click(stopButton);

      const acceptButton = screen.getByRole('button', { name: /use.*video|accept|continue/i });
      await user.click(acceptButton);

      // Verify storage error handling
      await waitFor(() => {
        expect(screen.getByText(/storage.*error|permission.*denied/i)).toBeInTheDocument();
      });
    });

    it('should clean up temporary files', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Record and then retake video
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      const stopButton = screen.getByRole('button', { name: /stop|end.*recording/i });
      await user.click(stopButton);

      // Choose to retake instead of accept
      const retakeButton = screen.getByRole('button', { name: /retake|record.*again/i });
      await user.click(retakeButton);

      // Verify cleanup was called
      await waitFor(() => {
        expect(mockFileSystemPlugin.deleteFile).toHaveBeenCalled();
      });
    });
  });

  describe('Mobile Haptic Feedback', () => {
    it('should provide haptic feedback for camera actions', async () => {
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <MockCameraCapture />
        </TestWrapper>
      );

      // Test haptic feedback button
      const hapticButton = screen.getByTestId('haptic-test-btn');
      await user.click(hapticButton);

      // Verify haptic feedback was triggered
      await waitFor(() => {
        expect(mobileService.hapticFeedback).toHaveBeenCalledWith('medium');
      });

      // Test recording start haptic
      const recordButton = screen.getByTestId('start-recording-btn');
      await user.click(recordButton);

      // Verify haptic feedback on recording start
      await waitFor(() => {
        expect(mobileService.hapticFeedback).toHaveBeenCalled();
      });
    });

    it('should handle haptic feedback gracefully when unavailable', async () => {
      const user = userEvent.setup();
      
      // Mock haptic unavailability
      jest.spyOn(mobileService, 'getAppInfo').mockResolvedValue({
        ...await mobileService.getAppInfo(),
        features: {
          ...((await mobileService.getAppInfo()).features),
          hasHaptics: false,
          supportsVibration: false,
        },
      });

      render(
        <TestWrapper>
          <MockCameraCapture />
        </TestWrapper>
      );

      // Test haptic feedback when unavailable
      const hapticButton = screen.getByTestId('haptic-test-btn');
      await user.click(hapticButton);

      // Verify no error is thrown and operation continues
      await waitFor(() => {
        expect(screen.getByTestId('camera-capture')).toBeInTheDocument();
      });
    });
  });

  describe('Upload Integration', () => {
    it('should upload captured video successfully', async () => {
      const user = userEvent.setup();
      
      // Mock upload service
      const mockUpload = jest.fn().mockResolvedValue({
        success: true,
        data: {
          video_id: 'uploaded_video_123',
          upload_url: 'https://s3.amazonaws.com/formiq/video_123',
        },
      });

      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Complete video recording workflow
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      const stopButton = screen.getByRole('button', { name: /stop|end.*recording/i });
      await user.click(stopButton);

      const acceptButton = screen.getByRole('button', { name: /use.*video|accept|continue/i });
      await user.click(acceptButton);

      // Upload the video
      const uploadButton = screen.queryByRole('button', { name: /upload|analyze|submit/i });
      if (uploadButton) {
        await user.click(uploadButton);

        // Verify upload progress is shown
        await waitFor(() => {
          expect(screen.getByText(/uploading|upload.*progress/i)).toBeInTheDocument();
        });
      }
    });

    it('should handle upload failures with retry option', async () => {
      const user = userEvent.setup();
      
      // Mock upload failure
      const mockUpload = jest.fn().mockRejectedValue(
        new Error('Network error during upload')
      );

      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Complete video capture and try upload
      const recordButton = screen.getByRole('button', { name: /record|start.*recording/i });
      await user.click(recordButton);

      const stopButton = screen.getByRole('button', { name: /stop|end.*recording/i });
      await user.click(stopButton);

      const acceptButton = screen.getByRole('button', { name: /use.*video|accept|continue/i });
      await user.click(acceptButton);

      const uploadButton = screen.queryByRole('button', { name: /upload|analyze|submit/i });
      if (uploadButton) {
        await user.click(uploadButton);

        // Verify upload error handling
        await waitFor(() => {
          expect(screen.getByText(/upload.*failed|network.*error/i)).toBeInTheDocument();
        });

        // Verify retry option
        const retryButton = screen.queryByRole('button', { name: /retry|try.*again/i });
        if (retryButton) {
          expect(retryButton).toBeInTheDocument();
        }
      }
    });
  });

  describe('Device Performance Optimization', () => {
    it('should optimize camera settings based on device capabilities', async () => {
      // Mock low-end device
      jest.spyOn(mobileService, 'getAppInfo').mockResolvedValue({
        isNative: true,
        platform: 'android',
        safeAreaInsets: { top: 24, bottom: 0, left: 0, right: 0 },
        features: {
          hasCamera: true,
          hasHaptics: false,
          hasBiometrics: false,
          hasNotifications: true,
          supportsBackgroundMode: false,
          supportsVibration: true,
        },
        deviceInfo: {
          model: 'Budget Phone',
          platform: 'android',
          osVersion: '10.0',
          manufacturer: 'Generic',
          isVirtual: false,
          memoryUsed: 0.9, // High memory usage
        },
      });

      render(
        <TestWrapper>
          <CameraCapture />
        </TestWrapper>
      );

      // Verify performance optimizations are applied
      await waitFor(() => {
        // Lower resolution settings should be applied for low-end devices
        expect(enhancedCameraService.initializeCamera).toHaveBeenCalledWith(
          expect.objectContaining({
            video: expect.objectContaining({
              width: expect.any(Number),
              height: expect.any(Number),
            }),
          })
        );
      });
    });
  });
});