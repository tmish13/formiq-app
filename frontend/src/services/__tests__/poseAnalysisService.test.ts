import { jest } from '@jest/globals';
import * as tf from '@tensorflow/tfjs';
import * as poseDetection from '@tensorflow-models/pose-detection';
import { PoseAnalysisService, PoseAnalysisConfig, ExerciseType } from '../poseAnalysisService';
import { EventEmitter } from 'events';
import { MovementPath, JointAngles, PoseAnalysisResult, JointAngle, FormFeedback } from '../../types/formAnalysis';
import { MockPoseDetector, createMockPose } from '../../../tests/mocks/poseDetectorMock';

// Mock TensorFlow.js
jest.mock('@tensorflow/tfjs', () => ({
  ready: jest.fn(() => Promise.resolve()),
  setBackend: jest.fn((backend: string) => Promise.resolve()),
  getBackend: jest.fn(() => 'webgl'),
  backend: jest.fn(() => ({
    gpgpu: {
      gl: {
        getExtension: jest.fn(() => ({})),
      },
    },
  })),
  env: jest.fn(() => ({
    set: jest.fn(),
  }))
}));

// Create mock keypoints
const mockKeypoints: poseDetection.Keypoint[] = [
  { x: 0, y: 0, score: 0.9, name: 'nose' },
  { x: 10, y: 10, score: 0.8, name: 'left_shoulder' },
  { x: -10, y: 10, score: 0.8, name: 'right_shoulder' },
  { x: 15, y: 20, score: 0.7, name: 'left_elbow' },
  { x: -15, y: 20, score: 0.7, name: 'right_elbow' }
];

// Create mock pose
const mockPose = createMockPose(mockKeypoints, 0.85);

// Create a mock detector
const mockDetector = {
  estimatePoses: jest.fn().mockResolvedValue([mockPose]),
  dispose: jest.fn(),
  reset: jest.fn()
};

// Mock pose-detection module
jest.mock('@tensorflow-models/pose-detection', () => ({
  SupportedModels: {
    MoveNet: 'MoveNet'
  },
  createDetector: jest.fn().mockResolvedValue(mockDetector)
}));

describe('PoseAnalysisService', () => {
  let service: PoseAnalysisService;
  let mockVideoElement: HTMLVideoElement;
  
  const mockConfig: PoseAnalysisConfig = {
    minConfidence: 0.3,
    modelType: 'MoveNet',
    exerciseType: 'squat' as ExerciseType,
    deviceOptimization: {
      targetFPS: 30,
      downsampleFactor: 1,
      useWebGL: true,
      enableSmoothing: true,
      batchSize: 4,
      kernelOptimization: true
    }
  };

  beforeEach(async () => {
    mockVideoElement = document.createElement('video');
    service = await PoseAnalysisService.getInstance(mockConfig);
    await service.initialize();
  });

  afterEach(async () => {
    service.stopAnalysis();
    jest.clearAllMocks();
  });

  it('should initialize correctly', async () => {
    expect(service).toBeDefined();
    expect(poseDetection.createDetector).toHaveBeenCalled();
  });

  it('should start and stop analysis correctly', async () => {
    await service.startAnalysis(mockVideoElement);
    expect(service['isAnalyzing']).toBe(true);
    
    service.stopAnalysis();
    expect(service['isAnalyzing']).toBe(false);
  });

  it('should handle errors during analysis', async () => {
    const errorHandler = jest.fn();
    service.on('error', errorHandler);

    // Mock the error for this test only
    mockDetector.estimatePoses.mockRejectedValueOnce(new Error('Test error'));
    
    await service.startAnalysis(mockVideoElement);

    // Wait for error event
    await new Promise(resolve => setTimeout(resolve, 200));
    
    expect(errorHandler).toHaveBeenCalled();
  });

  // ... rest of the test file ...
}); 