import { workoutService } from '../workoutService';
import { mockWorkout, mockWorkoutPlan } from '../../services/api/handlers';
import { Workout, WorkoutPlan } from '../../types/workout';

// Mock the api module
jest.mock('../api', () => {
  return {
    __esModule: true,
    default: {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn()
    }
  };
});

// Import the mocked API
import api from '../api';

describe('WorkoutService', () => {
  // Clear mocks between tests
  beforeEach(() => {
    jest.clearAllMocks();
  });

  // Mock successful responses
  describe('successful operations', () => {
    beforeEach(() => {
      // Default successful responses
      (api.get as jest.Mock).mockImplementation((url) => {
        if (url.includes('workouts/upcoming')) {
          return Promise.resolve({ data: [mockWorkout] });
        } else if (url.includes('workout-plans/active')) {
          return Promise.resolve({ data: [mockWorkoutPlan] });
        } else if (url.includes('workouts/') && !url.includes('workouts/upcoming')) {
          return Promise.resolve({ data: mockWorkout });
        } else if (url.includes('workout-plans/')) {
          return Promise.resolve({ data: mockWorkoutPlan });
        } else if (url.includes('workouts')) {
          return Promise.resolve({ data: [mockWorkout] });
        } else if (url.includes('workout-plans')) {
          return Promise.resolve({ data: [mockWorkoutPlan] });
        }
        return Promise.resolve({ data: {} });
      });

      (api.post as jest.Mock).mockImplementation((url, data) => {
        if (url.includes('workouts')) {
          return Promise.resolve({
            data: {
              ...data,
              id: '123',
              userId: 'user123',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString()
            }
          });
        } else if (url.includes('workout-plans')) {
          return Promise.resolve({
            data: {
              ...data,
              id: '456',
              userId: 'user123',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString()
            }
          });
        }
        return Promise.resolve({ data: {} });
      });

      (api.put as jest.Mock).mockImplementation((url, data) => {
        if (url.includes('workouts/')) {
          return Promise.resolve({
            data: {
              ...mockWorkout,
              ...data
            }
          });
        } else if (url.includes('workout-plans/')) {
          return Promise.resolve({
            data: {
              ...mockWorkoutPlan,
              ...data
            }
          });
        }
        return Promise.resolve({ data: {} });
      });

      (api.delete as jest.Mock).mockResolvedValue({ data: { success: true } });
    });

    it('should fetch all workouts', async () => {
      const workouts = await workoutService.getWorkouts();
      
      expect(api.get).toHaveBeenCalledWith('/api/workouts');
      expect(Array.isArray(workouts)).toBe(true);
      expect(workouts).toEqual([mockWorkout]);
    });

    it('should fetch a single workout', async () => {
      const workout = await workoutService.getWorkout('123');
      
      expect(api.get).toHaveBeenCalledWith('/api/workouts/123');
      expect(workout).toBeDefined();
      expect(workout.id).toBe('123');
    });

    it('should create a new workout', async () => {
      const newWorkout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'> = {
        name: 'Evening Workout',
        exercises: [{
          id: 'ex2',
          name: 'Push-ups',
          sets: 3,
          reps: 15
        }],
        duration: 30,
        difficulty: 'beginner'
      };

      const created = await workoutService.createWorkout(newWorkout);
      
      expect(api.post).toHaveBeenCalledWith('/api/workouts', newWorkout);
      expect(created).toBeDefined();
      expect(created.name).toBe(newWorkout.name);
      expect(created.id).toBe('123');
    });

    it('should update a workout', async () => {
      const update: Partial<Workout> = {
        name: 'Updated Workout'
      };

      const updated = await workoutService.updateWorkout('123', update);
      
      expect(api.put).toHaveBeenCalledWith('/api/workouts/123', update);
      expect(updated).toBeDefined();
      expect(updated.name).toBe(update.name);
    });

    it('should delete a workout', async () => {
      await workoutService.deleteWorkout('123');
      
      expect(api.delete).toHaveBeenCalledWith('/api/workouts/123');
    });

    it('should fetch all workout plans', async () => {
      const plans = await workoutService.getWorkoutPlans();
      
      expect(api.get).toHaveBeenCalledWith('/api/workout-plans');
      expect(Array.isArray(plans)).toBe(true);
      expect(plans).toEqual([mockWorkoutPlan]);
    });

    it('should fetch a single workout plan', async () => {
      const plan = await workoutService.getWorkoutPlan('456');
      
      expect(api.get).toHaveBeenCalledWith('/api/workout-plans/456');
      expect(plan).toBeDefined();
      expect(plan.id).toBe('456');
    });

    it('should create a new workout plan', async () => {
      // Cast mockWorkout to ensure type compatibility
      const typedMockWorkout = mockWorkout as Workout;
      
      const newPlan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'> = {
        name: '8 Week Program',
        workouts: [typedMockWorkout],
        frequency: '4x per week',
        duration: 8
      };

      const created = await workoutService.createWorkoutPlan(newPlan);
      
      expect(api.post).toHaveBeenCalledWith('/api/workout-plans', newPlan);
      expect(created).toBeDefined();
      expect(created.name).toBe(newPlan.name);
      expect(created.id).toBe('456');
    });

    it('should update a workout plan', async () => {
      const update: Partial<WorkoutPlan> = {
        name: 'Updated Plan'
      };

      const updated = await workoutService.updateWorkoutPlan('456', update);
      
      expect(api.put).toHaveBeenCalledWith('/api/workout-plans/456', update);
      expect(updated).toBeDefined();
      expect(updated.name).toBe(update.name);
    });

    it('should delete a workout plan', async () => {
      await workoutService.deleteWorkoutPlan('456');
      
      expect(api.delete).toHaveBeenCalledWith('/api/workout-plans/456');
    });

    it('should fetch upcoming workouts', async () => {
      const workouts = await workoutService.getUpcomingWorkouts(7);
      
      expect(api.get).toHaveBeenCalledWith('/api/workouts/upcoming', {
        params: { days: 7 }
      });
      expect(Array.isArray(workouts)).toBe(true);
      expect(workouts).toEqual([mockWorkout]);
    });

    it('should fetch active workout plans', async () => {
      const plans = await workoutService.getActiveWorkoutPlans();
      
      expect(api.get).toHaveBeenCalledWith('/api/workout-plans/active');
      expect(Array.isArray(plans)).toBe(true);
      expect(plans).toEqual([mockWorkoutPlan]);
    });
  });

  // Test error handling
  describe('error handling', () => {
    beforeEach(() => {
      // Mock failed responses for error tests
      (api.get as jest.Mock).mockRejectedValue(new Error('Network error'));
      (api.post as jest.Mock).mockRejectedValue(new Error('Network error'));
      (api.put as jest.Mock).mockRejectedValue(new Error('Network error'));
      (api.delete as jest.Mock).mockRejectedValue(new Error('Network error'));
    });

    it('should handle errors when fetching workouts', async () => {
      await expect(workoutService.getWorkouts()).rejects.toThrow('Network error');
    });

    it('should handle errors when fetching a single workout', async () => {
      await expect(workoutService.getWorkout('123')).rejects.toThrow('Network error');
    });

    it('should handle errors when creating a workout', async () => {
      const newWorkout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'> = {
        name: 'Test Workout',
        exercises: [],
        duration: 30,
        difficulty: 'beginner'
      };
      
      await expect(workoutService.createWorkout(newWorkout)).rejects.toThrow('Network error');
    });

    it('should handle errors when updating a workout', async () => {
      await expect(workoutService.updateWorkout('123', { name: 'Updated' })).rejects.toThrow('Network error');
    });

    it('should handle errors when deleting a workout', async () => {
      await expect(workoutService.deleteWorkout('123')).rejects.toThrow('Network error');
    });
  });
}); 