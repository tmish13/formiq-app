import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Workout, WorkoutPlan } from '../../types';

export interface WorkoutState {
  workouts: Workout[];
  workoutPlans: WorkoutPlan[];
  currentWorkout: Workout | null;
  currentPlan: WorkoutPlan | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: WorkoutState = {
  workouts: [],
  workoutPlans: [],
  currentWorkout: null,
  currentPlan: null,
  isLoading: false,
  error: null,
};

const workoutSlice = createSlice({
  name: 'workout',
  initialState,
  reducers: {
    setWorkouts: (state, action: PayloadAction<Workout[]>) => {
      state.workouts = action.payload;
    },
    setWorkoutPlans: (state, action: PayloadAction<WorkoutPlan[]>) => {
      state.workoutPlans = action.payload;
    },
    setCurrentWorkout: (state, action: PayloadAction<Workout | null>) => {
      state.currentWorkout = action.payload;
    },
    setCurrentPlan: (state, action: PayloadAction<WorkoutPlan | null>) => {
      state.currentPlan = action.payload;
    },
    addWorkout: (state, action: PayloadAction<Workout>) => {
      state.workouts.push(action.payload);
    },
    addWorkoutPlan: (state, action: PayloadAction<WorkoutPlan>) => {
      state.workoutPlans.push(action.payload);
    },
    updateWorkout: (state, action: PayloadAction<Workout>) => {
      const index = state.workouts.findIndex(w => w.id === action.payload.id);
      if (index !== -1) {
        state.workouts[index] = action.payload;
      }
      if (state.currentWorkout?.id === action.payload.id) {
        state.currentWorkout = action.payload;
      }
    },
    updateWorkoutPlan: (state, action: PayloadAction<WorkoutPlan>) => {
      const index = state.workoutPlans.findIndex(p => p.id === action.payload.id);
      if (index !== -1) {
        state.workoutPlans[index] = action.payload;
      }
      if (state.currentPlan?.id === action.payload.id) {
        state.currentPlan = action.payload;
      }
    },
    deleteWorkout: (state, action: PayloadAction<string>) => {
      state.workouts = state.workouts.filter(w => w.id !== action.payload);
      if (state.currentWorkout?.id === action.payload) {
        state.currentWorkout = null;
      }
    },
    deleteWorkoutPlan: (state, action: PayloadAction<string>) => {
      state.workoutPlans = state.workoutPlans.filter(p => p.id !== action.payload);
      if (state.currentPlan?.id === action.payload) {
        state.currentPlan = null;
      }
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
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
} = workoutSlice.actions;

export default workoutSlice.reducer; 