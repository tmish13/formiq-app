import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Camera } from 'expo-camera';
import CameraScreen from '../src/screens/CameraScreen';

jest.mock('expo-camera', () => ({
  Camera: {
    requestCameraPermissionsAsync: jest.fn(),
    getCameraPermissionsAsync: jest.fn(),
  },
}));

describe('CameraScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('requests camera permissions on mount', async () => {
    Camera.requestCameraPermissionsAsync.mockResolvedValue({ granted: true });
    
    render(<CameraScreen />);
    
    await waitFor(() => {
      expect(Camera.requestCameraPermissionsAsync).toHaveBeenCalled();
    });
  });

  it('shows error message when camera permission is denied', async () => {
    Camera.requestCameraPermissionsAsync.mockResolvedValue({ granted: false });
    
    const { getByText } = render(<CameraScreen />);
    
    await waitFor(() => {
      expect(getByText('Camera permission is required')).toBeTruthy();
    });
  });

  it('handles video recording', async () => {
    const mockStartRecording = jest.fn();
    const mockStopRecording = jest.fn();
    
    const { getByTestId } = render(
      <CameraScreen
        onStartRecording={mockStartRecording}
        onStopRecording={mockStopRecording}
      />
    );
    
    const recordButton = getByTestId('record-button');
    fireEvent.press(recordButton);
    
    expect(mockStartRecording).toHaveBeenCalled();
    
    fireEvent.press(recordButton);
    expect(mockStopRecording).toHaveBeenCalled();
  });

  it('handles camera flip', () => {
    const { getByTestId } = render(<CameraScreen />);
    
    const flipButton = getByTestId('flip-camera-button');
    fireEvent.press(flipButton);
    
    // Add assertions for camera flip functionality
  });

  it('handles flash mode toggle', () => {
    const { getByTestId } = render(<CameraScreen />);
    
    const flashButton = getByTestId('flash-button');
    fireEvent.press(flashButton);
    
    // Add assertions for flash mode changes
  });
}); 