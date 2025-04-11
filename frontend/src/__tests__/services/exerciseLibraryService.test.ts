import { exerciseLibraryService, Exercise, ExerciseType, ExerciseDifficulty } from '../../services/exerciseLibraryService';
import { apiService } from '../../services/apiService';

// Mock the apiService
jest.mock('../../services/apiService', () => ({
  apiService: {
    exercises: {
      list: jest.fn(),
      get: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    },
  },
}));

describe('ExerciseLibraryService', () => {
  const mockExercise: Exercise = {
    id: '1',
    name: 'Test Exercise',
    description: 'Test Description',
    type: ExerciseType.STRENGTH,
    difficulty: ExerciseDifficulty.BEGINNER,
    muscleGroups: ['Quadriceps', 'Hamstrings'],
    equipment: ['Dumbbell'],
    instructions: ['Step 1', 'Step 2'],
    videoUrl: 'https://example.com/video',
    thumbnailUrl: 'https://example.com/thumbnail',
    duration: 300,
    caloriesBurned: 100,
    tags: ['test', 'exercise'],
    metrics: {
      recommendedSets: 3,
      recommendedReps: 12,
      restTime: 60,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getExercises', () => {
    it('should fetch exercises with filters', async () => {
      const mockFilters = {
        type: ExerciseType.STRENGTH,
        difficulty: ExerciseDifficulty.BEGINNER,
      };
      const mockResponse = { data: [mockExercise] };
      (apiService.exercises.list as jest.Mock).mockResolvedValue(mockResponse);

      const result = await exerciseLibraryService.getExercises(mockFilters);

      expect(apiService.exercises.list).toHaveBeenCalledWith(mockFilters);
      expect(result).toEqual([mockExercise]);
    });

    it('should handle errors when fetching exercises', async () => {
      const error = new Error('Failed to fetch exercises');
      (apiService.exercises.list as jest.Mock).mockRejectedValue(error);

      await expect(exerciseLibraryService.getExercises()).rejects.toThrow('Failed to fetch exercises');
    });
  });

  describe('getExerciseById', () => {
    it('should fetch a single exercise by id', async () => {
      const mockResponse = { data: mockExercise };
      (apiService.exercises.get as jest.Mock).mockResolvedValue(mockResponse);

      const result = await exerciseLibraryService.getExerciseById('1');

      expect(apiService.exercises.get).toHaveBeenCalledWith('1');
      expect(result).toEqual(mockExercise);
    });

    it('should handle errors when fetching exercise by id', async () => {
      const error = new Error('Exercise not found');
      (apiService.exercises.get as jest.Mock).mockRejectedValue(error);

      await expect(exerciseLibraryService.getExerciseById('1')).rejects.toThrow('Exercise not found');
    });
  });

  describe('createExercise', () => {
    it('should create a new exercise', async () => {
      const newExercise = { ...mockExercise, id: undefined };
      const mockResponse = { data: mockExercise };
      (apiService.exercises.create as jest.Mock).mockResolvedValue(mockResponse);

      const result = await exerciseLibraryService.createExercise(newExercise);

      expect(apiService.exercises.create).toHaveBeenCalledWith(newExercise);
      expect(result).toEqual(mockExercise);
    });

    it('should handle errors when creating exercise', async () => {
      const error = new Error('Failed to create exercise');
      (apiService.exercises.create as jest.Mock).mockRejectedValue(error);

      await expect(exerciseLibraryService.createExercise(mockExercise)).rejects.toThrow('Failed to create exercise');
    });
  });

  describe('updateExercise', () => {
    it('should update an existing exercise', async () => {
      const updatedExercise = { ...mockExercise, name: 'Updated Exercise' };
      const mockResponse = { data: updatedExercise };
      (apiService.exercises.update as jest.Mock).mockResolvedValue(mockResponse);

      const result = await exerciseLibraryService.updateExercise('1', updatedExercise);

      expect(apiService.exercises.update).toHaveBeenCalledWith('1', updatedExercise);
      expect(result).toEqual(updatedExercise);
    });

    it('should handle errors when updating exercise', async () => {
      const error = new Error('Failed to update exercise');
      (apiService.exercises.update as jest.Mock).mockRejectedValue(error);

      await expect(exerciseLibraryService.updateExercise('1', mockExercise)).rejects.toThrow('Failed to update exercise');
    });
  });

  describe('deleteExercise', () => {
    it('should delete an exercise', async () => {
      (apiService.exercises.delete as jest.Mock).mockResolvedValue({});

      await exerciseLibraryService.deleteExercise('1');

      expect(apiService.exercises.delete).toHaveBeenCalledWith('1');
    });

    it('should handle errors when deleting exercise', async () => {
      const error = new Error('Failed to delete exercise');
      (apiService.exercises.delete as jest.Mock).mockRejectedValue(error);

      await expect(exerciseLibraryService.deleteExercise('1')).rejects.toThrow('Failed to delete exercise');
    });
  });

  describe('getMuscleGroups', () => {
    it('should return a list of muscle groups', async () => {
      const result = await exerciseLibraryService.getMuscleGroups();

      expect(result).toEqual([
        'Quadriceps', 'Hamstrings', 'Calves', 'Glutes',
        'Chest', 'Back', 'Shoulders', 'Biceps', 'Triceps',
        'Core', 'Forearms', 'Trapezius', 'Lats', 'Obliques'
      ]);
    });
  });

  describe('getEquipment', () => {
    it('should return a list of equipment', async () => {
      const result = await exerciseLibraryService.getEquipment();

      expect(result).toEqual([
        'Dumbbells', 'Barbell', 'Kettlebell', 'Resistance Bands',
        'Pull-up Bar', 'Bench', 'Mat', 'Medicine Ball',
        'Foam Roller', 'Jump Rope', 'None'
      ]);
    });
  });
}); 