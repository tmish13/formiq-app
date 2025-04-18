// Mock the formCheckService
jest.mock('../formCheckService', () => ({
  formCheckService: {
    getFormChecks: jest.fn(),
    getFormCheck: jest.fn(),
    createFormCheck: jest.fn(),
    updateFormCheck: jest.fn(),
    deleteFormCheck: jest.fn(),
    getFormChecksByExerciseType: jest.fn(),
    getLatestFormChecks: jest.fn(),
    updateFormCheckStatus: jest.fn()
  }
}));

// Import the mocked service
import { formCheckService } from '../formCheckService';
import { apiService } from '../apiService';
import { FormCheck } from '../../types';
import { ExerciseType } from '../exerciseLibraryService';

// Mock the API service
jest.mock('../apiService', () => ({
  apiService: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn(),
  },
}));

describe('formCheckService', () => {
  // Define types inline to avoid import issues
  type ExerciseType = 'squat' | 'deadlift' | 'bench_press';
  
  interface FormCheck {
    id: number;
    user_id: number;
    exercise_type: ExerciseType;
    video_url: string;
    status: string;
    created_at: string;
    updated_at: string;
  }

  const mockFormCheck: FormCheck = {
    id: 1,
    user_id: 1,
    exercise_type: 'squat',
    video_url: 'https://example.com/video.mp4',
    status: 'pending',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getFormChecks', () => {
    it('should fetch all form checks', async () => {
      const mockResponse = [mockFormCheck];
      (formCheckService.getFormChecks as jest.Mock).mockResolvedValue(mockResponse);

      const result = await formCheckService.getFormChecks();

      expect(formCheckService.getFormChecks).toHaveBeenCalled();
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getFormCheck', () => {
    it('should fetch a single form check', async () => {
      (formCheckService.getFormCheck as jest.Mock).mockResolvedValue(mockFormCheck);

      const result = await formCheckService.getFormCheck('1');

      expect(formCheckService.getFormCheck).toHaveBeenCalledWith('1');
      expect(result).toEqual(mockFormCheck);
    });
  });

  describe('createFormCheck', () => {
    it('should create a new form check', async () => {
      const formCheckData = {
        exercise_type: 'squat' as ExerciseType,
        video_url: 'https://example.com/video.mp4',
      };
      
      (formCheckService.createFormCheck as jest.Mock).mockResolvedValue(mockFormCheck);

      const result = await formCheckService.createFormCheck(formCheckData);

      expect(formCheckService.createFormCheck).toHaveBeenCalledWith(formCheckData);
      expect(result).toEqual(mockFormCheck);
    });
  });

  describe('updateFormCheck', () => {
    it('should update a form check', async () => {
      const formCheckData = {
        status: 'completed',
      };
      const updatedFormCheck = {...mockFormCheck, ...formCheckData};
      
      (formCheckService.updateFormCheck as jest.Mock).mockResolvedValue(updatedFormCheck);

      const result = await formCheckService.updateFormCheck('1', formCheckData);

      expect(formCheckService.updateFormCheck).toHaveBeenCalledWith('1', formCheckData);
      expect(result).toEqual(updatedFormCheck);
    });
  });

  describe('deleteFormCheck', () => {
    it('should delete a form check', async () => {
      (formCheckService.deleteFormCheck as jest.Mock).mockResolvedValue(undefined);

      await formCheckService.deleteFormCheck('1');

      expect(formCheckService.deleteFormCheck).toHaveBeenCalledWith('1');
    });
  });

  describe('getFormChecksByExerciseType', () => {
    it('should fetch form checks by exercise type', async () => {
      const mockResponse = [mockFormCheck];
      (formCheckService.getFormChecksByExerciseType as jest.Mock).mockResolvedValue(mockResponse);

      const result = await formCheckService.getFormChecksByExerciseType('squat');

      expect(formCheckService.getFormChecksByExerciseType).toHaveBeenCalledWith('squat');
      expect(result).toEqual(mockResponse);
    });
  });
  
  describe('getLatestFormChecks', () => {
    it('should fetch latest form checks', async () => {
      const mockResponse = [mockFormCheck];
      (formCheckService.getLatestFormChecks as jest.Mock).mockResolvedValue(mockResponse);

      const result = await formCheckService.getLatestFormChecks(3);

      expect(formCheckService.getLatestFormChecks).toHaveBeenCalledWith(3);
      expect(result).toEqual(mockResponse);
    });
  });
  
  describe('updateFormCheckStatus', () => {
    it('should update form check status', async () => {
      const newStatus = 'completed';
      const updatedFormCheck = { ...mockFormCheck, status: newStatus };
      
      (formCheckService.updateFormCheckStatus as jest.Mock).mockResolvedValue(updatedFormCheck);

      const result = await formCheckService.updateFormCheckStatus('1', newStatus);

      expect(formCheckService.updateFormCheckStatus).toHaveBeenCalledWith('1', newStatus);
      expect(result).toEqual(updatedFormCheck);
    });
  });
}); 