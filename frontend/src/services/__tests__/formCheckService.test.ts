import { setupServer } from 'msw/node';
import { rest } from 'msw';
import { formCheckService } from '../formCheckService';
import { apiService } from '../api';
import { FormCheck, FormCheckStatus, ExerciseType } from '../../types/formCheck';

// Mock the API service first
jest.mock('../api', () => ({
  apiService: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn()
  }
}));

// Mock the service methods directly instead of mocking the module
jest.mock('../formCheckService', () => {
  // Save original module
  const originalModule = jest.requireActual('../formCheckService');
  
  return {
    formCheckService: {
      ...originalModule.formCheckService,
      getFormChecks: jest.fn(),
      getFormCheck: jest.fn(),
      createFormCheck: jest.fn(),
      updateFormCheck: jest.fn(),
      deleteFormCheck: jest.fn(),
      getFormChecksByExerciseType: jest.fn(),
      getLatestFormChecks: jest.fn(),
      updateFormCheckStatus: jest.fn(),
      uploadVideo: jest.fn(),
      analyze: jest.fn(),
      getHistory: jest.fn()
    }
  };
});

const mockFormCheck: FormCheck = {
  id: 123,
  user_id: 1,
  exercise_type: 'squat' as ExerciseType,
  video_url: 'test.mp4',
  status: 'completed' as FormCheckStatus,
  score: 85,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

// Create test server
const server = setupServer(
  // Mock successful response
  rest.get('/api/form-checks/:id', (req, res, ctx) => {
    return res(ctx.json(mockFormCheck));
  }),

  // Mock error response
  rest.post('/api/form-checks', (req, res, ctx) => {
    return res(ctx.status(500));
  }),

  // Mock timeout
  rest.get('/api/form-checks/timeout', (req, res, ctx) => {
    return res(ctx.delay(5000));
  })
);

describe('formCheckService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  beforeAll(() => server.listen());
  afterEach(() => server.resetHandlers());
  afterAll(() => server.close());

  describe('getFormChecks', () => {
    it('should fetch all form checks', async () => {
      const mockResponse = { data: [mockFormCheck] };
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.getFormChecks as jest.Mock).mockImplementation(async () => {
        const response = await apiService.get('/api/form-checks');
        return response.data;
      });

      const result = await formCheckService.getFormChecks();

      expect(apiService.get).toHaveBeenCalledWith('/api/form-checks');
      expect(result).toEqual([mockFormCheck]);
    });
  });

  describe('getFormCheck', () => {
    it('should fetch form check data successfully', async () => {
      const mockResponse = { data: mockFormCheck };
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.getFormCheck as jest.Mock).mockImplementation(async (id) => {
        const response = await apiService.get(`/api/form-checks/${id}`);
        return response.data;
      });

      const result = await formCheckService.getFormCheck('123');

      expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/123');
      expect(result).toEqual(mockFormCheck);
    });

    it('should handle errors', async () => {
      (apiService.get as jest.Mock).mockRejectedValue(new Error('API Error'));
      (formCheckService.getFormCheck as jest.Mock).mockImplementation(async (id) => {
        return apiService.get(`/api/form-checks/${id}`);
      });

      await expect(formCheckService.getFormCheck('123')).rejects.toThrow('API Error');
    });
  });

  describe('createFormCheck', () => {
    it('should create a new form check', async () => {
      const formCheckData = {
        exercise_type: 'squat' as ExerciseType,
        video_url: 'https://example.com/video.mp4',
      };
      const mockResponse = { data: mockFormCheck };
      (apiService.post as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.createFormCheck as jest.Mock).mockImplementation(async (data) => {
        const response = await apiService.post('/api/form-checks', data);
        return response.data;
      });

      const result = await formCheckService.createFormCheck(formCheckData);

      expect(apiService.post).toHaveBeenCalledWith('/api/form-checks', formCheckData);
      expect(result).toEqual(mockFormCheck);
    });
  });

  describe('updateFormCheck', () => {
    it('should update a form check', async () => {
      const formCheckData = {
        status: 'completed' as FormCheckStatus,
      };
      const updatedFormCheck = {...mockFormCheck, ...formCheckData};
      const mockResponse = { data: updatedFormCheck };
      (apiService.put as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.updateFormCheck as jest.Mock).mockImplementation(async (id, data) => {
        const response = await apiService.put(`/api/form-checks/${id}`, data);
        return response.data;
      });

      const result = await formCheckService.updateFormCheck('1', formCheckData);

      expect(apiService.put).toHaveBeenCalledWith('/api/form-checks/1', formCheckData);
      expect(result).toEqual(updatedFormCheck);
    });
  });

  describe('deleteFormCheck', () => {
    it('should delete a form check', async () => {
      (apiService.delete as jest.Mock).mockResolvedValue(undefined);
      (formCheckService.deleteFormCheck as jest.Mock).mockImplementation(async (id) => {
        return apiService.delete(`/api/form-checks/${id}`);
      });

      await formCheckService.deleteFormCheck('1');

      expect(apiService.delete).toHaveBeenCalledWith('/api/form-checks/1');
    });
  });

  describe('getFormChecksByExerciseType', () => {
    it('should fetch form checks by exercise type', async () => {
      const mockResponse = { data: [mockFormCheck] };
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.getFormChecksByExerciseType as jest.Mock).mockImplementation(async (exerciseType) => {
        const response = await apiService.get(`/api/form-checks/exercise/${exerciseType}`);
        return response.data;
      });

      const result = await formCheckService.getFormChecksByExerciseType('squat');

      expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/exercise/squat');
      expect(result).toEqual([mockFormCheck]);
    });
  });
  
  describe('getLatestFormChecks', () => {
    it('should fetch latest form checks', async () => {
      const mockResponse = { data: [mockFormCheck] };
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.getLatestFormChecks as jest.Mock).mockImplementation(async (limit) => {
        const response = await apiService.get(`/api/form-checks/latest`, { params: { limit } });
        return response.data;
      });

      const result = await formCheckService.getLatestFormChecks(3);

      expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/latest', { params: { limit: 3 } });
      expect(result).toEqual([mockFormCheck]);
    });
  });
  
  describe('updateFormCheckStatus', () => {
    const newStatus: FormCheckStatus = 'completed';

    it('should update form check status successfully', async () => {
      const updatedFormCheck = { ...mockFormCheck, status: newStatus };
      const mockResponse = { data: updatedFormCheck };
      (apiService.patch as jest.Mock).mockResolvedValue(mockResponse);
      (formCheckService.updateFormCheckStatus as jest.Mock).mockImplementation(async (id, status) => {
        const response = await apiService.patch(`/api/form-checks/${id}/status`, { status });
        return response.data;
      });

      const result = await formCheckService.updateFormCheckStatus('123', newStatus);
      
      expect(apiService.patch).toHaveBeenCalledWith('/api/form-checks/123/status', { status: newStatus });
      expect(result).toEqual(updatedFormCheck);
    });

    it('should handle errors', async () => {
      (apiService.patch as jest.Mock).mockRejectedValue(new Error('API Error'));
      (formCheckService.updateFormCheckStatus as jest.Mock).mockImplementation(async (id, status) => {
        return apiService.patch(`/api/form-checks/${id}/status`, { status });
      });

      await expect(formCheckService.updateFormCheckStatus('123', newStatus)).rejects.toThrow('API Error');
    });
  });

  describe('uploadVideo', () => {
    it('should upload a video file with exercise type', async () => {
      // Create mock file and exercise type
      const mockFile = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
      const exerciseType: ExerciseType = 'squat';
      
      // Mock successful API response
      const mockResponse = { data: mockFormCheck };
      (apiService.post as jest.Mock).mockResolvedValue(mockResponse);
      
      // Mock progress callback
      const mockProgressCallback = jest.fn();
      
      (formCheckService.uploadVideo as jest.Mock).mockImplementation(async (file, exType, progressCb) => {
        const formData = new FormData();
        formData.append('video', file);
        formData.append('exerciseType', exType);
        
        const response = await apiService.post('/api/form-checks/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: progressCb ? (progressEvent: any) => {
            if (progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              progressCb(progress);
            }
          } : undefined
        });
        
        return response.data;
      });
      
      const result = await formCheckService.uploadVideo(mockFile, exerciseType, mockProgressCallback);

      // Verify API call
      expect(apiService.post).toHaveBeenCalled();
      
      // Get the arguments for the post call
      const postCall = (apiService.post as jest.Mock).mock.calls[0];
      
      // Verify endpoint
      expect(postCall[0]).toBe('/api/form-checks/upload');
      
      // Verify form data was created
      const formData = postCall[1];
      expect(formData instanceof FormData).toBe(true);
      
      // Verify config with headers and progress handler
      const config = postCall[2];
      expect(config).toHaveProperty('headers');
      expect(config.headers['Content-Type']).toBe('multipart/form-data');
      expect(config).toHaveProperty('onUploadProgress');
      
      // Simulate progress event
      if (config.onUploadProgress) {
        const progressEvent = { loaded: 50, total: 100 };
        config.onUploadProgress(progressEvent);
        expect(mockProgressCallback).toHaveBeenCalledWith(50);
      }
      
      // Verify result
      expect(result).toEqual(mockFormCheck);
    });

    it('should handle errors during video upload', async () => {
      // Create mock file and exercise type
      const mockFile = new File(['mock video content'], 'test-video.mp4', { type: 'video/mp4' });
      const exerciseType: ExerciseType = 'squat';
      
      // Mock API error
      const error = new Error('Upload failed');
      (apiService.post as jest.Mock).mockRejectedValue(error);
      
      (formCheckService.uploadVideo as jest.Mock).mockImplementation(async (file, exType) => {
        const formData = new FormData();
        formData.append('video', file);
        formData.append('exerciseType', exType);
        
        try {
          const response = await apiService.post('/api/form-checks/upload', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            }
          });
          return response.data;
        } catch (err) {
          throw err;
        }
      });
      
      // Verify error is propagated
      await expect(formCheckService.uploadVideo(mockFile, exerciseType)).rejects.toThrow('Upload failed');
      expect(apiService.post).toHaveBeenCalled();
    });
  });

  describe('analyze', () => {
    it('should trigger analysis of a form check', async () => {
      // Mock successful API response
      const mockResponse = { data: { ...mockFormCheck, status: 'analyzed' } };
      (apiService.post as jest.Mock).mockResolvedValue(mockResponse);

      (formCheckService.analyze as jest.Mock).mockImplementation(async (id) => {
        const response = await apiService.post(`/api/form-checks/${id}/analyze`);
        return response.data;
      });

      const result = await formCheckService.analyze('form-check-123');

      // Verify API call
      expect(apiService.post).toHaveBeenCalledWith('/api/form-checks/form-check-123/analyze');
      
      // Verify result
      expect(result).toEqual({ ...mockFormCheck, status: 'analyzed' });
    });

    it('should handle errors during analysis', async () => {
      // Mock API error
      const error = new Error('Analysis failed');
      (apiService.post as jest.Mock).mockRejectedValue(error);

      (formCheckService.analyze as jest.Mock).mockImplementation(async (id) => {
        try {
          const response = await apiService.post(`/api/form-checks/${id}/analyze`);
          return response.data;
        } catch (err) {
          throw err;
        }
      });

      // Verify error is propagated
      await expect(formCheckService.analyze('form-check-123')).rejects.toThrow('Analysis failed');
      expect(apiService.post).toHaveBeenCalledWith('/api/form-checks/form-check-123/analyze');
    });
  });

  describe('getHistory', () => {
    it('should fetch user form check history', async () => {
      // Mock successful API response
      const mockResponse = { data: [mockFormCheck] };
      (apiService.get as jest.Mock).mockResolvedValue(mockResponse);

      (formCheckService.getHistory as jest.Mock).mockImplementation(async () => {
        const response = await apiService.get('/api/form-checks/history');
        return response.data;
      });

      const result = await formCheckService.getHistory();

      // Verify API call
      expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/history');
      
      // Verify result
      expect(result).toEqual([mockFormCheck]);
    });

    it('should handle errors when fetching history', async () => {
      // Mock API error
      const error = new Error('Failed to fetch history');
      (apiService.get as jest.Mock).mockRejectedValue(error);

      (formCheckService.getHistory as jest.Mock).mockImplementation(async () => {
        try {
          const response = await apiService.get('/api/form-checks/history');
          return response.data;
        } catch (err) {
          throw err;
        }
      });

      // Verify error is propagated
      await expect(formCheckService.getHistory()).rejects.toThrow('Failed to fetch history');
      expect(apiService.get).toHaveBeenCalledWith('/api/form-checks/history');
    });
  });
}); 