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
    const params: any = {};
    
    if (exerciseId) {
      params.exercise_id = exerciseId;
    }
    
    if (activeOnly) {
      params.active_only = true;
    }
    
    const response = await apiService.get<ExerciseConfigWithExercise[]>('/exercise-configs', params);
    return response.data;
  }

  /**
   * Get a specific exercise configuration by ID
   * @param configId Configuration ID
   * @returns Exercise configuration with exercise details
   */
  async getById(configId: string): Promise<ExerciseConfigWithExercise> {
    const response = await apiService.get<ExerciseConfigWithExercise>(`/exercise-configs/${configId}`);
    return response.data;
  }

  /**
   * Get the active configuration for an exercise
   * @param exerciseId Exercise ID
   * @returns Active exercise configuration
   */
  async getActiveForExercise(exerciseId: string): Promise<ExerciseConfig> {
    const response = await apiService.get<ExerciseConfig>(`/exercise-configs/exercise/${exerciseId}/active`);
    return response.data;
  }

  /**
   * Create a new exercise configuration
   * @param config Configuration data
   * @returns Created configuration
   */
  async create(config: ExerciseConfigCreate): Promise<ExerciseConfig> {
    const response = await apiService.post<ExerciseConfig>('/exercise-configs', config);
    return response.data;
  }

  /**
   * Update an exercise configuration
   * @param configId Configuration ID
   * @param config Update data
   * @returns Updated configuration
   */
  async update(configId: string, config: ExerciseConfigUpdate): Promise<ExerciseConfig> {
    const response = await apiService.put<ExerciseConfig>(`/exercise-configs/${configId}`, config);
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
    const params = deactivatePrevious ? {} : { deactivate_previous: false };
    const response = await apiService.post<ExerciseConfig>(
      `/exercise-configs/exercise/${exerciseId}/new_version`,
      config,
      { params }
    );
    return response.data;
  }

  /**
   * Delete an exercise configuration
   * @param configId Configuration ID
   * @returns Success status
   */
  async delete(configId: string): Promise<void> {
    await apiService.delete(`/exercise-configs/${configId}`);
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