import { formAnalysisService } from '../../services/formAnalysisService';
import { apiService } from '../../services/apiService';
import { poseAnalysisService } from '../../services/poseAnalysisService';
import { FormAnalysisRequest, FormAnalysisResult, FormAnalysisResponse } from '../../types/formAnalysis';
import { ExerciseType } from '../../services/exerciseLibraryService';
import { mockPoseData, mockVideoElement } from '../__mocks__/poseData';
import { waitFor } from '@testing-library/react';

// Mock dependencies
jest.mock('../../services/apiService');
jest.mock('../../services/poseAnalysisService');

describe('FormAnalysisService', () => {
  const mockKeypoints = [
    { x: 100, y: 100, score: 0.9, name: 'nose' },
    { x: 200, y: 200, score: 0.8, name: 'left_shoulder' },
    { x: 300, y: 300, score: 0.85, name: 'right_shoulder' }
  ];

  const mockFormAnalysisRequest: FormAnalysisRequest = {
    videoUrl: 'https://example.com/video.mp4',
    exerciseId: '123',
    keypoints: mockKeypoints,
    duration: 10
  };

  const mockFormAnalysisResult: FormAnalysisResult = {
    exerciseType: ExerciseType.STRENGTH,
    confidence: 0.95,
    keypoints: mockKeypoints,
    metrics: {
      alignment: 0.9,
      stability: 0.85,
      symmetry: 0.8,
      consistency: 0.75
    },
    feedback: ['Keep your back straight', 'Lower your hips more'],
    suggestions: ['Try to maintain better form', 'Focus on your breathing']
  };

  const mockFormAnalysisResponse: FormAnalysisResponse = {
    id: '123',
    status: 'completed',
    result: mockFormAnalysisResult
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('initialization', () => {
    it('should initialize with default configuration', () => {
      expect(formAnalysisService).toBeDefined();
    });

    it('should handle initialization errors gracefully', async () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      // Force initialization error
      jest.spyOn(formAnalysisService as any, 'initializeDetector').mockRejectedValue(new Error('Init failed'));
      
      await formAnalysisService.startAnalysis(mockVideoElement);
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('pose analysis', () => {
    it('should analyze pose data correctly', async () => {
      const result = await formAnalysisService.analyzePose(mockPoseData);
      expect(result).toBeDefined();
      expect(result.confidence).toBeGreaterThan(0);
    });

    it('should handle missing keypoints gracefully', async () => {
      const incompleteData = { ...mockPoseData, keypoints: mockPoseData.keypoints.slice(0, 5) };
      const result = await formAnalysisService.analyzePose(incompleteData);
      expect(result.confidence).toBeLessThan(0.5);
    });

    it('should reject invalid pose data', async () => {
      await expect(formAnalysisService.analyzePose(null as any)).rejects.toThrow();
    });
  });

  describe('real-time analysis', () => {
    it('should maintain performance under continuous analysis', async () => {
      const startTime = performance.now();
      await formAnalysisService.startAnalysis(mockVideoElement);
      
      // Simulate 10 frames of analysis
      for (let i = 0; i < 10; i++) {
        await formAnalysisService.analyzePose(mockPoseData);
      }
      
      const duration = performance.now() - startTime;
      expect(duration).toBeLessThan(1000); // Should complete within 1 second
    });

    it('should handle video stream interruptions', async () => {
      const onErrorMock = jest.fn();
      formAnalysisService.on('error', onErrorMock);
      
      // Simulate stream interruption
      mockVideoElement.dispatchEvent(new Event('pause'));
      
      await waitFor(() => {
        expect(onErrorMock).toHaveBeenCalled();
      });
    });
  });

  describe('error handling', () => {
    it('should recover from temporary detection failures', async () => {
      const errorSpy = jest.fn();
      formAnalysisService.on('error', errorSpy);
      
      // Simulate temporary failure
      jest.spyOn(formAnalysisService as any, 'detectPoses')
        .mockRejectedValueOnce(new Error('Temporary failure'))
        .mockResolvedValueOnce(mockPoseData);
      
      await formAnalysisService.startAnalysis(mockVideoElement);
      expect(errorSpy).toHaveBeenCalledTimes(1);
      
      // Should recover on next frame
      const result = await formAnalysisService.analyzePose(mockPoseData);
      expect(result).toBeDefined();
    });

    it('should handle low confidence detections appropriately', async () => {
      const lowConfidenceData = {
        ...mockPoseData,
        keypoints: mockPoseData.keypoints.map(kp => ({ ...kp, score: 0.1 }))
      };
      
      const result = await formAnalysisService.analyzePose(lowConfidenceData);
      expect(result.isReliable).toBe(false);
      expect(result.confidence).toBeLessThan(0.3);
    });
  });

  describe('performance optimization', () => {
    it('should maintain frame rate under load', async () => {
      const frameRates: number[] = [];
      let lastFrameTime = performance.now();
      
      // Analyze 30 frames and measure frame rate
      for (let i = 0; i < 30; i++) {
        await formAnalysisService.analyzePose(mockPoseData);
        const currentTime = performance.now();
        const frameTime = currentTime - lastFrameTime;
        frameRates.push(1000 / frameTime);
        lastFrameTime = currentTime;
      }
      
      const averageFrameRate = frameRates.reduce((a, b) => a + b) / frameRates.length;
      expect(averageFrameRate).toBeGreaterThan(15); // Should maintain at least 15 FPS
    });

    it('should handle memory cleanup correctly', async () => {
      await formAnalysisService.startAnalysis(mockVideoElement);
      
      // Force garbage collection if possible
      if (global.gc) {
        global.gc();
      }
      
      // Simulate multiple start/stop cycles
      for (let i = 0; i < 5; i++) {
        await formAnalysisService.stopAnalysis();
        await formAnalysisService.startAnalysis(mockVideoElement);
      }
      
      // Should not have memory leaks
      // Note: This is a basic check, real memory leaks should be tested with proper memory profiling tools
      expect(formAnalysisService.isAnalyzing).toBe(true);
    });
  });

  describe('analyzeForm', () => {
    it('should successfully analyze form and return results', async () => {
      // Mock API response
      (apiService.formAnalysis.analyze as jest.Mock).mockResolvedValue({
        data: mockFormAnalysisResponse
      });

      // Mock pose analysis
      (poseAnalysisService.analyzePose as jest.Mock).mockResolvedValue({
        keypoints: mockKeypoints,
        metrics: mockFormAnalysisResult.metrics
      });

      const result = await formAnalysisService.analyzeForm(mockFormAnalysisRequest);

      expect(result).toEqual(mockFormAnalysisResult);
      expect(apiService.formAnalysis.analyze).toHaveBeenCalledWith(mockFormAnalysisRequest);
      expect(poseAnalysisService.analyzePose).toHaveBeenCalledWith(mockKeypoints);
    });

    it('should handle errors during form analysis', async () => {
      const errorMessage = 'Analysis failed';
      (apiService.formAnalysis.analyze as jest.Mock).mockRejectedValue(new Error(errorMessage));

      await expect(formAnalysisService.analyzeForm(mockFormAnalysisRequest))
        .rejects
        .toThrow(errorMessage);
    });
  });

  describe('getState', () => {
    it('should return the current state', () => {
      const state = formAnalysisService.getState();
      
      expect(state).toEqual({
        isAnalyzing: false,
        error: null,
        lastAnalysis: null
      });
    });

    it('should update state after successful analysis', async () => {
      (apiService.formAnalysis.analyze as jest.Mock).mockResolvedValue({
        data: mockFormAnalysisResponse
      });

      await formAnalysisService.analyzeForm(mockFormAnalysisRequest);
      const state = formAnalysisService.getState();

      expect(state.isAnalyzing).toBe(false);
      expect(state.error).toBe(null);
      expect(state.lastAnalysis).toEqual(mockFormAnalysisResult);
    });

    it('should update state after failed analysis', async () => {
      const errorMessage = 'Analysis failed';
      (apiService.formAnalysis.analyze as jest.Mock).mockRejectedValue(new Error(errorMessage));

      await expect(formAnalysisService.analyzeForm(mockFormAnalysisRequest))
        .rejects
        .toThrow(errorMessage);

      const state = formAnalysisService.getState();
      expect(state.isAnalyzing).toBe(false);
      expect(state.error).toBe(errorMessage);
      expect(state.lastAnalysis).toBe(null);
    });
  });
}); 