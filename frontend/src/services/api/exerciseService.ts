import { BaseApiService, ApiResponse } from './baseApi';

export interface Exercise {
  id: string;
  name: string;
  type: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  targetMuscles: string[];
  description: string;
  instructions: string[];
  videoUrl?: string;
  thumbnailUrl?: string;
  metrics: {
    caloriesPerMinute: number;
    recommendedSets: number;
    recommendedReps: number;
    restBetweenSets: number;
  };
}

export interface ExerciseProgress {
  id: string;
  exerciseId: string;
  userId: string;
  date: string;
  sets: Array<{
    reps: number;
    weight?: number;
    duration?: number;
    formScore: number;
  }>;
  notes?: string;
}

export interface FormAnalysis {
  score: number;
  feedback: Array<{
    type: 'success' | 'warning' | 'error';
    message: string;
    timestamp: number;
  }>;
  keypoints: Array<{
    name: string;
    coordinates: [number, number];
    confidence: number;
  }>;
}

class ExerciseService extends BaseApiService {
  private static instance: ExerciseService | null = null;

  private constructor() {
    super();
  }

  public static getInstance(): ExerciseService {
    if (!ExerciseService.instance) {
      ExerciseService.instance = new ExerciseService();
    }
    return ExerciseService.instance;
  }

  public async getAllExercises(filters?: {
    type?: string;
    difficulty?: string;
    targetMuscle?: string;
  }): Promise<ApiResponse<Exercise[]>> {
    const queryParams = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value) queryParams.append(key, value);
      });
    }
    return this.get<Exercise[]>(`/exercises?${queryParams.toString()}`);
  }

  public async getExerciseById(id: string): Promise<ApiResponse<Exercise>> {
    return this.get<Exercise>(`/exercises/${id}`);
  }

  public async getExerciseProgress(exerciseId: string): Promise<ApiResponse<ExerciseProgress[]>> {
    return this.get<ExerciseProgress[]>(`/exercises/${exerciseId}/progress`);
  }

  public async saveExerciseProgress(
    exerciseId: string,
    progress: Omit<ExerciseProgress, 'id' | 'exerciseId' | 'userId'>
  ): Promise<ApiResponse<ExerciseProgress>> {
    return this.post<ExerciseProgress>(`/exercises/${exerciseId}/progress`, progress);
  }

  public async analyzeForm(
    exerciseId: string,
    videoData: Blob
  ): Promise<ApiResponse<FormAnalysis>> {
    const formData = new FormData();
    formData.append('video', videoData);
    
    return this.post<FormAnalysis>(`/exercises/${exerciseId}/analyze`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  public async getRecommendedExercises(): Promise<ApiResponse<Exercise[]>> {
    return this.get<Exercise[]>('/exercises/recommended');
  }

  public async getFeaturedWorkouts(): Promise<ApiResponse<Exercise[]>> {
    return this.get<Exercise[]>('/exercises/featured');
  }

  public async getExerciseHistory(
    page: number = 1,
    limit: number = 10
  ): Promise<ApiResponse<ExerciseProgress[]>> {
    return this.get<ExerciseProgress[]>(`/exercises/history?page=${page}&limit=${limit}`);
  }

  public async updateExerciseNotes(
    progressId: string,
    notes: string
  ): Promise<ApiResponse<ExerciseProgress>> {
    return this.put<ExerciseProgress>(`/exercises/progress/${progressId}/notes`, { notes });
  }
}

export const exerciseService = ExerciseService.getInstance();
export default exerciseService; 