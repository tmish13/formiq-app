import { formCheckService } from '../formCheckService';
import { apiService } from '../api';
import { FormCheck, ExerciseType } from '../../types';

// Mock the API service
jest.mock('../api', () => ({
  apiService: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

describe('formCheckService', () => {
  const mockFormCheck: FormCheck = {
    id: 1,
    user_id: 1,
    exercise_type: 'squat' as ExerciseType,
    video_url: 'https://example.com/video.mp4',
    status: 'pending',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getUserFormChecks', () => {
    it('should fetch user form checks', async () => {
      const mockResponse = [mockFormCheck];
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);

      const result = await formCheckService.getUserFormChecks();

      expect(apiService.get).toHaveBeenCalledWith('/form-checks');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getFormCheck', () => {
    it('should fetch a single form check', async () => {
      (apiService.get as jest.Mock).mockResolvedValue(mockFormCheck);

      const result = await formCheckService.getFormCheck(1);

      expect(apiService.get).toHaveBeenCalledWith('/form-checks/1');
      expect(result).toEqual(mockFormCheck);
    });
  });

  describe('submitFormCheck', () => {
    it('should submit a form check with video', async () => {
      const video = new File([''], 'test.mp4', { type: 'video/mp4' });
      (apiService.post as jest.Mock).mockResolvedValue(mockFormCheck);

      const result = await formCheckService.submitFormCheck(video, 'squat');

      expect(apiService.post).toHaveBeenCalledWith(
        '/form-checks',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      expect(result).toEqual(mockFormCheck);
    });

    it('should submit a form check with notes', async () => {
      const video = new File([''], 'test.mp4', { type: 'video/mp4' });
      const notes = 'Test notes';
      (apiService.post as jest.Mock).mockResolvedValue(mockFormCheck);

      const result = await formCheckService.submitFormCheck(video, 'squat', notes);

      expect(apiService.post).toHaveBeenCalledWith(
        '/form-checks',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      expect(result).toEqual(mockFormCheck);
    });
  });

  describe('deleteFormCheck', () => {
    it('should delete a form check', async () => {
      (apiService.delete as jest.Mock).mockResolvedValue(undefined);

      await formCheckService.deleteFormCheck(1);

      expect(apiService.delete).toHaveBeenCalledWith('/form-checks/1');
    });
  });

  describe('completeAnalysis', () => {
    it('should complete form check analysis', async () => {
      const updatedFormCheck = { ...mockFormCheck, status: 'completed', score: 85 };
      (apiService.post as jest.Mock).mockResolvedValue(updatedFormCheck);

      const result = await formCheckService.completeAnalysis(1, 'Good form overall', 85);

      expect(apiService.post).toHaveBeenCalledWith('/form-checks/1/complete', {
        summary: 'Good form overall',
        overall_score: 85,
      });
      expect(result).toEqual(updatedFormCheck);
    });
  });

  describe('getFormChecksByExercise', () => {
    it('should fetch form checks by exercise type', async () => {
      const mockResponse = [mockFormCheck];
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);

      const result = await formCheckService.getFormChecksByExercise('squat');

      expect(apiService.get).toHaveBeenCalledWith('/form-checks/exercise/squat');
      expect(result).toEqual(mockResponse);
    });
  });
}); 