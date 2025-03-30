import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { workoutService } from '../services/workoutService';
import {
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
} from '../store/slices/workoutSlice';
import { Workout, WorkoutPlan } from '../types';

export const useWorkout = () => {
  const dispatch = useDispatch();
  const {
    workouts,
    workoutPlans,
    currentWorkout,
    currentPlan,
    isLoading,
    error,
  } = useSelector((state: RootState) => state.workout);

  const fetchWorkouts = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.getWorkouts();
      dispatch(setWorkouts(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch workouts'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchWorkout = useCallback(async (id: string) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.getWorkout(id);
      dispatch(setCurrentWorkout(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch workout'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const createWorkout = useCallback(async (workout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.createWorkout(workout);
      dispatch(addWorkout(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to create workout'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const updateWorkoutData = useCallback(async (id: string, workout: Partial<Workout>) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.updateWorkout(id, workout);
      dispatch(updateWorkout(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to update workout'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const removeWorkout = useCallback(async (id: string) => {
    try {
      dispatch(setLoading(true));
      await workoutService.deleteWorkout(id);
      dispatch(deleteWorkout(id));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to delete workout'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchWorkoutPlans = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.getWorkoutPlans();
      dispatch(setWorkoutPlans(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch workout plans'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchWorkoutPlan = useCallback(async (id: string) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.getWorkoutPlan(id);
      dispatch(setCurrentPlan(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch workout plan'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const createWorkoutPlan = useCallback(async (plan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'>) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.createWorkoutPlan(plan);
      dispatch(addWorkoutPlan(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to create workout plan'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const updateWorkoutPlanData = useCallback(async (id: string, plan: Partial<WorkoutPlan>) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.updateWorkoutPlan(id, plan);
      dispatch(updateWorkoutPlan(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to update workout plan'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const removeWorkoutPlan = useCallback(async (id: string) => {
    try {
      dispatch(setLoading(true));
      await workoutService.deleteWorkoutPlan(id);
      dispatch(deleteWorkoutPlan(id));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to delete workout plan'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchUpcomingWorkouts = useCallback(async (days: number = 7) => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.getUpcomingWorkouts(days);
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch upcoming workouts'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchActiveWorkoutPlans = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      const data = await workoutService.getActiveWorkoutPlans();
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch active workout plans'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  return {
    workouts,
    workoutPlans,
    currentWorkout,
    currentPlan,
    isLoading,
    error,
    fetchWorkouts,
    fetchWorkout,
    createWorkout,
    updateWorkout: updateWorkoutData,
    deleteWorkout: removeWorkout,
    fetchWorkoutPlans,
    fetchWorkoutPlan,
    createWorkoutPlan,
    updateWorkoutPlan: updateWorkoutPlanData,
    deleteWorkoutPlan: removeWorkoutPlan,
    fetchUpcomingWorkouts,
    fetchActiveWorkoutPlans,
  };
}; 