import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { authReducer } from '../../store/slices/authSlice';
import CameraCapture from './CameraCapture';

// Mock the camera API
const mockGetUserMedia = jest.fn();
Object.defineProperty(global.navigator, 'mediaDevices', {
  value: {
    getUserMedia: mockGetUserMedia,
  },
});

const createMockStore = (isAuthenticated = false) => {
  return configureStore({
    reducer: {
      auth: authReducer
    },
    preloadedState: {
      auth: {
        isAuthenticated,
        user: isAuthenticated ? { id: 1 } : null
      }
    }
  });
};

describe('CameraCapture', () => {
  beforeEach(() => {
    mockGetUserMedia.mockClear();
  });

  it('shows login message when user is not authenticated', () => {
    const mockStore = createMockStore(false);
    render(
      <Provider store={mockStore}>
        <CameraCapture />
      </Provider>
    );
    
    expect(screen.getByText('Please log in to access the camera')).toBeInTheDocument();
    expect(mockGetUserMedia).not.toHaveBeenCalled();
  });

  it('attempts to access camera when user is authenticated', async () => {
    const mockStream = { getTracks: () => [{ stop: jest.fn() }] };
    mockGetUserMedia.mockResolvedValueOnce(mockStream);
    
    const mockStore = createMockStore(true);
    render(
      <Provider store={mockStore}>
        <CameraCapture />
      </Provider>
    );
    
    await waitFor(() => {
      expect(mockGetUserMedia).toHaveBeenCalledWith({ video: true });
    });
  });

  it('shows error message when camera access fails', async () => {
    mockGetUserMedia.mockRejectedValueOnce(new Error('Camera access denied'));
    
    const mockStore = createMockStore(true);
    render(
      <Provider store={mockStore}>
        <CameraCapture />
      </Provider>
    );
    
    await waitFor(() => {
      expect(screen.getByText('Failed to access camera')).toBeInTheDocument();
    });
  });
}); 