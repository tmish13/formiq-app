import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../context/AuthContext';
import CameraCapture from './CameraCapture';

// Mock the camera API
const mockGetUserMedia = jest.fn();
global.navigator.mediaDevices = {
  getUserMedia: mockGetUserMedia,
};

describe('CameraCapture', () => {
  beforeEach(() => {
    mockGetUserMedia.mockReset();
  });

  const renderCameraCapture = () => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <CameraCapture />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  it('renders camera capture component', () => {
    renderCameraCapture();
    expect(screen.getByText(/Camera Capture/i)).toBeInTheDocument();
  });

  it('handles camera access request', async () => {
    mockGetUserMedia.mockResolvedValueOnce(new MediaStream());
    renderCameraCapture();
    
    const startButton = screen.getByText(/Start Camera/i);
    fireEvent.click(startButton);
    
    expect(mockGetUserMedia).toHaveBeenCalledWith({
      video: { facingMode: 'environment' },
      audio: false
    });
  });

  it('handles camera access denial', async () => {
    mockGetUserMedia.mockRejectedValueOnce(new Error('Camera access denied'));
    renderCameraCapture();
    
    const startButton = screen.getByText(/Start Camera/i);
    fireEvent.click(startButton);
    
    expect(screen.getByText(/Camera access denied/i)).toBeInTheDocument();
  });
}); 