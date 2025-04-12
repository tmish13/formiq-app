import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import NetInfo from '@react-native-community/netinfo';
import OfflineManager from '../src/utils/OfflineManager';
import VideoUploadQueue from '../src/utils/VideoUploadQueue';

jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: jest.fn(),
  fetch: jest.fn(),
}));

jest.mock('../src/utils/VideoUploadQueue', () => ({
  addToQueue: jest.fn(),
  processQueue: jest.fn(),
}));

describe('OfflineMode', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('detects offline mode', async () => {
    NetInfo.fetch.mockResolvedValue({ isConnected: false });
    
    const { getByText } = render(<OfflineManager />);
    
    await waitFor(() => {
      expect(getByText('You are offline')).toBeTruthy();
    });
  });

  it('queues video upload when offline', async () => {
    NetInfo.fetch.mockResolvedValue({ isConnected: false });
    
    const videoData = {
      uri: 'file://video.mp4',
      type: 'video/mp4',
      name: 'test.mp4',
    };
    
    await OfflineManager.handleVideoUpload(videoData);
    
    expect(VideoUploadQueue.addToQueue).toHaveBeenCalledWith(videoData);
  });

  it('processes queued videos when coming back online', async () => {
    NetInfo.addEventListener.mockImplementation((callback) => {
      callback({ isConnected: true });
    });
    
    await OfflineManager.handleConnectivityChange({ isConnected: true });
    
    expect(VideoUploadQueue.processQueue).toHaveBeenCalled();
  });

  it('stores video metadata locally when offline', async () => {
    const videoMetadata = {
      id: '123',
      filename: 'test.mp4',
      timestamp: Date.now(),
    };
    
    await OfflineManager.storeVideoMetadata(videoMetadata);
    
    const stored = await OfflineManager.getStoredVideos();
    expect(stored).toContainEqual(videoMetadata);
  });

  it('handles failed uploads in queue', async () => {
    VideoUploadQueue.processQueue.mockRejectedValue(new Error('Upload failed'));
    
    await OfflineManager.handleConnectivityChange({ isConnected: true });
    
    const failedUploads = await OfflineManager.getFailedUploads();
    expect(failedUploads.length).toBeGreaterThan(0);
  });
}); 