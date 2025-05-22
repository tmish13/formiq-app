import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { CameraPermissionFallback } from '../CameraPermissionFallback';
import { useCameraPermissions } from '../../../hooks/useCameraPermissions';
import { theme } from '../../../theme';

// Mock the capacitor modules
jest.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: jest.fn().mockReturnValue(false)
  },
  WebPlugin: class WebPlugin {
    addListener() { return { remove: jest.fn() }; }
    removeAllListeners() {}
  }
}));

jest.mock('@capacitor/app', () => ({
  App: {
    openUrl: jest.fn().mockResolvedValue(undefined)
  }
}));

// Mock the camera hooks
jest.mock('../../../hooks/useCameraPermissions');

describe('CameraPermissionFallback Component - Camera Permission Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Tests for UI rendering
   */
  describe('UI Rendering', () => {
    it('renders the fallback UI correctly when permissions are denied', () => {
      // Mock denied permissions
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: jest.fn().mockResolvedValue(false),
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback />
        </ThemeProvider>
      );

      expect(screen.getByText('Camera Access Required')).toBeInTheDocument();
      expect(screen.getByText(/we need permission to use your camera/i)).toBeInTheDocument();
      expect(screen.getByText('Try Again')).toBeInTheDocument();
      expect(screen.getByText(/click here to upload a video/i)).toBeInTheDocument();
    });

    it('renders a loading state when checking permissions', () => {
      // Mock loading state
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: jest.fn(),
        isLoading: true,
        granted: false,
        denied: false,
        requested: true,
        error: null,
      });
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback />
        </ThemeProvider>
      );

      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  /**
   * Tests for permission request flow
   */
  describe('Permission Request Flow', () => {
    it('calls requestPermission when "Try Again" button is clicked', async () => {
      // Mock permissions hook with a spy on requestPermission
      const mockRequestPermission = jest.fn().mockResolvedValue(false);
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: mockRequestPermission,
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback />
        </ThemeProvider>
      );

      // Click the "Try Again" button
      fireEvent.click(screen.getByText('Try Again'));
      
      // Verify requestPermission was called
      await waitFor(() => {
        expect(mockRequestPermission).toHaveBeenCalledTimes(1);
      });
    });

    it('calls onRetry callback when permission is granted after retry', async () => {
      // Mock successful permission request
      const mockRequestPermission = jest.fn().mockResolvedValue(true);
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: mockRequestPermission,
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      const onRetry = jest.fn();
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback onRetry={onRetry} />
        </ThemeProvider>
      );

      // Click the "Try Again" button
      fireEvent.click(screen.getByText('Try Again'));
      
      // Verify onRetry was called after successful permission request
      await waitFor(() => {
        expect(mockRequestPermission).toHaveBeenCalledTimes(1);
        expect(onRetry).toHaveBeenCalledTimes(1);
      });
    });

    it('does not call onRetry when permission remains denied after retry', async () => {
      // Mock failed permission request
      const mockRequestPermission = jest.fn().mockResolvedValue(false);
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: mockRequestPermission,
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      const onRetry = jest.fn();
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback onRetry={onRetry} />
        </ThemeProvider>
      );

      // Click the "Try Again" button
      fireEvent.click(screen.getByText('Try Again'));
      
      // Verify requestPermission was called but not onRetry
      await waitFor(() => {
        expect(mockRequestPermission).toHaveBeenCalledTimes(1);
      });
      
      // onRetry should not have been called
      expect(onRetry).not.toHaveBeenCalled();
    });

    it('handles permission request errors gracefully', async () => {
      // Mock error in permission request
      const mockRequestPermission = jest.fn().mockRejectedValue(new Error('Permission request failed'));
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: mockRequestPermission,
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      const onRetry = jest.fn();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback onRetry={onRetry} />
        </ThemeProvider>
      );

      // Click the "Try Again" button
      fireEvent.click(screen.getByText('Try Again'));
      
      // Verify requestPermission was called
      await waitFor(() => {
        expect(mockRequestPermission).toHaveBeenCalledTimes(1);
      });
      
      // onRetry should not have been called
      expect(onRetry).not.toHaveBeenCalled();
      
      // Restore console.error
      consoleErrorSpy.mockRestore();
    });
  });

  /**
   * Tests for file upload fallback flow
   */
  describe('File Upload Fallback', () => {
    it('calls onFileUpload when a file is selected', () => {
      // Mock denied permissions
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: jest.fn().mockResolvedValue(false),
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      const onFileUpload = jest.fn();
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback onFileUpload={onFileUpload} />
        </ThemeProvider>
      );

      // Create a mock video file
      const file = new File(['dummy content'], 'example.mp4', { type: 'video/mp4' });
      const input = screen.getByLabelText(/click here to upload a video/i, { selector: 'input' });
      
      // Mock files array on the input element
      Object.defineProperty(input, 'files', {
        value: [file],
      });
      
      // Trigger file selection
      fireEvent.change(input);
      
      // Verify onFileUpload was called with the file
      expect(onFileUpload).toHaveBeenCalledWith(file);
    });

    it('validates file type when uploading', () => {
      // Mock denied permissions
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: jest.fn().mockResolvedValue(false),
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });

      const onFileUpload = jest.fn();
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback onFileUpload={onFileUpload} />
        </ThemeProvider>
      );

      // Create a mock non-video file
      const file = new File(['dummy content'], 'example.txt', { type: 'text/plain' });
      const input = screen.getByLabelText(/click here to upload a video/i, { selector: 'input' });
      
      // Mock files array on the input element
      Object.defineProperty(input, 'files', {
        value: [file],
      });
      
      // Trigger file selection
      fireEvent.change(input);
      
      // Verify onFileUpload was not called for invalid file type
      expect(onFileUpload).not.toHaveBeenCalled();
      
      // Restore console.error
      consoleErrorSpy.mockRestore();
    });
  });

  /**
   * Tests for initial state and automatic permission requests
   */
  describe('Initial State and Automatic Permission Requests', () => {
    it('automatically requests permissions on mount if not requested before', () => {
      // Mock permissions not yet requested
      const mockRequestPermission = jest.fn().mockResolvedValue(false);
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: mockRequestPermission,
        isLoading: false,
        granted: false,
        denied: false,
        requested: false, // Not requested yet
        error: null,
      });
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback />
        </ThemeProvider>
      );
      
      // Verify requestPermission was called automatically
      expect(mockRequestPermission).toHaveBeenCalledTimes(1);
    });

    it('does not automatically request permissions if already requested', () => {
      // Mock permissions already requested
      const mockRequestPermission = jest.fn().mockResolvedValue(false);
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: mockRequestPermission,
        isLoading: false,
        granted: false,
        denied: true,
        requested: true, // Already requested
        error: null,
      });
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback />
        </ThemeProvider>
      );
      
      // Verify requestPermission was not called automatically
      expect(mockRequestPermission).not.toHaveBeenCalled();
    });
  });

  /**
   * Tests for native platform behaviors
   */
  describe('Native Platform Behaviors', () => {
    it('opens settings when "Open Settings" button is clicked on native platform', () => {
      // Mock native platform
      (require('@capacitor/core').Capacitor.isNativePlatform as jest.Mock).mockReturnValue(true);
      
      // Mock permissions denied
      (useCameraPermissions as jest.Mock).mockReturnValue({
        requestPermission: jest.fn().mockResolvedValue(false),
        isLoading: false,
        granted: false,
        denied: true,
        requested: true,
        error: null,
      });
      
      render(
        <ThemeProvider theme={theme}>
          <CameraPermissionFallback />
        </ThemeProvider>
      );
      
      // Verify "Open Settings" button is shown on native platform
      const settingsButton = screen.getByText('Open Settings');
      expect(settingsButton).toBeInTheDocument();
      
      // Click the "Open Settings" button
      fireEvent.click(settingsButton);
      
      // Verify App.openUrl was called to open settings
      expect(require('@capacitor/app').App.openUrl).toHaveBeenCalled();
    });
  });
}); 