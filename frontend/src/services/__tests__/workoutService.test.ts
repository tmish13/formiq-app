import { workoutService } from '../workoutService';
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

describe('Workout Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should get all workouts', async () => {
    const mockResponse = {
      data: [
        { id: '1', name: 'Workout 1' },
        { id: '2', name: 'Workout 2' }
      ]
    };
    
    (api.get as jest.Mock).mockResolvedValueOnce(mockResponse);
    
    const result = await workoutService.getWorkouts();
    
    expect(api.get).toHaveBeenCalledWith('/api/workouts');
    expect(result).toEqual(mockResponse.data);
  });
}); 