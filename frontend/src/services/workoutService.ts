import apiServiceService from './apiServiceService';
import { Workout, WorkoutPlan } from '../types';

const API_PATH = '/apiService';

export class WorkoutService {
  async getWorkouts(): Promise<Workout[]> {
    const response = await apiServiceService.get(`${API_PATH}/workouts`);
    return response.data;
  }

  async getWorkout(id: string): Promise<Workout> {
    const response = await apiServiceService.get(`${API_PATH}/workouts/${id}`);
    return response.data;
  }

  async createWorkout(workout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<Workout> {
    const response = await apiServiceService.post(`${API_PATH}/workouts`, workout);
    return response.data;
  }

  async updateWorkout(id: string, workout: Partial<Workout>): Promise<Workout> {
    const response = await apiServiceService.put(`${API_PATH}/workouts/${id}`, workout);
    return response.data;
  }

  async deleteWorkout(id: string): Promise<void> {
    await apiService.delete(`${API_PATH}/workouts/${id}`);
  }

  // Workout Plans
  async getWorkoutPlans(): Promise<WorkoutPlan[]> {
    const response = await apiService.get(`${API_PATH}/workout-plans`);
    return response.data;
  }

  async getWorkoutPlan(id: string): Promise<WorkoutPlan> {
    const response = await apiService.get(`${API_PATH}/workout-plans/${id}`);
    return response.data;
  }

  async createWorkoutPlan(plan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<WorkoutPlan> {
    const response = await apiService.post(`${API_PATH}/workout-plans`, plan);
    return response.data;
  }

  async updateWorkoutPlan(id: string, plan: Partial<WorkoutPlan>): Promise<WorkoutPlan> {
    const response = await apiService.put(`${API_PATH}/workout-plans/${id}`, plan);
    return response.data;
  }

  async deleteWorkoutPlan(id: string): Promise<void> {
    await apiService.delete(`${API_PATH}/workout-plans/${id}`);
  }

  // Additional endpoints
  async getUpcomingWorkouts(days: number = 7): Promise<Workout[]> {
    const response = await apiService.get(`${API_PATH}/workouts/upcoming`, {
      params: { days }
    });
    return response.data;
  }

  async getActiveWorkoutPlans(): Promise<WorkoutPlan[]> {
    const response = await apiService.get(`${API_PATH}/workout-plans/active`);
    return response.data;
  }
}

export const workoutService = new WorkoutService(); 