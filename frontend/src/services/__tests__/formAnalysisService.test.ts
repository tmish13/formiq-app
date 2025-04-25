import { FormAnalysisService } from '../../../src/services/formAnalysisService';
import { rest } from 'msw';
import { server } from '../../mocks/server';
import { 
  FormAnalysisRequest, 
  FormAnalysisResult,
  FormFeedback
} from '../../../src/types/formAnalysis';
import * as poseDetection from '@tensorflow-models/pose-detection';

// Mock pose detection
jest.mock('@tensorflow-models/pose-detection', () => ({
  SupportedModels: {
    MoveNet: 'movenet'
  },
  movenet: {
    modelType: {
      SINGLEPOSE_LIGHTNING: 'lightning'
    }
  },
  createDetector: jest.fn().mockResolvedValue({
    estimatePoses: jest.fn().mockResolvedValue([{
      keypoints: [
        { name: 'left_hip', x: 100, y: 100, score: 0.9 },
        { name: 'left_knee', x: 100, y: 200, score: 0.9 },
        { name: 'left_ankle', x: 100, y: 300, score: 0.9 }
      ],
      score: 0.9
    }])
  })
}));

// Mock fetch API
global.fetch = jest.fn();

describe('FormAnalysisService', () => {
  let service: FormAnalysisService;

  beforeEach(() => {
    service = new FormAnalysisService();
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  describe('initialization', () => {
    it('should initialize successfully', async () => {
      await service.initialize();
      expect(poseDetection.createDetector).toHaveBeenCalled();
    });

    it('should not initialize if already initialized', async () => {
      await service.initialize();
      await service.initialize();
      expect(poseDetection.createDetector).toHaveBeenCalledTimes(1);
    });

    it('should handle initialization errors gracefully', async () => {
      (poseDetection.createDetector as jest.Mock).mockRejectedValueOnce(new Error('Model not available'));
      
      try {
        await service.initialize();
        // Should complete without throwing
      } catch (error) {
        fail('Initialization should handle errors gracefully');
      }
      
      // Service should mark initialization as failed
      expect(service['initialized']).toBe(false);
    });
  });

  describe('analyzeForm', () => {
    it('should successfully analyze form with keypoints', async () => {
      const mockRequest: FormAnalysisRequest = {
        keypoints: [
          { name: 'left_hip', x: 100, y: 100, score: 0.9 },
          { name: 'left_knee', x: 100, y: 200, score: 0.9 },
          { name: 'left_ankle', x: 100, y: 300, score: 0.9 }
        ],
        video_url: 'https://example.com/video.mp4',
        exercise_id: '123'
      };

      await service.initialize();
      const result = await service.analyzeForm(mockRequest);

      expect(result.status).toBe('success');
      expect(result.result.isReliable).toBe(true);
      expect(result.result.keypoints).toEqual(mockRequest.keypoints);
      expect(result.result.angles).toHaveProperty('leftKnee');
      expect(result.result.feedback).toBeInstanceOf(Array);
    });

    it('should handle errors when no keypoints are provided', async () => {
      const mockRequest: FormAnalysisRequest = {
        video_url: 'https://example.com/video.mp4',
        exercise_id: '123'
      };

      await service.initialize();
      const result = await service.analyzeForm(mockRequest);

      expect(result.status).toBe('error');
      expect(result.result.isReliable).toBe(false);
      expect(result.result.keypoints).toEqual([]);
      expect(result.message).toBe('No keypoints or video URL provided');
    });

    it('should handle errors when no keypoints and no video URL are provided', async () => {
      const mockRequest: FormAnalysisRequest = {
        exercise_id: '123'
      };

      await service.initialize();
      const result = await service.analyzeForm(mockRequest);

      expect(result.status).toBe('error');
      expect(result.message).toBe('No keypoints or video URL provided');
    });

    it('should handle empty keypoints array', async () => {
      const mockRequest: FormAnalysisRequest = {
        keypoints: [],
        exercise_id: '123'
      };

      await service.initialize();
      const result = await service.analyzeForm(mockRequest);

      expect(result.status).toBe('error');
      expect(result.message).toBe('No valid keypoints provided');
      expect(result.result.isReliable).toBe(false);
    });

    it('should handle video processing with pose detection', async () => {
      const mockRequest: FormAnalysisRequest = {
        video_url: 'https://example.com/video.mp4',
        exercise_id: '123',
        shouldExtractPose: true
      };

      const estimatePosesMock = jest.fn().mockResolvedValue([{
        keypoints: [
          { name: 'left_hip', x: 100, y: 100, score: 0.9 },
          { name: 'left_knee', x: 100, y: 200, score: 0.9 },
          { name: 'left_ankle', x: 100, y: 300, score: 0.9 }
        ],
        score: 0.9
      }]);

      (poseDetection.createDetector as jest.Mock).mockResolvedValueOnce({
        estimatePoses: estimatePosesMock
      });

      // Mock HTMLVideoElement
      const mockVideo = {
        src: '',
        load: jest.fn(),
        play: jest.fn().mockResolvedValue(undefined),
        pause: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn()
      };

      document.createElement = jest.fn().mockImplementation((tag) => {
        if (tag === 'video') {
          return mockVideo as unknown as HTMLVideoElement;
        }
        return {} as any;
      });

      await service.initialize();
      
      // Simulate video loaded event
      mockVideo.addEventListener.mock.calls.forEach(call => {
        if (call[0] === 'loadeddata') {
          // Call the loadeddata event handler
          call[1]();
        }
      });

      const result = await service.analyzeForm(mockRequest);

      expect(mockVideo.src).toBe('https://example.com/video.mp4');
      expect(mockVideo.play).toHaveBeenCalled();
      expect(mockVideo.pause).toHaveBeenCalled();
      expect(estimatePosesMock).toHaveBeenCalled();
      expect(result.status).toBe('success');
    });
  });

  describe('getAnalysisHistory', () => {
    it('should fetch analysis history successfully', async () => {
      const mockHistory: FormAnalysisResult[] = [{
        confidence: 0.9,
        isReliable: true,
        keypoints: [],
        angles: {},
        feedback: [{
          type: 'success',
          message: 'Good form',
          confidence: 0.9,
          jointName: 'leftKnee'
        }],
        timestamp: Date.now()
      }];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ data: mockHistory })
      });

      const result = await service.getAnalysisHistory();
      expect(result).toEqual(mockHistory);
      expect(global.fetch).toHaveBeenCalledWith('/api/form-analysis/history', expect.anything());
    });

    it('should handle server errors when fetching history', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      await expect(service.getAnalysisHistory()).rejects.toThrow('Failed to fetch analysis history');
    });

    it('should handle network errors when fetching history', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(service.getAnalysisHistory()).rejects.toThrow('Network error');
    });

    it('should handle malformed response data', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ invalidData: 'not what we expected' })
      });

      await expect(service.getAnalysisHistory()).rejects.toThrow('Invalid server response');
    });
  });

  describe('saveAnalysis', () => {
    it('should save analysis result successfully', async () => {
      const mockResult: FormAnalysisResult = {
        confidence: 0.9,
        isReliable: true,
        keypoints: [],
        angles: {},
        feedback: [{
          type: 'success',
          message: 'Good form',
          confidence: 0.9,
          jointName: 'leftKnee'
        }],
        timestamp: Date.now()
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: '123' })
      });

      await service.saveAnalysis(mockResult);
      
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/form-analysis',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: expect.any(String)
        })
      );

      // Verify the body contains the analysis result
      const callBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
      expect(callBody).toMatchObject({
        result: mockResult
      });
    });

    it('should handle server errors when saving analysis', async () => {
      const mockResult: FormAnalysisResult = {
        confidence: 0.9,
        isReliable: true,
        keypoints: [],
        angles: {},
        feedback: [],
        timestamp: Date.now()
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      await expect(service.saveAnalysis(mockResult)).rejects.toThrow('Failed to save analysis');
    });

    it('should handle network errors when saving analysis', async () => {
      const mockResult: FormAnalysisResult = {
        confidence: 0.9,
        isReliable: true,
        keypoints: [],
        angles: {},
        feedback: [],
        timestamp: Date.now()
      };

      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      await expect(service.saveAnalysis(mockResult)).rejects.toThrow('Network error');
    });

    it('should handle invalid analysis data', async () => {
      const invalidResult = {
        // Missing required fields
        feedback: 'not an array' // Wrong type
      } as unknown as FormAnalysisResult;

      await expect(service.saveAnalysis(invalidResult)).rejects.toThrow('Invalid analysis data');
    });
  });

  describe('generateFeedback', () => {
    it('should generate appropriate feedback for good form', async () => {
      await service.initialize();
      
      const mockAngles = {
        leftKnee: 90, // Perfect squat knee angle
        rightKnee: 88, // Almost perfect
        leftHip: 95,  // Good hip angle
        rightHip: 97
      };
      
      const feedback = await service['generateFeedback'](mockAngles, 'squat');
      
      // Should have at least one positive feedback
      expect(feedback.some(item => item.type === 'success')).toBe(true);
      
      // Check overall feedback sentiment
      const goodFeedback = feedback.filter(item => item.type === 'success' || item.type === 'info');
      const badFeedback = feedback.filter(item => item.type === 'warning' || item.type === 'error');
      
      expect(goodFeedback.length).toBeGreaterThan(badFeedback.length);
    });
    
    it('should generate corrective feedback for poor form', async () => {
      await service.initialize();
      
      const mockAngles = {
        leftKnee: 45, // Too shallow for a squat
        rightKnee: 50, // Too shallow
        leftHip: 30,  // Poor hip angle
        rightHip: 35
      };
      
      const feedback = await service['generateFeedback'](mockAngles, 'squat');
      
      // Should have at least one corrective feedback
      expect(feedback.some(item => item.type === 'warning' || item.type === 'error')).toBe(true);
      
      // Check feedback content for specific cues
      expect(feedback.some(item => 
        item.message.toLowerCase().includes('depth') || 
        item.message.toLowerCase().includes('deeper') ||
        item.message.toLowerCase().includes('low')
      )).toBe(true);
    });
  });
}); 