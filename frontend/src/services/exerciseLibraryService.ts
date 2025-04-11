import { apiService } from './apiService';

export enum ExerciseType {
  STRENGTH = 'strength',
  CARDIO = 'cardio',
  FLEXIBILITY = 'flexibility',
  BALANCE = 'balance'
}

export interface ExerciseFormRule {
  id: string;
  name: string;
  description: string;
  jointAngles: {
    [key: string]: {
      min: number;
      max: number;
      optimal: number;
    };
  };
  alignment: {
    vertical: string[];
    horizontal: string[];
  };
  movement: {
    path: string;
    speed: 'slow' | 'moderate' | 'fast';
    repetitionRange: {
      min: number;
      max: number;
    };
  };
}

export interface Exercise {
  id: string;
  name: string;
  type: ExerciseType;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  targetMuscles: string[];
  equipment: string[];
  formRules: ExerciseFormRule[];
  videoUrl?: string;
  thumbnailUrl?: string;
  tips: string[];
  variations: string[];
  created_at: string;
  updated_at: string;
}

class ExerciseLibraryService {
  private exercises: Map<string, Exercise> = new Map();
  private formRules: Map<string, ExerciseFormRule> = new Map();

  public async getExercises(): Promise<Exercise[]> {
    try {
      const response = await apiService.exercises.getAll();
      const exercises = response.data;
      
      // Update local cache
      exercises.forEach(exercise => {
        this.exercises.set(exercise.id, exercise);
      });

      return exercises;
    } catch (error) {
      console.error('Failed to fetch exercises:', error);
      throw error;
    }
  }

  public async getExercise(id: string): Promise<Exercise | null> {
    try {
      // Check cache first
      if (this.exercises.has(id)) {
        return this.exercises.get(id)!;
      }

      const response = await apiService.exercises.get(id);
      const exercise = response.data;
      
      // Update cache
      this.exercises.set(exercise.id, exercise);

      return exercise;
    } catch (error) {
      console.error(`Failed to fetch exercise ${id}:`, error);
      return null;
    }
  }

  public async getFormRules(exerciseId: string): Promise<ExerciseFormRule[]> {
    try {
      const exercise = await this.getExercise(exerciseId);
      if (!exercise) {
        throw new Error(`Exercise ${exerciseId} not found`);
      }
      return exercise.formRules;
    } catch (error) {
      console.error(`Failed to fetch form rules for exercise ${exerciseId}:`, error);
      throw error;
    }
  }

  public async searchExercises(query: string): Promise<Exercise[]> {
    try {
      const response = await apiService.exercises.search(query);
      return response.data;
    } catch (error) {
      console.error('Failed to search exercises:', error);
      throw error;
    }
  }

  public async filterExercises(filters: {
    type?: ExerciseType;
    difficulty?: Exercise['difficulty'];
    equipment?: string[];
    targetMuscles?: string[];
  }): Promise<Exercise[]> {
    try {
      const response = await apiService.exercises.filter(filters);
      return response.data;
    } catch (error) {
      console.error('Failed to filter exercises:', error);
      throw error;
    }
  }

  public getExerciseTypes(): ExerciseType[] {
    return Object.values(ExerciseType);
  }

  public validateForm(exerciseId: string, jointAngles: { [key: string]: number }): {
    isValid: boolean;
    feedback: string[];
  } {
    const exercise = this.exercises.get(exerciseId);
    if (!exercise) {
      return {
        isValid: false,
        feedback: ['Exercise not found']
      };
    }

    const feedback: string[] = [];
    let isValid = true;

    exercise.formRules.forEach(rule => {
      Object.entries(rule.jointAngles).forEach(([joint, angles]) => {
        const currentAngle = jointAngles[joint];
        if (currentAngle !== undefined) {
          if (currentAngle < angles.min || currentAngle > angles.max) {
            isValid = false;
            feedback.push(`${joint} angle should be between ${angles.min}° and ${angles.max}°`);
          } else if (Math.abs(currentAngle - angles.optimal) > 10) {
            feedback.push(`Try to keep ${joint} angle closer to ${angles.optimal}°`);
          }
        }
      });
    });

    return { isValid, feedback };
  }
}

export const exerciseLibraryService = new ExerciseLibraryService(); 