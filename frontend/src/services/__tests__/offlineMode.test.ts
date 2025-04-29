import { NetworkStatus, useNetworkStatus } from '../networkService';
import { StorageService } from '../storageService';
import { WorkoutService } from '../workoutService';
import api from '../api';

jest.mock('../api');
jest.mock('../storageService');
jest.mock('../networkService', () => ({
  ...jest.requireActual('../networkService'),
  useNetworkStatus: jest.fn()
}));

describe('Offline Mode and Retry Handling', () => {
  let storageService: jest.Mocked<StorageService>;
  let workoutService: WorkoutService;
  let mockNetworkStatus: NetworkStatus;
  const mockUseNetworkStatus = useNetworkStatus as jest.MockedFunction<typeof useNetworkStatus>;

  beforeEach(() => {
    jest.clearAllMocks();
    storageService = StorageService.getInstance() as jest.Mocked<StorageService>;
    workoutService = new WorkoutService();
    mockNetworkStatus = {
      connected: true,
      connectionType: 'wifi'
    };

    // Mock api calls
    (api.post as jest.Mock).mockRejectedValue(new Error('Network error'));
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

    // Attempt to create workout while offline
    await workoutService.createWorkout(workout);

    // Verify workout was queued in storage
    expect(storageService.addToWorkoutQueue).toHaveBeenCalledWith({
      type: 'CREATE_WORKOUT',
      data: workout,
      timestamp: expect.any(Number)
    });
  });

  it('retries queued requests when coming back online', async () => {
    // Simulate offline mode
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
    (storageService.getWorkoutQueue as jest.Mock).mockResolvedValue(queuedRequests);

    // Simulate coming back online
    mockNetworkStatus.connected = true;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: true
    });

    // Verify queued requests were processed
    expect(storageService.removeFromWorkoutQueue).toHaveBeenCalled();
    expect(api.post).toHaveBeenCalledWith(
      '/api/workouts',
      queuedRequests[0].data
    );
  });

  it('handles failed retry attempts and re-queues requests', async () => {
    // Simulate offline mode
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
    (storageService.getWorkoutQueue as jest.Mock).mockResolvedValue(queuedRequests);

    // Simulate coming back online but request fails
    mockNetworkStatus.connected = true;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: true
    });

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
    // Simulate offline mode
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
    (storageService.getWorkoutQueue as jest.Mock).mockResolvedValue(queuedRequests);

    // Simulate coming back online
    mockNetworkStatus.connected = true;
    mockUseNetworkStatus.mockReturnValue({
      status: mockNetworkStatus,
      isOnline: true
    });

    // Verify request was removed from queue without retrying
    expect(storageService.removeFromWorkoutQueue).toHaveBeenCalledWith(queuedRequests[0].data.id);
  });
}); 