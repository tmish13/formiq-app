import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Camera } from '@capacitor/camera';
import { Preferences } from '@capacitor/preferences';
import { Network } from '@capacitor/network';
import { App } from '../../src/App';
import { render } from '../../src/test-utils';

// Mock Capacitor plugins
jest.mock('@capacitor/camera', () => ({
  Camera: {
    getPhoto: jest.fn().mockResolvedValue({
      path: 'path/to/photo.jpg',
      webPath: 'blob:photo.jpg',
      format: 'jpeg'
    }),
    checkPermissions: jest.fn().mockResolvedValue({ camera: 'granted' }),
    requestPermissions: jest.fn().mockResolvedValue({ camera: 'granted' })
  }
}));

jest.mock('@capacitor/preferences', () => ({
  Preferences: {
    get: jest.fn().mockResolvedValue({ value: 'test-token' }),
    set: jest.fn().mockResolvedValue(undefined),
    remove: jest.fn().mockResolvedValue(undefined),
    clear: jest.fn().mockResolvedValue(undefined),
    keys: jest.fn().mockResolvedValue({ keys: ['auth-token', 'user-settings'] })
  }
}));

jest.mock('@capacitor/network', () => ({
  Network: {
    getStatus: jest.fn().mockResolvedValue({ connected: true, connectionType: 'wifi' }),
    addListener: jest.fn().mockReturnValue({ remove: jest.fn() })
  }
}));

describe('Mobile Features Integration Tests', () => {
  test('Camera functionality for form check', async () => {
    render(<App />);

    // Check camera permissions
    await waitFor(() => {
      expect(Camera.checkPermissions).toHaveBeenCalled();
    });

    // Navigate to form check
    const formCheckLink = screen.getByText(/form check/i);
    fireEvent.click(formCheckLink);

    // Trigger camera
    const cameraButton = screen.getByRole('button', { name: /take photo/i });
    fireEvent.click(cameraButton);

    // Verify camera was called
    await waitFor(() => {
      expect(Camera.getPhoto).toHaveBeenCalled();
    });

    // Verify photo preview
    expect(await screen.findByAltText(/preview/i)).toHaveAttribute('src', 'blob:photo.jpg');
  });

  test('Offline support and auth flow', async () => {
    render(<App />);

    // Check if token is retrieved from preferences
    await waitFor(() => {
      expect(Preferences.get).toHaveBeenCalledWith({ key: 'auth-token' });
    });

    // Simulate offline mode
    (Network.getStatus as jest.Mock).mockResolvedValueOnce({ 
      connected: false, 
      connectionType: 'none' 
    });

    // Verify offline indicator is shown
    await waitFor(() => {
      expect(screen.getByText(/offline mode/i)).toBeInTheDocument();
    });

    // Verify cached data is displayed
    expect(screen.getByText(/cached workouts/i)).toBeInTheDocument();

    // Test offline form submission
    const formCheckLink = screen.getByText(/form check/i);
    fireEvent.click(formCheckLink);

    const fileInput = screen.getByLabelText(/upload video/i);
    const file = new File(['dummy content'], 'workout.mp4', { type: 'video/mp4' });
    await userEvent.upload(fileInput, file);

    // Verify offline queue message
    expect(screen.getByText(/queued for upload/i)).toBeInTheDocument();
  });

  test('Local storage and preferences', async () => {
    render(<App />);

    // Test saving user preferences
    const settingsLink = screen.getByText(/settings/i);
    fireEvent.click(settingsLink);

    // Change theme preference
    const darkModeSwitch = screen.getByRole('switch', { name: /dark mode/i });
    fireEvent.click(darkModeSwitch);

    await waitFor(() => {
      expect(Preferences.set).toHaveBeenCalledWith({
        key: 'theme',
        value: 'dark'
      });
    });

    // Test clearing preferences
    const clearButton = screen.getByRole('button', { name: /clear preferences/i });
    fireEvent.click(clearButton);

    await waitFor(() => {
      expect(Preferences.clear).toHaveBeenCalled();
    });
  });

  test('Network state changes', async () => {
    render(<App />);

    // Initial online state
    expect(screen.queryByText(/offline mode/i)).not.toBeInTheDocument();

    // Simulate going offline
    const offlineCallback = Network.addListener.mock.calls[0][1];
    offlineCallback({ connected: false, connectionType: 'none' });

    // Verify offline state
    await waitFor(() => {
      expect(screen.getByText(/offline mode/i)).toBeInTheDocument();
    });

    // Simulate coming back online
    offlineCallback({ connected: true, connectionType: 'wifi' });

    // Verify online state
    await waitFor(() => {
      expect(screen.queryByText(/offline mode/i)).not.toBeInTheDocument();
    });

    // Verify sync attempt
    expect(screen.getByText(/syncing data/i)).toBeInTheDocument();
  });

  test('Camera permissions handling', async () => {
    // Mock denied camera permissions
    (Camera.checkPermissions as jest.Mock).mockResolvedValueOnce({ camera: 'denied' });
    (Camera.requestPermissions as jest.Mock).mockResolvedValueOnce({ camera: 'denied' });

    render(<App />);

    // Navigate to form check
    const formCheckLink = screen.getByText(/form check/i);
    fireEvent.click(formCheckLink);

    // Try to use camera
    const cameraButton = screen.getByRole('button', { name: /take photo/i });
    fireEvent.click(cameraButton);

    // Verify permissions request
    await waitFor(() => {
      expect(Camera.requestPermissions).toHaveBeenCalled();
    });

    // Verify error message
    expect(screen.getByText(/camera permission required/i)).toBeInTheDocument();
  });
}); 