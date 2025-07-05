import apiService from './apiService';
import { Exercise } from './exerciseLibraryService';

export interface WorkoutTemplate {
  id: string;
  name: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  exercises: WorkoutExercise[];
  estimatedDuration: number;
  targetMuscleGroups: string[];
  createdAt: string;
  updatedAt: string;
}

export interface WorkoutExercise {
  exercise: Exercise;
  sets: number;
  reps: number;
  restTime: number;
  order: number;
  notes?: string;
}

export interface WorkoutSchedule {
  id: string;
  templateId: string;
  userId: string;
  scheduledDate: string;
  completed: boolean;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkoutProgress {
  id: string;
  scheduleId: string;
  exerciseProgress: ExerciseProgress[];
  startTime: string;
  endTime?: string;
  notes?: string;
}

export interface ExerciseProgress {
  exerciseId: string;
  sets: SetProgress[];
}

export interface SetProgress {
  setNumber: number;
  reps: number;
  weight?: number;
  completed: boolean;
  notes?: string;
}

class WorkoutPlanningService {
  private templates: WorkoutTemplate[] = [];
  private schedules: WorkoutSchedule[] = [];
  private progress: WorkoutProgress[] = [];
  private isLoading = false;
  private error: string | null = null;

  // Template Management
  async createTemplate(template: Omit<WorkoutTemplate, 'id' | 'createdAt' | 'updatedAt'>): Promise<WorkoutTemplate> {
    try {
      this.isLoading = true;
      const response = await apiService.post('/workout-templates', template);
      const newTemplate = response.data;
      this.templates.push(newTemplate);
      return newTemplate;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to create workout template';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getTemplates(): Promise<WorkoutTemplate[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get('/workout-templates');
      this.templates = response.data;
      return this.templates;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch workout templates';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getTemplateById(id: string): Promise<WorkoutTemplate> {
    try {
      this.isLoading = true;
      const response = await apiService.get(`/workout-templates/${id}`);
      return response.data;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch workout template';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Schedule Management
  async scheduleWorkout(schedule: Omit<WorkoutSchedule, 'id' | 'createdAt' | 'updatedAt'>): Promise<WorkoutSchedule> {
    try {
      this.isLoading = true;
      const response = await apiService.post('/workout-schedules', schedule);
      const newSchedule = response.data;
      this.schedules.push(newSchedule);
      return newSchedule;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to schedule workout';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async getSchedules(startDate: string, endDate: string): Promise<WorkoutSchedule[]> {
    try {
      this.isLoading = true;
      const response = await apiService.get('/workout-schedules', {
        params: { startDate, endDate }
      });
      this.schedules = response.data;
      return this.schedules;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to fetch workout schedules';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // Progress Tracking
  async startWorkout(scheduleId: string): Promise<WorkoutProgress> {
    try {
      this.isLoading = true;
      const response = await apiService.post('/workout-progress', {
        scheduleId,
        startTime: new Date().toISOString()
      });
      const newProgress = response.data;
      this.progress.push(newProgress);
      return newProgress;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to start workout';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async updateExerciseProgress(
    progressId: string,
    exerciseProgress: ExerciseProgress
  ): Promise<WorkoutProgress> {
    try {
      this.isLoading = true;
      const response = await apiService.put(`/workout-progress/${progressId}/exercise`, exerciseProgress);
      const updatedProgress = response.data;
      const index = this.progress.findIndex(p => p.id === progressId);
      if (index !== -1) {
        this.progress[index] = updatedProgress;
      }
      return updatedProgress;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to update exercise progress';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  async completeWorkout(progressId: string): Promise<WorkoutProgress> {
    try {
      this.isLoading = true;
      const response = await apiService.put(`/workout-progress/${progressId}/complete`, {
        endTime: new Date().toISOString()
      });
      const completedProgress = response.data;
      const index = this.progress.findIndex(p => p.id === progressId);
      if (index !== -1) {
        this.progress[index] = completedProgress;
      }
      return completedProgress;
    } catch (error) {
      this.error = error instanceof Error ? error.message : 'Failed to complete workout';
      throw error;
    } finally {
      this.isLoading = false;
    }
  }

  // State Management
  getState() {
    return {
      templates: this.templates,
      schedules: this.schedules,
      progress: this.progress,
      isLoading: this.isLoading,
      error: this.error
    };
  }
}

export const workoutPlanningService = new WorkoutPlanningService(); 