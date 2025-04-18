import { apiService } from './apiService';
import { Workout, WorkoutPlan } from '../types';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || '/api';

export class WorkoutService {
  async getWorkouts(): Promise<Workout[]> {
    const response = await axios.get(`${API_URL}/workouts`);
    return response.data;
  }

  async getWorkout(id: string): Promise<Workout> {
    const response = await axios.get(`${API_URL}/workouts/${id}`);
    return response.data;
  }

  async createWorkout(workout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<Workout> {
    const response = await axios.post(`${API_URL}/workouts`, workout);
    return response.data;
  }

  async updateWorkout(id: string, workout: Partial<Workout>): Promise<Workout> {
    const response = await axios.put(`${API_URL}/workouts/${id}`, workout);
    return response.data;
  }

  async deleteWorkout(id: string): Promise<void> {
    await axios.delete(`${API_URL}/workouts/${id}`);
  }

  // Workout Plans
  async getWorkoutPlans(): Promise<WorkoutPlan[]> {
    const response = await axios.get(`${API_URL}/workout-plans`);
    return response.data;
  }

  async getWorkoutPlan(id: string): Promise<WorkoutPlan> {
    const response = await axios.get(`${API_URL}/workout-plans/${id}`);
    return response.data;
  }

  async createWorkoutPlan(plan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'>): Promise<WorkoutPlan> {
    const response = await axios.post(`${API_URL}/workout-plans`, plan);
    return response.data;
  }

  async updateWorkoutPlan(id: string, plan: Partial<WorkoutPlan>): Promise<WorkoutPlan> {
    const response = await axios.put(`${API_URL}/workout-plans/${id}`, plan);
    return response.data;
  }

  async deleteWorkoutPlan(id: string): Promise<void> {
    await axios.delete(`${API_URL}/workout-plans/${id}`);
  }

  // Additional endpoints
  async getUpcomingWorkouts(days: number = 7): Promise<Workout[]> {
    const response = await axios.get(`${API_URL}/workouts/upcoming`, {
      params: { days }
    });
    return response.data;
  }

  async getActiveWorkoutPlans(): Promise<WorkoutPlan[]> {
    const response = await axios.get(`${API_URL}/workout-plans/active`);
    return response.data;
  }
}

export const workoutService = new WorkoutService(); 