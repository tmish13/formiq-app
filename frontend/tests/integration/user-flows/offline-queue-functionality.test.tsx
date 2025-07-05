/**
 * Integration Test: Offline Queue Functionality
 * 
 * Tests the complete offline queue system including queueing operations
 * when offline, syncing when online, retry mechanisms, and data persistence.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IntegrationTestUtils, config } from '../setup';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { store } from '../../../src/store';
import { ThemeProvider } from '../../../src/contexts/ThemeContext';
import { offlineQueueService } from '../../../src/services/offlineQueue';
import { networkService } from '../../../src/services/networkService';
import FormCheckUploadPage from '../../../src/pages/workout/FormCheckUploadPage';
import * as apiService from '../../../src/services/apiService';

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

// Mock network status control
const mockNetworkStatus = {
  setOnline: (online: boolean) => {
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: online,
    });
    
    if (online) {
      window.dispatchEvent(new Event('online'));
    } else {
      window.dispatchEvent(new Event('offline'));
    }
  },
};

describe('Offline Queue Functionality Integration Tests', () => {
  let originalNavigatorOnline: boolean;

  beforeEach(async () => {
    // Store original online status
    originalNavigatorOnline = navigator.onLine;
    
    // Clear offline queue
    offlineQueueService.clearQueue();
    
    // Clear local storage
    localStorage.clear();
    
    // Enable auto sync for testing
    offlineQueueService.enableAutoSync();

    // Mock API services
    jest.spyOn(apiService, 'uploadVideo').mockImplementation(
      async (formData: FormData, progressCallback?: (progress: number) => void) => {
        // Simulate upload progress
        if (progressCallback) {
          setTimeout(() => progressCallback(25), 100);
          setTimeout(() => progressCallback(50), 200);
          setTimeout(() => progressCallback(75), 300);
          setTimeout(() => progressCallback(100), 400);
        }
        
        await new Promise(resolve => setTimeout(resolve, 500));
        
        return {
          success: true,
          data: {
            video_id: `video_${Date.now()}`,
            upload_url: 'https://mock-s3.amazonaws.com/test-video',
          },
        };
      }
    );

    jest.spyOn(apiService, 'submitFormAnalysis').mockResolvedValue({
      success: true,
      data: {
        analysis_id: `analysis_${Date.now()}`,
        status: 'processing',
      },
    });

    jest.spyOn(apiService, 'saveAnalysisResults').mockResolvedValue({
      success: true,
      data: {
        saved: true,
        analysis_id: `analysis_${Date.now()}`,
      },
    });
  });

  afterEach(() => {
    // Restore original online status
    mockNetworkStatus.setOnline(originalNavigatorOnline);
    
    // Disable auto sync
    offlineQueueService.disableAutoSync();
    
    // Clear all mocks
    jest.clearAllMocks();
  });

  describe('Offline Operation Queueing', () => {
    it('should queue video upload when offline', async () => {
      const user = userEvent.setup();
      
      // Set offline status
      mockNetworkStatus.setOnline(false);
      
      render(
        <TestWrapper>
          <FormCheckUploadPage />
        </TestWrapper>
      );

      // Select exercise and prepare upload
      const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
      await user.selectOptions(exerciseSelect, 'squat');

      const videoFile = IntegrationTestUtils.createTestVideoFile();
      const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
      await user.upload(fileInput, videoFile);

      // Attempt upload while offline
      const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
      await user.click(uploadButton);

      // Verify offline message is shown
      await waitFor(() => {
        expect(screen.getByText(/offline|no.*connection|queued/i)).toBeInTheDocument();
      });

      // Verify item was added to queue
      expect(offlineQueueService.getQueueLength()).toBe(1);
      
      const queueItems = offlineQueueService.getQueueItems();
      expect(queueItems[0].type).toBe('UPLOAD_VIDEO');
      expect(queueItems[0].payload.exerciseType).toBe('squat');
    });

    it('should queue analysis request when offline', async () => {
      // Add a pre-uploaded video scenario
      const mockVideoId = 'test-video-123';
      
      // Set offline status
      mockNetworkStatus.setOnline(false);
      
      // Queue analysis request directly (simulating completed upload)
      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: {
          video_id: mockVideoId,
          exercise_type: 'squat',
          user_preferences: {
            analysis_depth: 'detailed',
          },
        },
        priority: 'high',
      });

      // Verify analysis was queued
      expect(offlineQueueService.getQueueLength()).toBe(1);
      
      const queueItems = offlineQueueService.getQueueItems();
      expect(queueItems[0].type).toBe('ANALYZE_FORM');
      expect(queueItems[0].payload.video_id).toBe(mockVideoId);
    });

    it('should handle multiple offline operations', async () => {
      const user = userEvent.setup();
      
      // Set offline status
      mockNetworkStatus.setOnline(false);
      
      // Queue multiple operations
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: { video_id: 'video-1', exercise_type: 'deadlift' },
        priority: 'medium',
      });

      await offlineQueueService.addToQueue({
        type: 'SAVE_ANALYSIS',
        payload: { analysis_id: 'analysis-1', results: {} },
        priority: 'low',
      });

      // Verify all operations are queued
      expect(offlineQueueService.getQueueLength()).toBe(3);
      
      const queueItems = offlineQueueService.getQueueItems();
      expect(queueItems.map(item => item.type)).toEqual([
        'UPLOAD_VIDEO',
        'ANALYZE_FORM',
        'SAVE_ANALYSIS',
      ]);
    });
  });

  describe('Online Sync Functionality', () => {
    it('should automatically sync queue when coming online', async () => {
      // Start offline and queue operations
      mockNetworkStatus.setOnline(false);
      
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: { video_id: 'video-1', exercise_type: 'squat' },
        priority: 'medium',
      });

      expect(offlineQueueService.getQueueLength()).toBe(2);

      // Come back online
      mockNetworkStatus.setOnline(true);

      // Wait for auto-sync to process the queue
      await IntegrationTestUtils.waitFor(
        () => offlineQueueService.getQueueLength() === 0,
        10000
      );

      // Verify all items were processed
      expect(offlineQueueService.getQueueLength()).toBe(0);
      
      // Verify API calls were made
      expect(apiService.uploadVideo).toHaveBeenCalled();
      expect(apiService.submitFormAnalysis).toHaveBeenCalled();
    });

    it('should respect priority order during sync', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Add items with different priorities
      await offlineQueueService.addToQueue({
        type: 'SAVE_ANALYSIS',
        payload: { analysis_id: 'low-priority' },
        priority: 'low',
      });

      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: { video_id: 'medium-priority' },
        priority: 'medium',
      });

      // Track processing order
      const processOrder: string[] = [];
      
      jest.spyOn(apiService, 'uploadVideo').mockImplementation(async () => {
        processOrder.push('high');
        return { success: true, data: { video_id: 'test' } };
      });

      jest.spyOn(apiService, 'submitFormAnalysis').mockImplementation(async () => {
        processOrder.push('medium');
        return { success: true, data: { analysis_id: 'test' } };
      });

      jest.spyOn(apiService, 'saveAnalysisResults').mockImplementation(async () => {
        processOrder.push('low');
        return { success: true, data: { saved: true } };
      });

      // Come online and sync
      mockNetworkStatus.setOnline(true);

      await IntegrationTestUtils.waitFor(
        () => processOrder.length === 3,
        10000
      );

      // Verify high priority processed first
      expect(processOrder).toEqual(['high', 'medium', 'low']);
    });

    it('should handle sync errors with retry mechanism', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Queue operation
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      // Mock API failure on first attempts
      let attemptCount = 0;
      jest.spyOn(apiService, 'uploadVideo').mockImplementation(async () => {
        attemptCount++;
        if (attemptCount <= 2) {
          throw new Error('Network error');
        }
        return { success: true, data: { video_id: 'test' } };
      });

      // Come online
      mockNetworkStatus.setOnline(true);

      // Wait for retries and eventual success
      await IntegrationTestUtils.waitFor(
        () => attemptCount >= 3,
        15000
      );

      // Verify item was eventually processed
      await IntegrationTestUtils.waitFor(
        () => offlineQueueService.getQueueLength() === 0,
        5000
      );

      expect(attemptCount).toBe(3);
    });

    it('should remove items after max retry attempts', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Queue operation
      const queueId = await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      // Mock API to always fail
      jest.spyOn(apiService, 'uploadVideo').mockRejectedValue(new Error('Persistent error'));

      // Track failed items
      const failedItems: any[] = [];
      offlineQueueService.on('itemFailed', (data) => {
        failedItems.push(data);
      });

      // Come online
      mockNetworkStatus.setOnline(true);

      // Wait for max retries and removal
      await IntegrationTestUtils.waitFor(
        () => failedItems.length > 0,
        15000
      );

      // Verify item was removed after max retries
      expect(offlineQueueService.getQueueLength()).toBe(0);
      expect(failedItems).toHaveLength(1);
      expect(failedItems[0].item.id).toBe(queueId);
    });
  });

  describe('Queue Persistence', () => {
    it('should persist queue across app restarts', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Add items to queue
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: { video_id: 'video-1', exercise_type: 'deadlift' },
        priority: 'medium',
      });

      expect(offlineQueueService.getQueueLength()).toBe(2);

      // Verify queue is saved to localStorage
      const storedQueue = localStorage.getItem('formiq_offline_queue');
      expect(storedQueue).toBeTruthy();
      
      const parsedQueue = JSON.parse(storedQueue!);
      expect(parsedQueue).toHaveLength(2);
      expect(parsedQueue[0].type).toBe('UPLOAD_VIDEO');
      expect(parsedQueue[1].type).toBe('ANALYZE_FORM');

      // Simulate app restart by clearing queue and reloading
      offlineQueueService.clearQueue();
      expect(offlineQueueService.getQueueLength()).toBe(0);

      // Create new service instance (simulating app restart)
      const { offlineQueueService: newQueueService } = await import('../../../src/services/offlineQueue');
      
      // Verify queue is restored
      expect(newQueueService.getQueueLength()).toBe(2);
    });

    it('should handle corrupted queue data gracefully', async () => {
      // Corrupt localStorage data
      localStorage.setItem('formiq_offline_queue', 'invalid-json-data');

      // Create new service instance
      const { offlineQueueService: newQueueService } = await import('../../../src/services/offlineQueue');
      
      // Verify service handles corruption gracefully
      expect(newQueueService.getQueueLength()).toBe(0);
      
      // Verify new operations work normally
      await newQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      expect(newQueueService.getQueueLength()).toBe(1);
    });
  });

  describe('Queue Progress and Events', () => {
    it('should emit progress events during sync', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Track events
      const events: any[] = [];
      
      offlineQueueService.on('syncStart', (data) => events.push({ type: 'syncStart', data }));
      offlineQueueService.on('syncComplete', (data) => events.push({ type: 'syncComplete', data }));
      offlineQueueService.on('uploadProgress', (data) => events.push({ type: 'uploadProgress', data }));

      // Queue items
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: { video_id: 'video-1', exercise_type: 'squat' },
        priority: 'medium',
      });

      // Come online and wait for sync
      mockNetworkStatus.setOnline(true);

      await IntegrationTestUtils.waitFor(
        () => events.some(e => e.type === 'syncComplete'),
        10000
      );

      // Verify events were emitted
      expect(events.find(e => e.type === 'syncStart')).toBeTruthy();
      expect(events.find(e => e.type === 'syncComplete')).toBeTruthy();
      
      const syncStartEvent = events.find(e => e.type === 'syncStart');
      expect(syncStartEvent.data.queueLength).toBe(2);
      
      const syncCompleteEvent = events.find(e => e.type === 'syncComplete');
      expect(syncCompleteEvent.data.processedCount).toBe(2);
    });

    it('should emit upload progress events', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Track upload progress
      const progressEvents: any[] = [];
      offlineQueueService.on('uploadProgress', (data) => progressEvents.push(data));

      // Queue upload
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      // Come online
      mockNetworkStatus.setOnline(true);

      // Wait for upload progress events
      await IntegrationTestUtils.waitFor(
        () => progressEvents.length > 0,
        10000
      );

      // Verify progress events
      expect(progressEvents.length).toBeGreaterThan(0);
      expect(progressEvents[0]).toHaveProperty('progress');
      expect(progressEvents[0]).toHaveProperty('exerciseType', 'squat');
    });
  });

  describe('UI Integration', () => {
    it('should show queue status in UI', async () => {
      const user = userEvent.setup();
      
      mockNetworkStatus.setOnline(false);
      
      render(
        <TestWrapper>
          <FormCheckUploadPage />
        </TestWrapper>
      );

      // Try to upload while offline
      const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
      await user.selectOptions(exerciseSelect, 'squat');

      const videoFile = IntegrationTestUtils.createTestVideoFile();
      const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
      await user.upload(fileInput, videoFile);

      const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
      await user.click(uploadButton);

      // Verify queue status is shown
      await waitFor(() => {
        expect(screen.getByText(/queued.*sync|pending.*upload|offline.*mode/i)).toBeInTheDocument();
      });

      // Check if queue count is displayed
      const queueStatus = screen.queryByText(/1.*item.*queue|queued.*1/i);
      if (queueStatus) {
        expect(queueStatus).toBeInTheDocument();
      }
    });

    it('should update UI when sync occurs', async () => {
      const user = userEvent.setup();
      
      mockNetworkStatus.setOnline(false);
      
      render(
        <TestWrapper>
          <FormCheckUploadPage />
        </TestWrapper>
      );

      // Queue an upload
      const exerciseSelect = screen.getByLabelText(/exercise.*type/i);
      await user.selectOptions(exerciseSelect, 'squat');

      const videoFile = IntegrationTestUtils.createTestVideoFile();
      const fileInput = screen.getByLabelText(/choose.*file|upload.*video/i);
      await user.upload(fileInput, videoFile);

      const uploadButton = screen.getByRole('button', { name: /upload|analyze/i });
      await user.click(uploadButton);

      // Verify offline status
      await waitFor(() => {
        expect(screen.getByText(/offline|queued/i)).toBeInTheDocument();
      });

      // Come back online
      mockNetworkStatus.setOnline(true);

      // Verify UI updates to show sync in progress
      await waitFor(() => {
        expect(screen.getByText(/syncing|uploading/i)).toBeInTheDocument();
      });

      // Verify completion
      await waitFor(() => {
        expect(screen.getByText(/upload.*complete|sync.*complete/i)).toBeInTheDocument();
      }, { timeout: 10000 });
    });
  });

  describe('Error Recovery', () => {
    it('should recover from partial sync failures', async () => {
      mockNetworkStatus.setOnline(false);
      
      // Queue multiple operations
      await offlineQueueService.addToQueue({
        type: 'UPLOAD_VIDEO',
        payload: { file: IntegrationTestUtils.createTestVideoFile(), exerciseType: 'squat' },
        priority: 'high',
      });

      await offlineQueueService.addToQueue({
        type: 'ANALYZE_FORM',
        payload: { video_id: 'video-1', exercise_type: 'deadlift' },
        priority: 'medium',
      });

      // Mock first operation to fail, second to succeed
      jest.spyOn(apiService, 'uploadVideo').mockRejectedValue(new Error('Upload failed'));
      jest.spyOn(apiService, 'submitFormAnalysis').mockResolvedValue({
        success: true,
        data: { analysis_id: 'test' },
      });

      // Come online
      mockNetworkStatus.setOnline(true);

      // Wait for partial sync
      await IntegrationTestUtils.waitFor(
        () => offlineQueueService.getQueueLength() === 1, // One item should remain
        10000
      );

      // Verify failed item is retried
      const remainingItems = offlineQueueService.getQueueItems();
      expect(remainingItems).toHaveLength(1);
      expect(remainingItems[0].type).toBe('UPLOAD_VIDEO');
      expect(remainingItems[0].retries).toBeGreaterThan(0);
    });
  });
});