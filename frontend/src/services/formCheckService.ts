import { apiService } from './api';
import { FormCheck, ExerciseType, FormCheckStatus } from '../types';

class FormCheckService {
  private baseUrl = '/api/form-checks';

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
}

export const formCheckService = new FormCheckService(); 