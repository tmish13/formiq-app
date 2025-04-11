import { poseAnalysisService } from '../../services/poseAnalysisService';
import { apiService } from '../../services/apiService';

// Mock the apiService
jest.mock('../../services/apiService', () => ({
  apiService: {
    poseAnalysis: {
      analyze: jest.fn(),
      detect: jest.fn(),
    },
  },
}));

describe('PoseAnalysisService', () => {
  const mockKeypoints = [
    { x: 100, y: 100, score: 0.9 },
    { x: 200, y: 200, score: 0.8 },
  ];

  const mockPoseAnalysisResult = {
    keypoints: mockKeypoints,
    metrics: {
      alignment: 0.8,
      stability: 0.7,
      symmetry: 0.9,
      consistency: 0.85,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (apiService.poseAnalysis.analyze as jest.Mock).mockResolvedValue({ data: mockPoseAnalysisResult });
    (apiService.poseAnalysis.detect as jest.Mock).mockResolvedValue({ data: { keypoints: mockKeypoints } });
  });

  describe('analyzePose', () => {
    it('should analyze pose keypoints', async () => {
      const result = await poseAnalysisService.analyzePose(mockKeypoints);

      expect(apiService.poseAnalysis.analyze).toHaveBeenCalledWith({ keypoints: mockKeypoints });
      expect(result).toEqual(mockPoseAnalysisResult);
    });

    it('should handle errors during analysis', async () => {
      const error = new Error('Analysis failed');
      (apiService.poseAnalysis.analyze as jest.Mock).mockRejectedValue(error);

      await expect(poseAnalysisService.analyzePose(mockKeypoints)).rejects.toThrow('Analysis failed');
    });
  });

  describe('detectPose', () => {
    it('should detect pose from video', async () => {
      const videoUrl = 'https://example.com/video';
      const result = await poseAnalysisService.detectPose(videoUrl);

      expect(apiService.poseAnalysis.detect).toHaveBeenCalledWith({ videoUrl });
      expect(result).toEqual(mockKeypoints);
    });

    it('should handle errors during detection', async () => {
      const error = new Error('Detection failed');
      (apiService.poseAnalysis.detect as jest.Mock).mockRejectedValue(error);

      await expect(poseAnalysisService.detectPose('https://example.com/video')).rejects.toThrow('Detection failed');
    });
  });

  describe('getState', () => {
    it('should return the current state', () => {
      const state = poseAnalysisService.getState();

      expect(state).toEqual({
        isAnalyzing: false,
        error: null,
        lastAnalysis: null,
      });
    });

    it('should update state after successful analysis', async () => {
      await poseAnalysisService.analyzePose(mockKeypoints);

      const state = poseAnalysisService.getState();

      expect(state).toEqual({
        isAnalyzing: false,
        error: null,
        lastAnalysis: mockPoseAnalysisResult,
      });
    });

    it('should update state after error', async () => {
      const error = new Error('Analysis failed');
      (apiService.poseAnalysis.analyze as jest.Mock).mockRejectedValue(error);

      await expect(poseAnalysisService.analyzePose(mockKeypoints)).rejects.toThrow();

      const state = poseAnalysisService.getState();

      expect(state).toEqual({
        isAnalyzing: false,
        error: 'Analysis failed',
        lastAnalysis: null,
      });
    });
  });
}); 