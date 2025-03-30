import workoutReducer, {
  setWorkouts,
  setWorkoutPlans,
  setCurrentWorkout,
  setCurrentPlan,
  addWorkout,
  addWorkoutPlan,
  updateWorkout,
  updateWorkoutPlan,
  deleteWorkout,
  deleteWorkoutPlan,
  setLoading,
  setError,
} from '../workoutSlice';
import { Workout, WorkoutPlan } from '../../../types';

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

describe('workoutSlice', () => {
  const initialState = {
    workouts: [],
    workoutPlans: [],
    currentWorkout: null,
    currentPlan: null,
    isLoading: false,
    error: null,
  };

  it('should handle setWorkouts', () => {
    const workouts = [mockWorkout];
    const nextState = workoutReducer(initialState, setWorkouts(workouts));

    expect(nextState.workouts).toEqual(workouts);
  });

  it('should handle setWorkoutPlans', () => {
    const plans = [mockWorkoutPlan];
    const nextState = workoutReducer(initialState, setWorkoutPlans(plans));

    expect(nextState.workoutPlans).toEqual(plans);
  });

  it('should handle setCurrentWorkout', () => {
    const nextState = workoutReducer(initialState, setCurrentWorkout(mockWorkout));

    expect(nextState.currentWorkout).toEqual(mockWorkout);
  });

  it('should handle setCurrentPlan', () => {
    const nextState = workoutReducer(initialState, setCurrentPlan(mockWorkoutPlan));

    expect(nextState.currentPlan).toEqual(mockWorkoutPlan);
  });

  it('should handle addWorkout', () => {
    const nextState = workoutReducer(initialState, addWorkout(mockWorkout));

    expect(nextState.workouts).toContainEqual(mockWorkout);
  });

  it('should handle addWorkoutPlan', () => {
    const nextState = workoutReducer(initialState, addWorkoutPlan(mockWorkoutPlan));

    expect(nextState.workoutPlans).toContainEqual(mockWorkoutPlan);
  });

  it('should handle updateWorkout', () => {
    const state = {
      ...initialState,
      workouts: [mockWorkout],
      currentWorkout: mockWorkout,
    };
    const updatedWorkout = { ...mockWorkout, name: 'Updated Workout' };
    const nextState = workoutReducer(state, updateWorkout(updatedWorkout));

    expect(nextState.workouts[0]).toEqual(updatedWorkout);
    expect(nextState.currentWorkout).toEqual(updatedWorkout);
  });

  it('should handle updateWorkoutPlan', () => {
    const state = {
      ...initialState,
      workoutPlans: [mockWorkoutPlan],
      currentPlan: mockWorkoutPlan,
    };
    const updatedPlan = { ...mockWorkoutPlan, name: 'Updated Plan' };
    const nextState = workoutReducer(state, updateWorkoutPlan(updatedPlan));

    expect(nextState.workoutPlans[0]).toEqual(updatedPlan);
    expect(nextState.currentPlan).toEqual(updatedPlan);
  });

  it('should handle deleteWorkout', () => {
    const state = {
      ...initialState,
      workouts: [mockWorkout],
      currentWorkout: mockWorkout,
    };
    const nextState = workoutReducer(state, deleteWorkout('1'));

    expect(nextState.workouts).not.toContainEqual(mockWorkout);
    expect(nextState.currentWorkout).toBeNull();
  });

  it('should handle deleteWorkoutPlan', () => {
    const state = {
      ...initialState,
      workoutPlans: [mockWorkoutPlan],
      currentPlan: mockWorkoutPlan,
    };
    const nextState = workoutReducer(state, deleteWorkoutPlan('1'));

    expect(nextState.workoutPlans).not.toContainEqual(mockWorkoutPlan);
    expect(nextState.currentPlan).toBeNull();
  });

  it('should handle setLoading', () => {
    const nextState = workoutReducer(initialState, setLoading(true));

    expect(nextState.isLoading).toBe(true);
  });

  it('should handle setError', () => {
    const error = 'Test error';
    const nextState = workoutReducer(initialState, setError(error));

    expect(nextState.error).toBe(error);
  });

  it('should handle setError with null', () => {
    const state = {
      ...initialState,
      error: 'Test error',
    };
    const nextState = workoutReducer(state, setError(null));

    expect(nextState.error).toBeNull();
  });
}); 