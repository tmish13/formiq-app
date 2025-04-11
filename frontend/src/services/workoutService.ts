import { apiService } from './apiService';
import { Workout, WorkoutPlan } from '../types';
import { ApiResponse } from './apiService';

export class WorkoutService {
  async getWorkouts(): Promise<Workout[]> {
    const response = await apiService.formChecks.getAll();
    return response.data.data;
  }

  async getWorkout(id: string): Promise<Workout> {
    const response = await apiService.formChecks.getById(id);
    return response.data.data;
  }

  async createWorkout(workout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<Workout> {
    const formData = new FormData();
    formData.append('workout', JSON.stringify(workout));
    const response = await apiService.formChecks.upload(formData);
    return response.data.data;
  }

  async updateWorkout(id: string, workout: Partial<Workout>): Promise<Workout> {
    const formData = new FormData();
    formData.append('workout', JSON.stringify(workout));
    const response = await apiService.formChecks.upload(formData);
    return response.data.data;
  }

  async deleteWorkout(id: string): Promise<void> {
    await apiService.formChecks.getById(id); // TODO: Add delete endpoint
  }

  // Workout Plans
  async getWorkoutPlans(): Promise<WorkoutPlan[]> {
    const response = await apiService.formChecks.getAll();
    return response.data.data;
  }

  async getWorkoutPlan(id: string): Promise<WorkoutPlan> {
    const response = await apiService.formChecks.getById(id);
    return response.data.data;
  }

  async createWorkoutPlan(plan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<WorkoutPlan> {
    const formData = new FormData();
    formData.append('plan', JSON.stringify(plan));
    const response = await apiService.formChecks.upload(formData);
    return response.data.data;
  }

  async updateWorkoutPlan(id: string, plan: Partial<WorkoutPlan>): Promise<WorkoutPlan> {
    const formData = new FormData();
    formData.append('plan', JSON.stringify(plan));
    const response = await apiService.formChecks.upload(formData);
    return response.data.data;
  }

  async deleteWorkoutPlan(id: string): Promise<void> {
    await apiService.formChecks.getById(id); // TODO: Add delete endpoint
  }

  // Additional endpoints
  async getUpcomingWorkouts(days: number = 7): Promise<Workout[]> {
    const response = await apiService.formChecks.getAll();
    return response.data.data;
  }

  async getActiveWorkoutPlans(): Promise<WorkoutPlan[]> {
    const response = await apiService.formChecks.getAll();
    return response.data.data;
  }
}

export const workoutService = new WorkoutService(); 