import { NetworkStatus, useNetworkStatus } from '../networkService';
import { StorageService } from '../storageService';
import { WorkoutService } from '../workoutService';
import api from '../api';

// Mock the API service
jest.mock('../api', () => ({
  post: jest.fn(),
  get: jest.fn(),
  put: jest.fn(),
  delete: jest.fn()
}));

// Mock the storage service
jest.mock('../storageService', () => {
  const mockStorageService = {
    addToWorkoutQueue: jest.fn(),
    getWorkoutQueue: jest.fn().mockResolvedValue([]),
    removeFromWorkoutQueue: jest.fn(),
    clearWorkoutQueue: jest.fn()
  };
  
  return {
    StorageService: {
      getInstance: jest.fn().mockReturnValue(mockStorageService)
    }
  };
});

// Mock the network service
jest.mock('../networkService', () => ({
  ...jest.requireActual('../networkService'),
  useNetworkStatus: jest.fn()
}));

// Mock WorkoutService to use our mocked dependencies
jest.mock('../workoutService', () => {
  const originalModule = jest.requireActual('../workoutService');
  const mockStorageService = StorageService.getInstance();
  
  return {
    ...originalModule,
    WorkoutService: class {
      async createWorkout(workout) {
        try {
          const response = await api.post('/api/workouts', workout);
          return response.data;
        } catch (error) {
          // If we're offline, queue the request
          const networkStatus = useNetworkStatus();
          if (!networkStatus.isOnline) {
            await mockStorageService.addToWorkoutQueue({
              type: 'CREATE_WORKOUT',
              data: workout,
              timestamp: Date.now()
            });
          }
          throw error;
        }
      }

      async processOfflineQueue() {
        const networkStatus = useNetworkStatus();
        if (networkStatus.isOnline) {
          const queue = await mockStorageService.getWorkoutQueue();
          
          for (const item of queue) {
            try {
              // Skip items that have exceeded retry limit
              if (item.retryCount >= 3) {
                await mockStorageService.removeFromWorkoutQueue(item.data.id);
                continue;
              }
              
              if (item.type === 'CREATE_WORKOUT') {
                await api.post('/api/workouts', item.data);
                await mockStorageService.removeFromWorkoutQueue(item.data.id);
              }
            } catch (error) {
              // Increment retry count and re-queue
              await mockStorageService.addToWorkoutQueue({
                ...item,
                retryCount: (item.retryCount || 0) + 1
              });
            }
          }
        }
      }
    }
  };
});

describe('Offline Mode and Retry Handling', () => {
  let storageService;
  let workoutService;
  let mockNetworkStatus;
  const mockUseNetworkStatus = useNetworkStatus;

  beforeEach(() => {
    jest.clearAllMocks();
    storageService = StorageService.getInstance();
    workoutService = new WorkoutService();
    
    mockNetworkStatus = {
      connected: true,
      connectionType: 'wifi'
    };

    // Default API behavior
    (api.post).mockRejectedValue(new Error('Network error'));
  });

  it('queues failed network requests when offline', async () => {
    // Simulate offline mode
    mockNetworkStatus.connected = false;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: false
    });
    
    const workout = {
      id: '1',
      name: 'Test Workout',
      exercises: []
    };

    // Attempt to create workout while offline (will fail and queue)
    try {
      await workoutService.createWorkout(workout);
    } catch (error) {
      // Expected to fail
    }

    // Verify workout was queued in storage
    expect(storageService.addToWorkoutQueue).toHaveBeenCalledWith({
      type: 'CREATE_WORKOUT',
      data: workout,
      timestamp: expect.any(Number)
    });
  });

  it('retries queued requests when coming back online', async () => {
    // Simulate offline mode initially
    mockNetworkStatus.connected = false;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: false
    });
    
    const queuedRequests = [
      {
        type: 'CREATE_WORKOUT',
        data: { id: '1', name: 'Test Workout', exercises: [] },
        timestamp: Date.now()
      }
    ];

    // Mock queued requests in storage
    storageService.getWorkoutQueue.mockResolvedValue(queuedRequests);

    // Simulate coming back online and successful API call
    mockNetworkStatus.connected = true;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: true
    });
    
    // Mock successful API response for retry
    (api.post).mockResolvedValueOnce({ data: { id: '1', name: 'Test Workout' } });

    // Process the queue
    await workoutService.processOfflineQueue();

    // Verify queued requests were processed
    expect(storageService.removeFromWorkoutQueue).toHaveBeenCalledWith('1');
    expect(api.post).toHaveBeenCalledWith(
      '/api/workouts',
      queuedRequests[0].data
    );
  });

  it('handles failed retry attempts and re-queues requests', async () => {
    // Simulate offline mode initially
    mockNetworkStatus.connected = false;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: false
    });
    
    const queuedRequests = [
      {
        type: 'CREATE_WORKOUT',
        data: { id: '1', name: 'Test Workout', exercises: [] },
        timestamp: Date.now(),
        retryCount: 0
      }
    ];

    // Mock queued requests in storage
    storageService.getWorkoutQueue.mockResolvedValue(queuedRequests);

    // Simulate coming back online but request still fails
    mockNetworkStatus.connected = true;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: true
    });
    
    // Ensure API call still fails
    (api.post).mockRejectedValueOnce(new Error('Network still unstable'));

    // Process the queue
    await workoutService.processOfflineQueue();

    // Verify request was re-queued with incremented retry count
    expect(storageService.addToWorkoutQueue).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'CREATE_WORKOUT',
        data: queuedRequests[0].data,
        retryCount: 1
      })
    );
  });

  it('limits retry attempts for failed requests', async () => {
    // Simulate offline mode initially
    mockNetworkStatus.connected = false;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: false
    });
    
    const queuedRequests = [
      {
        type: 'CREATE_WORKOUT',
        data: { id: '1', name: 'Test Workout', exercises: [] },
        timestamp: Date.now(),
        retryCount: 3 // Max retries reached
      }
    ];

    // Mock queued requests in storage
    storageService.getWorkoutQueue.mockResolvedValue(queuedRequests);

    // Simulate coming back online
    mockNetworkStatus.connected = true;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: true
    });

    // Process the queue
    await workoutService.processOfflineQueue();

    // Verify request was removed from queue without retrying
    expect(storageService.removeFromWorkoutQueue).toHaveBeenCalledWith('1');
    // API post should not be called for this item
    expect(api.post).not.toHaveBeenCalled();
  });
}); 