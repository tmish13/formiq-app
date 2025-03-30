import { apiService } from './api';
import { ExerciseType } from '../types';
import { FormCheck } from '../types/formCheck';

export const formCheckService = {
  // Submit form check
  async submitFormCheck(
    video: File,
    exerciseType: ExerciseType,
    notes?: string
  ): Promise<FormCheck> {
    const formData = new FormData();
    formData.append('video', video);
    formData.append('exercise_type', exerciseType);
    if (notes) {
      formData.append('notes', notes);
    }
    return apiService.post<FormCheck>('/form-checks', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Get form check by ID
  async getFormCheck(id: number): Promise<FormCheck> {
    return apiService.get<FormCheck>(`/form-checks/${id}`);
  },

  // Get user's form checks
  async getUserFormChecks(): Promise<FormCheck[]> {
    return apiService.get<FormCheck[]>('/form-checks');
  },

  // Get form check by exercise type
  async getFormChecksByExercise(exerciseType: ExerciseType): Promise<FormCheck[]> {
    return apiService.get<FormCheck[]>(`/form-checks/exercise/${exerciseType}`);
  },

  // Delete form check
  async deleteFormCheck(id: number): Promise<void> {
    return apiService.delete<void>(`/form-checks/${id}`);
  },

  // Complete form check analysis
  async completeAnalysis(
    id: number,
    summary: string,
    overallScore: number
  ): Promise<FormCheck> {
    return apiService.post<FormCheck>(`/form-checks/${id}/complete`, {
      summary,
      overall_score: overallScore,
    });
  },
}; 