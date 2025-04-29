import { PoseAnalysisResult } from '../../types/pose';

class MockPoseAnalysisService {
  private static instance: MockPoseAnalysisService;
  private initialized: boolean = false;

  private constructor() {}

  static getInstance(): MockPoseAnalysisService {
    if (!MockPoseAnalysisService.instance) {
      MockPoseAnalysisService.instance = new MockPoseAnalysisService();
    }
    return MockPoseAnalysisService.instance;
  }

  initialize = jest.fn().mockResolvedValue(undefined);
  
  analyzePose = jest.fn().mockResolvedValue({
    keypoints: [
      { x: 0, y: 0, score: 1, name: 'nose' },
      { x: 10, y: 10, score: 1, name: 'left_shoulder' },
      { x: -10, y: 10, score: 1, name: 'right_shoulder' },
    ],
    score: 0.9,
    angles: {
      leftElbow: 90,
      rightElbow: 90,
      leftShoulder: 45,
      rightShoulder: 45,
      leftHip: 180,
      rightHip: 180,
      leftKnee: 180,
      rightKnee: 180,
      leftAnkle: 90,
      rightAnkle: 90,
    },
  } as PoseAnalysisResult);

  isInitialized = jest.fn().mockReturnValue(true);
  
  dispose = jest.fn().mockResolvedValue(undefined);
}

export const mockPoseAnalysisService = MockPoseAnalysisService.getInstance();
export default MockPoseAnalysisService; 