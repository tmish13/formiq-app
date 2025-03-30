import { renderHook, act } from '@testing-library/react-hooks';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useWorkout } from '../useWorkout';
import workoutReducer from '../../store/slices/workoutSlice';
import { Workout, WorkoutPlan } from '../../types';
import { WorkoutState } from '../../store/slices/workoutSlice';

// Mock the workout service
jest.mock('../../services/workoutService', () => ({
  workoutService: {
    getWorkouts: jest.fn(),
    getWorkout: jest.fn(),
    createWorkout: jest.fn(),
    updateWorkout: jest.fn(),
    deleteWorkout: jest.fn(),
    getWorkoutPlans: jest.fn(),
    getWorkoutPlan: jest.fn(),
    createWorkoutPlan: jest.fn(),
    updateWorkoutPlan: jest.fn(),
    deleteWorkoutPlan: jest.fn(),
    getUpcomingWorkouts: jest.fn(),
    getActiveWorkoutPlans: jest.fn(),
  },
}));

const mockWorkout: Workout = {
  id: '1',
  userId: 'user1',
  name: 'Test Workout',
  description: 'Test Description',
  exercises: [
    {
      id: '1',
      name: 'Test Exercise',
      sets: 3,
      reps: 10,
      weight: 100,
      notes: 'Test Notes',
    },
  ],
  duration: 60,
  difficulty: 'intermediate',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const mockWorkoutPlan: WorkoutPlan = {
  id: '1',
  userId: 'user1',
  name: 'Test Plan',
  description: 'Test Plan Description',
  frequency: 'weekly',
  duration: 4,
  notes: 'Test Plan Notes',
  workouts: [mockWorkout],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

const initialState: WorkoutState = {
  workouts: [],
  workoutPlans: [],
  currentWorkout: null,
  currentPlan: null,
  isLoading: false,
  error: null,
};

const createTestStore = (preloadedState: WorkoutState = initialState) => {
  return configureStore({
    reducer: {
      workout: workoutReducer,
    },
    preloadedState: {
      workout: preloadedState,
    },
  });
};

describe('useWorkout', () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    jest.clearAllMocks();
  });

  const TestWrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );

  it('should fetch workouts successfully', async () => {
    const mockWorkouts = [mockWorkout];
    (require('../../services/workoutService').workoutService.getWorkouts as jest.Mock).mockResolvedValue(mockWorkouts);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.fetchWorkouts();
    });

    expect(result.current.workouts).toEqual(mockWorkouts);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should handle error when fetching workouts', async () => {
    const error = new Error('Failed to fetch workouts');
    (require('../../services/workoutService').workoutService.getWorkouts as jest.Mock).mockRejectedValue(error);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.fetchWorkouts();
    });

    expect(result.current.error).toBe(error.message);
    expect(result.current.isLoading).toBe(false);
  });

  it('should create a workout successfully', async () => {
    const newWorkout = { ...mockWorkout, id: undefined, userId: undefined, createdAt: undefined, updatedAt: undefined };
    (require('../../services/workoutService').workoutService.createWorkout as jest.Mock).mockResolvedValue(mockWorkout);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.createWorkout(newWorkout);
    });

    expect(result.current.workouts).toContainEqual(mockWorkout);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should update a workout successfully', async () => {
    const updatedWorkout = { ...mockWorkout, name: 'Updated Workout' };
    (require('../../services/workoutService').workoutService.updateWorkout as jest.Mock).mockResolvedValue(updatedWorkout);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.updateWorkout('1', { name: 'Updated Workout' });
    });

    expect(result.current.workouts).toContainEqual(updatedWorkout);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should delete a workout successfully', async () => {
    (require('../../services/workoutService').workoutService.deleteWorkout as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.deleteWorkout('1');
    });

    expect(result.current.workouts).not.toContainEqual(mockWorkout);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should fetch workout plans successfully', async () => {
    const mockPlans = [mockWorkoutPlan];
    (require('../../services/workoutService').workoutService.getWorkoutPlans as jest.Mock).mockResolvedValue(mockPlans);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.fetchWorkoutPlans();
    });

    expect(result.current.workoutPlans).toEqual(mockPlans);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should create a workout plan successfully', async () => {
    const newPlan = { ...mockWorkoutPlan, id: undefined, userId: undefined, createdAt: undefined, updatedAt: undefined };
    (require('../../services/workoutService').workoutService.createWorkoutPlan as jest.Mock).mockResolvedValue(mockWorkoutPlan);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.createWorkoutPlan(newPlan);
    });

    expect(result.current.workoutPlans).toContainEqual(mockWorkoutPlan);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should update a workout plan successfully', async () => {
    const updatedPlan = { ...mockWorkoutPlan, name: 'Updated Plan' };
    (require('../../services/workoutService').workoutService.updateWorkoutPlan as jest.Mock).mockResolvedValue(updatedPlan);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.updateWorkoutPlan('1', { name: 'Updated Plan' });
    });

    expect(result.current.workoutPlans).toContainEqual(updatedPlan);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should delete a workout plan successfully', async () => {
    (require('../../services/workoutService').workoutService.deleteWorkoutPlan as jest.Mock).mockResolvedValue(undefined);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    await act(async () => {
      await result.current.deleteWorkoutPlan('1');
    });

    expect(result.current.workoutPlans).not.toContainEqual(mockWorkoutPlan);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should fetch upcoming workouts successfully', async () => {
    const mockUpcomingWorkouts = [mockWorkout];
    (require('../../services/workoutService').workoutService.getUpcomingWorkouts as jest.Mock).mockResolvedValue(mockUpcomingWorkouts);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    const upcomingWorkouts = await act(async () => {
      return await result.current.fetchUpcomingWorkouts();
    });

    expect(upcomingWorkouts).toEqual(mockUpcomingWorkouts);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  it('should fetch active workout plans successfully', async () => {
    const mockActivePlans = [mockWorkoutPlan];
    (require('../../services/workoutService').workoutService.getActiveWorkoutPlans as jest.Mock).mockResolvedValue(mockActivePlans);

    const { result } = renderHook(() => useWorkout(), { wrapper: TestWrapper });

    const activePlans = await act(async () => {
      return await result.current.fetchActiveWorkoutPlans();
    });

    expect(activePlans).toEqual(mockActivePlans);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });
}); 