import apiService from './apiService';
import { FormCheck, ExerciseType, FormCheckStatus } from '../types/formCheck';

export class FormCheckService {
  private static instance: FormCheckService | null = null;
  private baseUrl = '/api/form-checks';

  private constructor() {}

  public static getInstance(): FormCheckService {
    if (!FormCheckService.instance) {
      FormCheckService.instance = new FormCheckService();
    }
    return FormCheckService.instance;
  }

  async getFormChecks(): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(this.baseUrl);
    return response.data;
  }

  async getFormCheck(id: string): Promise<FormCheck> {
    const response = await apiService.get<FormCheck>(`${this.baseUrl}/${id}`);
    return response.data;
  }

  async createFormCheck(formCheckData: Partial<FormCheck>): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(this.baseUrl, formCheckData);
    return response.data;
  }

  async updateFormCheck(id: string, formCheckData: Partial<FormCheck>): Promise<FormCheck> {
    const response = await apiService.put<FormCheck>(`${this.baseUrl}/${id}`, formCheckData);
    return response.data;
  }

  async deleteFormCheck(id: number | string): Promise<void> {
    await apiService.delete(`${this.baseUrl}/${id}`);
  }

  async getFormChecksByExerciseType(exerciseType: ExerciseType): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/exercise/${exerciseType}`);
    return response.data;
  }

  async getLatestFormChecks(limit: number = 5): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/latest`, {
      params: { limit }
    });
    return response.data;
  }

  async updateFormCheckStatus(id: string, status: FormCheckStatus): Promise<FormCheck> {
    const response = await apiService.patch<FormCheck>(`${this.baseUrl}/${id}/status`, { status });
    return response.data;
  }

  // Add the missing methods needed by the useFormCheck hook
  async uploadVideo(
    video: File, 
    exerciseType: ExerciseType, 
    onProgress?: (progress: number) => void
  ): Promise<FormCheck> {
    const formData = new FormData();
    formData.append('video', video);
    formData.append('exerciseType', exerciseType);

    const response = await apiService.post<FormCheck>(`${this.baseUrl}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      }
    });
    
    return response.data;
  }

  async analyze(id: string): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(`${this.baseUrl}/${id}/analyze`);
    return response.data;
  }

  async getHistory(): Promise<FormCheck[]> {
    const response = await apiService.get<FormCheck[]>(`${this.baseUrl}/history`);
    return response.data;
  }

  // ML-specific methods

  async getMLAnalysis(id: string): Promise<{
    ml_scores?: {
      posture_score: number;
      stability_score: number;
      depth_score: number;
      confidence?: number;
    };
    pose_data?: any[];
    detected_issues?: any[];
  }> {
    const response = await apiService.get(`${this.baseUrl}/${id}/ml-analysis`);
    return response.data;
  }

  async getReferencePose(exerciseType: ExerciseType): Promise<any> {
    const response = await apiService.get(`/api/exercises/${exerciseType}/reference-pose`);
    return response.data;
  }

  async exportAnalysisFrame(id: string, frameIndex: number): Promise<Blob> {
    const response = await apiService.get(`${this.baseUrl}/${id}/export-frame/${frameIndex}`, {
      responseType: 'blob'
    });
    return response.data;
  }

  async getFormCheckComparison(currentId: string, previousId: string): Promise<{
    current: FormCheck;
    previous: FormCheck;
    improvements: {
      posture_improvement: number;
      stability_improvement: number;
      depth_improvement: number;
      overall_improvement: number;
    };
  }> {
    const response = await apiService.get(`${this.baseUrl}/compare/${currentId}/${previousId}`);
    return response.data;
  }

  async getMLModelInfo(): Promise<{
    version: string;
    supported_exercises: string[];
    confidence_threshold: number;
    last_updated: string;
  }> {
    const response = await apiService.get('/api/ml/model-info');
    return response.data;
  }

  async requestMLReanalysis(id: string): Promise<FormCheck> {
    const response = await apiService.post<FormCheck>(`${this.baseUrl}/${id}/reanalyze`);
    return response.data;
  }
}

export const formCheckService = FormCheckService.getInstance(); 