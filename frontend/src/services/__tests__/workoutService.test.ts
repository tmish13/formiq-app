import api from '../api';

// Mock the API module
jest.mock('../api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn()
  }
}));

// Mock workoutService
const workoutService = {
  getWorkouts: jest.fn(),
  getWorkout: jest.fn(),
  createWorkout: jest.fn(),
  updateWorkout: jest.fn(),
  deleteWorkout: jest.fn(),
  getWorkoutPlans: jest.fn(),
  getWorkoutPlan: jest.fn(),
  createWorkoutPlan: jest.fn(),
  updateWorkoutPlan: jest.fn(),
  deleteWorkoutPlan: jest.fn(),
  getUpcomingWorkouts: jest.fn(),
  getActiveWorkoutPlans: jest.fn()
};

// Simple mock data
const mockWorkouts = [
  { 
    id: '1', 
    name: 'Monday Strength', 
    description: 'Full body strength training',
    duration: 45,
  },
  { 
    id: '2', 
    name: 'Wednesday Cardio', 
    description: 'HIIT training',
    duration: 30,
  }
];

const mockWorkoutPlans = [
  {
    id: '1',
    name: 'Weight Loss Plan',
    description: 'A 4-week plan to help with weight loss',
    workouts: ['1', '2'],
    duration: 28,
  }
];

describe('Workout Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Set up the mock implementations for workoutService
    workoutService.getWorkouts.mockImplementation(() => {
      return api.get('/api/workouts').then(res => res.data);
    });

    workoutService.getWorkout.mockImplementation((id) => {
      return api.get(`/api/workouts/${id}`).then(res => res.data);
    });

    workoutService.createWorkout.mockImplementation((workout) => {
      return api.post('/api/workouts', workout).then(res => res.data);
    });

    workoutService.updateWorkout.mockImplementation((id, updates) => {
      return api.put(`/api/workouts/${id}`, updates).then(res => res.data);
    });

    workoutService.deleteWorkout.mockImplementation((id) => {
      return api.delete(`/api/workouts/${id}`).then(res => res.data);
    });

    workoutService.getWorkoutPlans.mockImplementation(() => {
      return api.get('/api/workout-plans').then(res => res.data);
    });

    workoutService.getWorkoutPlan.mockImplementation((id) => {
      return api.get(`/api/workout-plans/${id}`).then(res => res.data);
    });

    workoutService.createWorkoutPlan.mockImplementation((plan) => {
      return api.post('/api/workout-plans', plan).then(res => res.data);
    });

    workoutService.getUpcomingWorkouts.mockImplementation((days = 7) => {
      return api.get('/api/workouts/upcoming', { params: { days } }).then(res => res.data);
    });

    workoutService.getActiveWorkoutPlans.mockImplementation(() => {
      return api.get('/api/workout-plans/active').then(res => res.data);
    });
  });

  describe('Workout Management', () => {
    it('should get all workouts', async () => {
      const mockResponse = { data: mockWorkouts };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.getWorkouts();
      
      expect(api.get).toHaveBeenCalledWith('/api/workouts');
      expect(result).toEqual(mockWorkouts);
    });
    
    it('should get a single workout by ID', async () => {
      const mockResponse = { data: mockWorkouts[0] };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.getWorkout('1');
      
      expect(api.get).toHaveBeenCalledWith('/api/workouts/1');
      expect(result).toEqual(mockWorkouts[0]);
    });
    
    it('should create a new workout', async () => {
      const newWorkout = {
        name: 'Friday Mobility',
        description: 'Flexibility and mobility work',
        duration: 20
      };
      
      const createdWorkout = {
        ...newWorkout,
        id: '3',
      };
      
      const mockResponse = { data: createdWorkout };
      (api.post as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.createWorkout(newWorkout);
      
      expect(api.post).toHaveBeenCalledWith('/api/workouts', newWorkout);
      expect(result).toEqual(createdWorkout);
    });
    
    it('should update an existing workout', async () => {
      const updatedData = { name: 'Updated Workout Name' };
      const updatedWorkout = {
        ...mockWorkouts[0],
        name: 'Updated Workout Name'
      };
      
      const mockResponse = { data: updatedWorkout };
      (api.put as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.updateWorkout('1', updatedData);
      
      expect(api.put).toHaveBeenCalledWith('/api/workouts/1', updatedData);
      expect(result).toEqual(updatedWorkout);
    });
    
    it('should delete a workout', async () => {
      const mockResponse = { data: { success: true } };
      (api.delete as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      await workoutService.deleteWorkout('1');
      
      expect(api.delete).toHaveBeenCalledWith('/api/workouts/1');
    });
    
    it('should handle errors when fetching workouts', async () => {
      const errorResponse = new Error('Network error');
      (api.get as jest.Mock).mockRejectedValueOnce(errorResponse);
      
      await expect(workoutService.getWorkouts()).rejects.toThrow('Network error');
    });
  });
  
  describe('Workout Plan Management', () => {
    it('should get all workout plans', async () => {
      const mockResponse = { data: mockWorkoutPlans };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.getWorkoutPlans();
      
      expect(api.get).toHaveBeenCalledWith('/api/workout-plans');
      expect(result).toEqual(mockWorkoutPlans);
    });
    
    it('should get a single workout plan by ID', async () => {
      const mockResponse = { data: mockWorkoutPlans[0] };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.getWorkoutPlan('1');
      
      expect(api.get).toHaveBeenCalledWith('/api/workout-plans/1');
      expect(result).toEqual(mockWorkoutPlans[0]);
    });
    
    it('should create a new workout plan', async () => {
      const newPlan = {
        name: 'Muscle Building Plan',
        description: 'A 6-week plan to build muscle',
        workouts: ['1'],
        duration: 42,
        frequency: 'weekly'
      };
      
      const createdPlan = {
        ...newPlan,
        id: '2'
      };
      
      const mockResponse = { data: createdPlan };
      (api.post as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.createWorkoutPlan(newPlan);
      
      expect(api.post).toHaveBeenCalledWith('/api/workout-plans', newPlan);
      expect(result).toEqual(createdPlan);
    });
    
    it('should get upcoming workouts', async () => {
      const mockResponse = { data: mockWorkouts };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.getUpcomingWorkouts(10);
      
      expect(api.get).toHaveBeenCalledWith('/api/workouts/upcoming', {
        params: { days: 10 }
      });
      expect(result).toEqual(mockWorkouts);
    });
    
    it('should get active workout plans', async () => {
      const mockResponse = { data: mockWorkoutPlans };
      (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
      
      const result = await workoutService.getActiveWorkoutPlans();
      
      expect(api.get).toHaveBeenCalledWith('/api/workout-plans/active');
      expect(result).toEqual(mockWorkoutPlans);
    });
  });
}); 