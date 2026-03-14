import apiService from './apiService';
import { Exercise, ExerciseType, ExerciseDifficulty } from './exerciseLibraryService';

export interface ExerciseRecommendation {
  id: string;
  exercise: Exercise;
  confidence: number;
  reason: string;
  alternatives: Exercise[];
}

export interface RecommendationRequest {
  userId: string;
  fitnessLevel: 'beginner' | 'intermediate' | 'advanced';
  goals: string[];
  preferences: {
    equipment: string[];
    timeAvailable: number;
    targetMuscleGroups: string[];
  };
  history?: {
    completedExercises: string[];
    preferredExercises: string[];
    avoidedExercises: string[];
  };
}

export interface RecommendationResponse {
  recommendations: ExerciseRecommendation[];
  workoutPlan: {
    duration: number;
    exercises: {
      exercise: Exercise;
      sets: number;
      reps: number;
      restTime: number;
    }[];
  };
}

class ExerciseRecommendationService {
  private isLoading = false;
  private error: string | null = null;

  async getRecommendations(request: RecommendationRequest): Promise<RecommendationResponse> {
    try {
      this.isLoading = true;
      const response = await apiService.post<RecommendationResponse>('/exercise-recommendations', request);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to get exercise recommendations';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getPersonalizedWorkoutPlan(request: RecommendationRequest): Promise<RecommendationResponse> {
    try {
      this.isLoading = true;
      const response = await apiService.post<RecommendationResponse>('/workout-plan', request);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to generate workout plan';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getExerciseAlternatives(exerciseId: string): Promise<Exercise[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get<Exercise[]>(`/exercise-alternatives/${exerciseId}`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to get exercise alternatives';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async updateUserPreferences(userId: string, preferences: RecommendationRequest['preferences']): Promise<void> {
    try {
      this.isLoading = true;
      await apiService.put(`/user-preferences/${userId}`, preferences);
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to update user preferences';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getExerciseHistory(userId: string): Promise<RecommendationRequest['history']> {
    try {
      this.isLoading = true;
      const response = await apiService.get<RecommendationRequest['history']>(`/exercise-history/${userId}`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to get exercise history';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  getState() {
    return {
      isLoading: this.isLoading,
      error: this.error
    };
  }
}

export const exerciseRecommendationService = new ExerciseRecommendationService(); 