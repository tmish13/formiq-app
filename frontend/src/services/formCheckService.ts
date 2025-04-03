import { apiService } from './api';
import { ExerciseType } from '../types';
import { FormCheck, FeedbackItem } from '../types/formCheck';

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

  // Submit form check with already uploaded video URL
  async submitFormCheckWithUrl(
    videoUrl: string,
    exerciseType: ExerciseType,
    notes?: string
  ): Promise<FormCheck> {
    return apiService.post<FormCheck>('/form-checks/with-url', {
      video_url: videoUrl,
      exercise_type: exerciseType,
      notes: notes || '',
    });
  },

  // Get presigned URL for direct upload
  async getPresignedUploadUrl(
    filename: string,
    contentType: string,
    exerciseType: ExerciseType
  ): Promise<{
    post_data: {
      url: string;
      fields: Record<string, string>;
    };
    file_url: string;
    file_key: string;
  }> {
    return apiService.post('/form-checks/presigned-upload', {
      filename,
      content_type: contentType,
      exercise_type: exerciseType,
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
  
  // Add feedback to form check
  async addFeedback(
    formCheckId: number,
    feedbackData: {
      feedbackType: string;
      severity: string;
      timestamp: number;
      description: string;
      suggestions?: string;
      isAiGenerated?: boolean;
    }
  ): Promise<FeedbackItem> {
    return apiService.post<FeedbackItem>(`/form-checks/${formCheckId}/feedback`, {
      feedback_type: feedbackData.feedbackType,
      severity: feedbackData.severity,
      timestamp: feedbackData.timestamp,
      description: feedbackData.description,
      suggestions: feedbackData.suggestions || '',
      is_ai_generated: feedbackData.isAiGenerated || false,
    });
  },
  
  // Get feedback items for a form check
  async getFeedbackItems(formCheckId: number): Promise<FeedbackItem[]> {
    return apiService.get<FeedbackItem[]>(`/form-checks/${formCheckId}/feedback`);
  },
}; 