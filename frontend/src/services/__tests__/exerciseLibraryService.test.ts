import { exerciseLibraryService, Exercise, ExerciseType, ExerciseFormRule } from '../../../src/services/exerciseLibraryService';
import { apiService } from '../../../src/services/apiService';

// Mock the apiService
jest.mock('../../../src/services/apiService', () => ({
  apiService: {
    exercises: {
      getAll: jest.fn().mockResolvedValue({ data: [], status: 200 }),
      get: jest.fn().mockResolvedValue({ data: {}, status: 200 }),
      search: jest.fn(),
      filter: jest.fn(),
    },
  },
}));

describe('ExerciseLibraryService', () => {
  const mockFormRule: ExerciseFormRule = {
    id: '1',
    name: 'Squat Form Rule',
    description: 'Proper squat form guidelines',
    jointAngles: {
      knee: {
        min: 80,
        max: 100,
        optimal: 90
      },
      hip: {
        min: 70,
        max: 90,
        optimal: 80
      }
    },
    alignment: {
      vertical: ['spine', 'neck'],
      horizontal: ['shoulders', 'hips']
    },
    movement: {
      path: 'down-up',
      speed: 'moderate',
      repetitionRange: {
        min: 8,
        max: 12
      }
    }
  };

  const mockExercise: Exercise = {
    id: '1',
    name: 'Test Exercise',
    description: 'Test Description',
    type: ExerciseType.STRENGTH,
    difficulty: 'beginner',
    targetMuscles: ['Quadriceps', 'Hamstrings'],
    equipment: ['Dumbbell'],
    formRules: [mockFormRule],
    videoUrl: 'https://example.com/video',
    thumbnailUrl: 'https://example.com/thumbnail',
    tips: ['Keep your back straight', 'Breathe steadily'],
    variations: ['Goblet Squat', 'Bulgarian Split Squat'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // Setup default mock implementation
    (apiService.exercises.get as jest.Mock).mockResolvedValue({ 
      data: mockExercise, 
      status: 200
    });
    
    (apiService.exercises.getAll as jest.Mock).mockResolvedValue({
      data: [mockExercise],
      status: 200
    });
    
    // Reset the service's cache before each test
    // @ts-ignore - accessing private property for testing
    exerciseLibraryService.exercises = new Map();
  });

  describe('getExercises', () => {
    it('should fetch exercises and update cache', async () => {
      const mockResponse = { data: [mockExercise], status: 200 };
      (apiService.exercises.getAll as jest.Mock).mockResolvedValue(mockResponse);

      const result = await exerciseLibraryService.getExercises();

      expect(apiService.exercises.getAll).toHaveBeenCalledTimes(1);
      expect(result).toEqual([mockExercise]);
    });

    it('should handle errors when fetching exercises', async () => {
      const error = new Error('Failed to fetch exercises');
      (apiService.exercises.getAll as jest.Mock).mockRejectedValue(error);

      await expect(exerciseLibraryService.getExercises()).rejects.toThrow('Failed to fetch exercises');
    });
  });

  describe('getExercise', () => {
    it('should fetch from API and return exercise', async () => {
      const result = await exerciseLibraryService.getExercise('1');
      expect(apiService.exercises.get).toHaveBeenCalledTimes(1);
      expect(apiService.exercises.get).toHaveBeenCalledWith('1');
      expect(result).toEqual(mockExercise);
    });

    it('should fetch from API if not in cache', async () => {
      const result = await exerciseLibraryService.getExercise('1');
      expect(apiService.exercises.get).toHaveBeenCalledWith('1');
      expect(result).toEqual(mockExercise);
    });

    it('should handle errors when fetching exercise', async () => {
      (apiService.exercises.get as jest.Mock).mockRejectedValueOnce(new Error('API error'));
      
      await expect(exerciseLibraryService.getExercise('1')).resolves.toBeNull();
    });
  });

  describe('getFormRules', () => {
    it('should return form rules for an exercise', async () => {
      const rules = await exerciseLibraryService.getFormRules('1');
      expect(apiService.exercises.get).toHaveBeenCalledWith('1');
      expect(rules).toEqual(mockExercise.formRules);
    });

    it('should throw error if exercise not found', async () => {
      (apiService.exercises.get as jest.Mock).mockRejectedValueOnce(new Error('Exercise not found'));
      
      await expect(exerciseLibraryService.getFormRules('1')).rejects.toThrow();
    });
  });

  describe('searchExercises', () => {
    it('should search exercises by query', async () => {
      const mockSearchResults = [mockExercise];
      (apiService.exercises.search as jest.Mock).mockResolvedValueOnce({ 
        data: mockSearchResults, 
        status: 200 
      });
      
      const results = await exerciseLibraryService.searchExercises('squat');
      expect(apiService.exercises.search).toHaveBeenCalledWith('squat');
      expect(results).toEqual(mockSearchResults);
    });
  });

  describe('filterExercises', () => {
    it('should filter exercises by criteria', async () => {
      const mockFilterResults = [mockExercise];
      const filterCriteria = { 
        type: ExerciseType.STRENGTH, 
        difficulty: 'beginner' as const, 
        equipment: ['Dumbbell'], 
        targetMuscles: ['Quadriceps'] 
      };
      
      (apiService.exercises.filter as jest.Mock).mockResolvedValueOnce({ 
        data: mockFilterResults, 
        status: 200 
      });
      
      const results = await exerciseLibraryService.filterExercises(filterCriteria);
      expect(apiService.exercises.filter).toHaveBeenCalledWith(filterCriteria);
      expect(results).toEqual(mockFilterResults);
    });
  });

  describe('validateForm', () => {
    const mockAngles = {
      knee: 75, // Significantly off from optimal 90 (>10 degrees)
      hip: 65   // Significantly off from optimal 80 (>10 degrees)
    };

    it('should provide feedback for suboptimal angles', () => {
      // Directly access and modify the private cache for testing
      // @ts-ignore - accessing private property for testing
      exerciseLibraryService.exercises.set('1', {
        ...mockExercise,
        formRules: [{
          ...mockFormRule,
          jointAngles: {
            knee: { min: 70, max: 100, optimal: 90 },
            hip: { min: 60, max: 90, optimal: 80 }
          }
        }]
      });
      
      const result = exerciseLibraryService.validateForm('1', mockAngles);
      
      expect(result.isValid).toBe(true);
      expect(result.feedback.length).toBeGreaterThan(0);
      expect(result.feedback).toContain('Try to keep knee angle closer to 90°');
      expect(result.feedback).toContain('Try to keep hip angle closer to 80°');
    });
    
    it('should return invalid when exercise not found', () => {
      const result = exerciseLibraryService.validateForm('999', mockAngles);
      
      expect(result.isValid).toBe(false);
      expect(result.feedback).toEqual(['Exercise not found']);
    });
  });

  describe('getExerciseTypes', () => {
    it('should return all exercise types', () => {
      const types = exerciseLibraryService.getExerciseTypes();

      expect(types).toEqual([
        ExerciseType.STRENGTH,
        ExerciseType.CARDIO,
        ExerciseType.FLEXIBILITY,
        ExerciseType.BALANCE
      ]);
    });
  });
}); 