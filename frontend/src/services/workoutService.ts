import { apiService } from './api';
import { Workout, WorkoutPlan } from '../types';

export const workoutService = {
  // Workout endpoints
  async getWorkouts(): Promise<Workout[]> {
    return apiService.get<Workout[]>('/workouts');
  },

  async getWorkout(id: string): Promise<Workout> {
    return apiService.get<Workout>(`/workouts/${id}`);
  },

  async createWorkout(workout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<Workout> {
    return apiService.post<Workout>('/workouts', workout);
  },

  async updateWorkout(id: string, workout: Partial<Workout>): Promise<Workout> {
    return apiService.put<Workout>(`/workouts/${id}`, workout);
  },

  async deleteWorkout(id: string): Promise<void> {
    return apiService.delete<void>(`/workouts/${id}`);
  },

  // Workout plan endpoints
  async getWorkoutPlans(): Promise<WorkoutPlan[]> {
    return apiService.get<WorkoutPlan[]>('/workout-plans');
  },

  async getWorkoutPlan(id: string): Promise<WorkoutPlan> {
    return apiService.get<WorkoutPlan>(`/workout-plans/${id}`);
  },

  async createWorkoutPlan(plan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<WorkoutPlan> {
    return apiService.post<WorkoutPlan>('/workout-plans', plan);
  },

  async updateWorkoutPlan(id: string, plan: Partial<WorkoutPlan>): Promise<WorkoutPlan> {
    return apiService.put<WorkoutPlan>(`/workout-plans/${id}`, plan);
  },

  async deleteWorkoutPlan(id: string): Promise<void> {
    return apiService.delete<void>(`/workout-plans/${id}`);
  },

  // Additional endpoints
  async getUpcomingWorkouts(days: number = 7): Promise<Workout[]> {
    return apiService.get<Workout[]>(`/workouts/upcoming?days=${days}`);
  },

  async getActiveWorkoutPlans(): Promise<WorkoutPlan[]> {
    return apiService.get<WorkoutPlan[]>('/workout-plans/active');
  },
}; 