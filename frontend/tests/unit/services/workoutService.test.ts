import { workoutService } from '../../../src/services/workoutService';
import { http, HttpResponse } from 'msw';
import { server } from '../../mocks/server';
import { Exercise, Workout, WorkoutPlan } from '../../../src/types/workout';

const mockExercise: Exercise = {
  id: 'ex1',
  name: 'Squat',
  sets: 3,
  reps: 12,
  weight: 100
};

const mockWorkout: Workout = {
  id: '123',
  name: 'Morning Workout',
  exercises: [mockExercise],
  duration: 45,
  difficulty: 'intermediate',
  userId: 'user123',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString()
};

const mockWorkoutPlan: WorkoutPlan = {
  id: '456',
  name: '12 Week Program',
  workouts: [mockWorkout],
  frequency: '3x per week',
  duration: 12,
  userId: 'user123',
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString()
};

describe('WorkoutService', () => {
  beforeEach(() => {
    server.resetHandlers();
    
    // Setup MSW handlers for the workout API endpoints
    server.use(
      http.get('/api/workouts', () => {
        return HttpResponse.json([mockWorkout]);
      }),
      
      http.get('/api/workouts/:id', ({ params }) => {
        return HttpResponse.json(mockWorkout);
      }),
      
      http.post('/api/workouts', async ({ request }) => {
        const data = await request.json();
        return HttpResponse.json({
          ...data,
          id: '123',
          userId: 'user123',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }, { status: 201 });
      }),
      
      http.put('/api/workouts/:id', async ({ params, request }) => {
        const data = await request.json();
        return HttpResponse.json({
          ...mockWorkout,
          ...data
        });
      }),
      
      http.delete('/api/workouts/:id', () => {
        return HttpResponse.json({ success: true });
      }),
      
      http.get('/api/workout-plans', () => {
        return HttpResponse.json([mockWorkoutPlan]);
      }),
      
      http.get('/api/workout-plans/:id', () => {
        return HttpResponse.json(mockWorkoutPlan);
      }),
      
      http.post('/api/workout-plans', async ({ request }) => {
        const data = await request.json();
        return HttpResponse.json({
          ...data,
          id: '456',
          userId: 'user123',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        }, { status: 201 });
      }),
      
      http.put('/api/workout-plans/:id', async ({ request }) => {
        const data = await request.json();
        return HttpResponse.json({
          ...mockWorkoutPlan,
          ...data
        });
      }),
      
      http.delete('/api/workout-plans/:id', () => {
        return HttpResponse.json({ success: true });
      }),
      
      http.get('/api/workouts/upcoming', () => {
        return HttpResponse.json([mockWorkout]);
      }),
      
      http.get('/api/workout-plans/active', () => {
        return HttpResponse.json([mockWorkoutPlan]);
      })
    );
  });

  describe('Workout operations', () => {
    it('should fetch all workouts', async () => {
      const workouts = await workoutService.getWorkouts();
      expect(Array.isArray(workouts)).toBe(true);
    });

    it('should fetch a single workout', async () => {
      const workout = await workoutService.getWorkout('123');
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
      expect(created).toBeDefined();
      expect(created.name).toBe(newWorkout.name);
    });

    it('should update a workout', async () => {
      const update: Partial<Workout> = {
        name: 'Updated Workout'
      };

      const updated = await workoutService.updateWorkout('123', update);
      expect(updated).toBeDefined();
      expect(updated.name).toBe(update.name);
    });

    it('should handle workout deletion', async () => {
      await expect(workoutService.deleteWorkout('123')).resolves.not.toThrow();
    });
  });

  describe('Workout Plan operations', () => {
    it('should fetch all workout plans', async () => {
      const plans = await workoutService.getWorkoutPlans();
      expect(Array.isArray(plans)).toBe(true);
    });

    it('should fetch a single workout plan', async () => {
      const plan = await workoutService.getWorkoutPlan('456');
      expect(plan).toBeDefined();
      expect(plan.id).toBe('456');
    });

    it('should create a new workout plan', async () => {
      const newPlan: Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'> = {
        name: '8 Week Program',
        workouts: [mockWorkout],
        frequency: '4x per week',
        duration: 8
      };

      const created = await workoutService.createWorkoutPlan(newPlan);
      expect(created).toBeDefined();
      expect(created.name).toBe(newPlan.name);
    });

    it('should update a workout plan', async () => {
      const update: Partial<WorkoutPlan> = {
        name: 'Updated Plan'
      };

      const updated = await workoutService.updateWorkoutPlan('456', update);
      expect(updated).toBeDefined();
      expect(updated.name).toBe(update.name);
    });

    it('should handle workout plan deletion', async () => {
      await expect(workoutService.deleteWorkoutPlan('456')).resolves.not.toThrow();
    });
  });

  describe('Additional operations', () => {
    it('should fetch upcoming workouts', async () => {
      const workouts = await workoutService.getUpcomingWorkouts(7);
      expect(Array.isArray(workouts)).toBe(true);
    });

    it('should fetch active workout plans', async () => {
      const plans = await workoutService.getActiveWorkoutPlans();
      expect(Array.isArray(plans)).toBe(true);
    });
  });

  describe('Error handling', () => {
    it('should handle API errors when fetching workouts', async () => {
      server.use(
        http.get('/api/workouts', () => {
          return new HttpResponse(null, { status: 500 });
        })
      );

      await expect(workoutService.getWorkouts()).rejects.toThrow();
    });

    it('should handle API errors when creating workouts', async () => {
      server.use(
        http.post('/api/workouts', () => {
          return new HttpResponse(null, { status: 500 });
        })
      );

      const newWorkout: Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'> = {
        name: 'Test Workout',
        exercises: [{
          id: 'ex3',
          name: 'Test Exercise',
          sets: 3,
          reps: 10
        }],
        duration: 30,
        difficulty: 'beginner'
      };

      await expect(workoutService.createWorkout(newWorkout)).rejects.toThrow();
    });
  });
}); 