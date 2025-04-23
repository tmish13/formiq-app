import { rest } from 'msw';
import { Exercise, Workout, WorkoutPlan } from '../../src/types/workout';

const baseUrl = process.env.REACT_APP_API_URL || '/api';

// Sample mock exercise
const mockExercise: Exercise = {
  id: 'ex1',
  name: 'Squat',
  sets: 3,
  reps: 12,
  weight: 100
};

// Sample mock workout
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

// Sample mock workout plan
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

// Mock DB for workouts
let workouts: Workout[] = [mockWorkout];
let workoutPlans: WorkoutPlan[] = [mockWorkoutPlan];

export const workoutHandlers = [
  // Get all workouts
  rest.get(`${baseUrl}/workouts`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json(workouts)
    );
  }),

  // Get a specific workout
  rest.get(`${baseUrl}/workouts/:id`, (req, res, ctx) => {
    const { id } = req.params;
    const workout = workouts.find(w => w.id === id);
    
    if (!workout) {
      return res(
        ctx.status(404),
        ctx.json({ message: 'Workout not found' })
      );
    }
    
    return res(
      ctx.status(200),
      ctx.json(workout)
    );
  }),

  // Create a new workout
  rest.post(`${baseUrl}/workouts`, async (req, res, ctx) => {
    const workoutData = await req.json() as Omit<Workout, 'id' | 'userId' | 'createdAt' | 'updatedAt'>;
    
    const newWorkout: Workout = {
      ...workoutData,
      id: Math.random().toString(36).substring(2, 9),
      userId: 'user123',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    workouts.push(newWorkout);
    return res(
      ctx.status(201),
      ctx.json(newWorkout)
    );
  }),

  // Update a workout
  rest.put(`${baseUrl}/workouts/:id`, async (req, res, ctx) => {
    const { id } = req.params;
    const updates = await req.json() as Partial<Workout>;
    
    const workoutIndex = workouts.findIndex(w => w.id === id);
    
    if (workoutIndex === -1) {
      return res(
        ctx.status(404),
        ctx.json({ message: 'Workout not found' })
      );
    }
    
    const updatedWorkout: Workout = {
      ...workouts[workoutIndex],
      ...updates,
      updatedAt: new Date().toISOString()
    };
    
    workouts[workoutIndex] = updatedWorkout;
    return res(
      ctx.status(200),
      ctx.json(updatedWorkout)
    );
  }),

  // Delete a workout
  rest.delete(`${baseUrl}/workouts/:id`, (req, res, ctx) => {
    const { id } = req.params;
    const workoutIndex = workouts.findIndex(w => w.id === id);
    
    if (workoutIndex === -1) {
      return res(
        ctx.status(404),
        ctx.json({ message: 'Workout not found' })
      );
    }
    
    workouts = workouts.filter(w => w.id !== id);
    return res(
      ctx.status(200),
      ctx.json({ success: true })
    );
  }),

  // Get all workout plans
  rest.get(`${baseUrl}/workout-plans`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json(workoutPlans)
    );
  }),

  // Get a specific workout plan
  rest.get(`${baseUrl}/workout-plans/:id`, (req, res, ctx) => {
    const { id } = req.params;
    const plan = workoutPlans.find(p => p.id === id);
    
    if (!plan) {
      return res(
        ctx.status(404),
        ctx.json({ message: 'Workout plan not found' })
      );
    }
    
    return res(
      ctx.status(200),
      ctx.json(plan)
    );
  }),

  // Create a new workout plan
  rest.post(`${baseUrl}/workout-plans`, async (req, res, ctx) => {
    const planData = await req.json() as Omit<WorkoutPlan, 'id' | 'userId' | 'createdAt' | 'updatedAt'>;
    
    const newPlan: WorkoutPlan = {
      ...planData,
      id: Math.random().toString(36).substring(2, 9),
      userId: 'user123',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };
    
    workoutPlans.push(newPlan);
    return res(
      ctx.status(201),
      ctx.json(newPlan)
    );
  }),

  // Update a workout plan
  rest.put(`${baseUrl}/workout-plans/:id`, async (req, res, ctx) => {
    const { id } = req.params;
    const updates = await req.json() as Partial<WorkoutPlan>;
    
    const planIndex = workoutPlans.findIndex(p => p.id === id);
    
    if (planIndex === -1) {
      return res(
        ctx.status(404),
        ctx.json({ message: 'Workout plan not found' })
      );
    }
    
    const updatedPlan: WorkoutPlan = {
      ...workoutPlans[planIndex],
      ...updates,
      updatedAt: new Date().toISOString()
    };
    
    workoutPlans[planIndex] = updatedPlan;
    return res(
      ctx.status(200),
      ctx.json(updatedPlan)
    );
  }),

  // Delete a workout plan
  rest.delete(`${baseUrl}/workout-plans/:id`, (req, res, ctx) => {
    const { id } = req.params;
    const planIndex = workoutPlans.findIndex(p => p.id === id);
    
    if (planIndex === -1) {
      return res(
        ctx.status(404),
        ctx.json({ message: 'Workout plan not found' })
      );
    }
    
    workoutPlans = workoutPlans.filter(p => p.id !== id);
    return res(
      ctx.status(200),
      ctx.json({ success: true })
    );
  }),

  // Get upcoming workouts
  rest.get(`${baseUrl}/workouts/upcoming`, (req, res, ctx) => {
    const days = parseInt(req.url.searchParams.get('days') || '7');
    
    // Simulate upcoming workouts
    const upcomingWorkouts = workouts.slice(0, Math.min(days, workouts.length));
    return res(
      ctx.status(200),
      ctx.json(upcomingWorkouts)
    );
  }),

  // Get active workout plans
  rest.get(`${baseUrl}/workout-plans/active`, (req, res, ctx) => {
    // Simulate active plans
    const activePlans = workoutPlans.slice(0, Math.min(2, workoutPlans.length));
    return res(
      ctx.status(200),
      ctx.json(activePlans)
    );
  })
]; 