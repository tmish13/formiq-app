import { apiService } from './apiService';
import { 
  ExerciseConfig, 
  ExerciseConfigWithExercise, 
  ExerciseConfigCreate, 
  ExerciseConfigUpdate 
} from '../types/exerciseConfig';
import axios, { AxiosResponse } from 'axios';
import { ApiResponse } from '../types/api';

/**
 * Service for managing exercise configurations
 */
class ExerciseConfigService {
  /**
   * Base URL for exercise configuration endpoints
   */
  private baseUrl = '/api/v1/exercise-configs';

  /**
   * Get all exercise configurations
   * @param exerciseId Optional exercise ID to filter by
   * @param activeOnly Whether to only return active configurations
   * @returns List of exercise configurations
   */
  async getAll(exerciseId?: string, activeOnly = false): Promise<ExerciseConfigWithExercise[]> {
    let url = this.baseUrl;
    const params = new URLSearchParams();
    
    if (exerciseId) {
      params.append('exercise_id', exerciseId);
    }
    
    if (activeOnly) {
      params.append('active_only', 'true');
    }
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    // Use public post method to make a GET request
    const response = await apiService.post<ExerciseConfigWithExercise[]>(`/internal/fetch`, {
      method: 'GET',
      url: url
    });
    return response.data;
  }

  /**
   * Get a specific exercise configuration by ID
   * @param configId Configuration ID
   * @returns Exercise configuration with exercise details
   */
  async getById(configId: string): Promise<ExerciseConfigWithExercise> {
    // Use public post method to make a GET request
    const response = await apiService.post<ExerciseConfigWithExercise>(`/internal/fetch`, {
      method: 'GET',
      url: `${this.baseUrl}/${configId}`
    });
    return response.data;
  }

  /**
   * Get the active configuration for an exercise
   * @param exerciseId Exercise ID
   * @returns Active exercise configuration
   */
  async getActiveForExercise(exerciseId: string): Promise<ExerciseConfig> {
    // Use public post method to make a GET request
    const response = await apiService.post<ExerciseConfig>(`/internal/fetch`, {
      method: 'GET',
      url: `${this.baseUrl}/exercise/${exerciseId}/active`
    });
    return response.data;
  }

  /**
   * Create a new exercise configuration
   * @param config Configuration data
   * @returns Created configuration
   */
  async create(config: ExerciseConfigCreate): Promise<ExerciseConfig> {
    const response = await apiService.post<ExerciseConfig>(this.baseUrl, config);
    return response.data;
  }

  /**
   * Update an exercise configuration
   * @param configId Configuration ID
   * @param config Update data
   * @returns Updated configuration
   */
  async update(configId: string, config: ExerciseConfigUpdate): Promise<ExerciseConfig> {
    // Use public post method to make a PUT request
    const response = await apiService.post<ExerciseConfig>(`/internal/fetch`, {
      method: 'PUT',
      url: `${this.baseUrl}/${configId}`,
      data: config
    });
    return response.data;
  }

  /**
   * Create a new version of an exercise configuration
   * @param exerciseId Exercise ID
   * @param config Configuration data
   * @param deactivatePrevious Whether to deactivate previous versions
   * @returns Created configuration
   */
  async createNewVersion(
    exerciseId: string,
    config: ExerciseConfigCreate,
    deactivatePrevious = true
  ): Promise<ExerciseConfig> {
    let url = `${this.baseUrl}/exercise/${exerciseId}/new_version`;
    
    if (!deactivatePrevious) {
      url += '?deactivate_previous=false';
    }
    
    const response = await apiService.post<ExerciseConfig>(url, config);
    return response.data;
  }

  /**
   * Delete an exercise configuration
   * @param configId Configuration ID
   * @returns Success status
   */
  async delete(configId: string): Promise<void> {
    // Use public post method to make a DELETE request
    await apiService.post<void>(`/internal/fetch`, {
      method: 'DELETE',
      url: `${this.baseUrl}/${configId}`
    });
  }
}

/**
 * Exercise configuration service instance
 */
export const exerciseConfigService = new ExerciseConfigService();

// Add exercise config interface to apiService
if (!('exerciseConfigs' in apiService)) {
  Object.defineProperty(apiService, 'exerciseConfigs', {
    value: {
      getAll: async (exerciseId?: string, activeOnly = false): Promise<ApiResponse<ExerciseConfigWithExercise[]>> => {
        return exerciseConfigService.getAll(exerciseId, activeOnly)
          .then(data => ({ data, success: true, status: 200 }))
          .catch(error => ({ data: [], success: false, error, status: error?.response?.status || 500 }));
      },
      getById: async (configId: string): Promise<ApiResponse<ExerciseConfigWithExercise>> => {
        return exerciseConfigService.getById(configId)
          .then(data => ({ data, success: true, status: 200 }))
          .catch(error => ({ data: {} as ExerciseConfigWithExercise, success: false, error, status: error?.response?.status || 500 }));
      },
      getActiveForExercise: async (exerciseId: string): Promise<ApiResponse<ExerciseConfig>> => {
        return exerciseConfigService.getActiveForExercise(exerciseId)
          .then(data => ({ data, success: true, status: 200 }))
          .catch(error => ({ data: {} as ExerciseConfig, success: false, error, status: error?.response?.status || 500 }));
      },
      create: async (config: ExerciseConfigCreate): Promise<ApiResponse<ExerciseConfig>> => {
        return exerciseConfigService.create(config)
          .then(data => ({ data, success: true, status: 201 }))
          .catch(error => ({ data: {} as ExerciseConfig, success: false, error, status: error?.response?.status || 500 }));
      },
      update: async (configId: string, config: ExerciseConfigUpdate): Promise<ApiResponse<ExerciseConfig>> => {
        return exerciseConfigService.update(configId, config)
          .then(data => ({ data, success: true, status: 200 }))
          .catch(error => ({ data: {} as ExerciseConfig, success: false, error, status: error?.response?.status || 500 }));
      },
      createNewVersion: async (
        exerciseId: string,
        config: ExerciseConfigCreate,
        deactivatePrevious = true
      ): Promise<ApiResponse<ExerciseConfig>> => {
        return exerciseConfigService.createNewVersion(exerciseId, config, deactivatePrevious)
          .then(data => ({ data, success: true, status: 201 }))
          .catch(error => ({ data: {} as ExerciseConfig, success: false, error, status: error?.response?.status || 500 }));
      },
      delete: async (configId: string): Promise<ApiResponse<void>> => {
        return exerciseConfigService.delete(configId)
          .then(() => ({ data: undefined, success: true, status: 204 }))
          .catch(error => ({ data: undefined, success: false, error, status: error?.response?.status || 500 }));
      }
    },
    writable: false
  });
} 