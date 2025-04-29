import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { CameraPermissionFallback } from '../CameraPermissionFallback';
import { useCameraPermissions } from '../../../hooks/useCameraPermissions';
import { theme } from '../../../theme';
import { Camera } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';

// Mock the camera hooks
jest.mock('../../../hooks/useCameraPermissions');

describe('CameraPermissionFallback', () => {
  beforeEach(() => {
    // Default mock implementation
    (useCameraPermissions as jest.Mock).mockReturnValue({
      requestPermission: jest.fn().mockResolvedValue(false),
      isLoading: false,
      granted: false,
      denied: true,
      requested: true,
      error: null,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders the fallback UI correctly', () => {
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

  it('calls onRetry when permission is granted after retry', async () => {
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

    fireEvent.click(screen.getByText('Try Again'));
    
    await waitFor(() => {
      expect(mockRequestPermission).toHaveBeenCalledTimes(1);
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  it('shows loading state while requesting permissions', async () => {
    (useCameraPermissions as jest.Mock).mockReturnValue({
      requestPermission: jest.fn().mockImplementation(() => {
        return new Promise(resolve => setTimeout(() => resolve(true), 100));
      }),
      isLoading: true,
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

    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('calls onFileUpload when a file is selected', () => {
    const onFileUpload = jest.fn();
    
    render(
      <ThemeProvider theme={theme}>
        <CameraPermissionFallback onFileUpload={onFileUpload} />
      </ThemeProvider>
    );

    const file = new File(['dummy content'], 'example.mp4', { type: 'video/mp4' });
    const input = screen.getByLabelText(/click here to upload a video/i, { selector: 'input' });
    
    Object.defineProperty(input, 'files', {
      value: [file],
    });
    
    fireEvent.change(input);
    
    expect(onFileUpload).toHaveBeenCalledWith(file);
  });
}); 