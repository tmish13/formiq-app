import apiService from './apiService';

export enum ExerciseType {
  STRENGTH = 'strength',
  CARDIO = 'cardio',
  FLEXIBILITY = 'flexibility',
  BALANCE = 'balance'
}

export enum ExerciseDifficulty {
  BEGINNER = 'beginner',
  INTERMEDIATE = 'intermediate',
  ADVANCED = 'advanced'
}

export interface ExerciseLibraryFilters {
  searchQuery?: string;
  type?: ExerciseType;
  difficulty?: ExerciseDifficulty;
  muscleGroups?: string[];
  equipment?: string[];
  duration?: {
    min: number;
    max: number;
  };
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
  difficulty: ExerciseDifficulty;
  targetMuscles: string[];
  equipment: string[];
  formRules: ExerciseFormRule[];
  videoUrl?: string;
  thumbnailUrl?: string;
  tips: string[];
  variations: string[];
  created_at: string;
  updated_at: string;
  metrics?: {
    recommendedSets: number;
    recommendedReps: number;
    restTime?: number;
  };
}

class ExerciseLibraryService {
  private exercises: Map<string, Exercise> = new Map();
  private formRules: Map<string, ExerciseFormRule> = new Map();

  public async getExercises(filters?: {
    type?: string;
    difficulty?: string;
    muscleGroups?: string[];
    searchQuery?: string;
  }): Promise<Exercise[]> {
    try {
      // Convert frontend filters to backend format
      const backendFilters = {
        type: filters?.type,
        difficulty: filters?.difficulty,
        muscleGroups: filters?.muscleGroups,
        search: filters?.searchQuery
      };

      const exercises = await apiService.getExercises(backendFilters);
      
      // Update local cache
      exercises.forEach(exercise => {
        this.exercises.set(exercise.id, exercise);
      });

      return exercises;
    } catch (error) {
      console.error('Failed to fetch exercises:', error);
      
      // Return mock data for development if backend is not available
      return this.getMockExercises(filters);
    }
  }

  private getMockExercises(filters?: any): Exercise[] {
    const mockExercises: Exercise[] = [
      {
        id: '1',
        name: 'Barbell Squat',
        type: ExerciseType.STRENGTH,
        description: 'A compound exercise that targets the quadriceps, hamstrings, and glutes.',
        difficulty: ExerciseDifficulty.INTERMEDIATE,
        targetMuscles: ['Quadriceps', 'Hamstrings', 'Glutes'],
        equipment: ['Barbell'],
        formRules: [],
        thumbnailUrl: '/placeholder-exercise.jpg',
        tips: ['Keep your chest up', 'Drive through your heels'],
        variations: ['Front Squat', 'Goblet Squat'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metrics: {
          recommendedSets: 3,
          recommendedReps: 12
        }
      },
      {
        id: '2',
        name: 'Deadlift',
        type: ExerciseType.STRENGTH,
        description: 'A compound exercise that works the entire posterior chain.',
        difficulty: ExerciseDifficulty.ADVANCED,
        targetMuscles: ['Hamstrings', 'Glutes', 'Back'],
        equipment: ['Barbell'],
        formRules: [],
        thumbnailUrl: '/placeholder-exercise.jpg',
        tips: ['Keep the bar close to your body', 'Maintain neutral spine'],
        variations: ['Romanian Deadlift', 'Sumo Deadlift'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metrics: {
          recommendedSets: 3,
          recommendedReps: 8
        }
      },
      {
        id: '3',
        name: 'Push-ups',
        type: ExerciseType.STRENGTH,
        description: 'A bodyweight exercise that targets the chest, shoulders, and triceps.',
        difficulty: ExerciseDifficulty.BEGINNER,
        targetMuscles: ['Chest', 'Shoulders', 'Triceps'],
        equipment: ['Bodyweight'],
        formRules: [],
        thumbnailUrl: '/placeholder-exercise.jpg',
        tips: ['Keep your body in a straight line', 'Lower until chest nearly touches ground'],
        variations: ['Incline Push-ups', 'Diamond Push-ups'],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        metrics: {
          recommendedSets: 3,
          recommendedReps: 15
        }
      }
    ];

    // Apply filters to mock data
    let filteredExercises = mockExercises;

    if (filters?.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      filteredExercises = filteredExercises.filter(ex => 
        ex.name.toLowerCase().includes(query) ||
        ex.description.toLowerCase().includes(query)
      );
    }

    if (filters?.type) {
      filteredExercises = filteredExercises.filter(ex => ex.type === filters.type);
    }

    if (filters?.difficulty) {
      filteredExercises = filteredExercises.filter(ex => ex.difficulty === filters.difficulty);
    }

    if (filters?.muscleGroups?.length) {
      filteredExercises = filteredExercises.filter(ex => 
        ex.targetMuscles.some(muscle => 
          filters.muscleGroups!.includes(muscle)
        )
      );
    }

    return filteredExercises;
  }

  public async getExercise(id: string): Promise<Exercise | null> {
    try {
      // Check cache first
      if (this.exercises.has(id)) {
        return this.exercises.get(id)!;
      }

      const exercise = await apiService.getExercise(id);
      
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
      const exercises = await apiService.getExercises({ search: query } as any);
      return exercises;
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
      const exercises = await apiService.getExercises({
        type: filters.type,
        difficulty: filters.difficulty,
        muscleGroups: filters.targetMuscles,
        equipment: filters.equipment
      } as any);
      return exercises;
    } catch (error) {
      console.error('Failed to filter exercises:', error);
      throw error;
    }
  }

  public getExerciseTypes(): ExerciseType[] {
    return Object.values(ExerciseType);
  }

  public async getMuscleGroups(): Promise<string[]> {
    // In a real implementation, this would come from the backend
    // For now, return common muscle groups
    return [
      'Chest', 'Back', 'Shoulders', 'Arms', 'Legs', 'Core',
      'Biceps', 'Triceps', 'Quadriceps', 'Hamstrings', 'Glutes', 'Calves'
    ];
  }

  public async getEquipment(): Promise<string[]> {
    // In a real implementation, this would come from the backend
    // For now, return common equipment
    return [
      'Barbell', 'Dumbbell', 'Kettlebell', 'Resistance Bands',
      'Pull-up Bar', 'Bench', 'Machine', 'Bodyweight', 'Cable'
    ];
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