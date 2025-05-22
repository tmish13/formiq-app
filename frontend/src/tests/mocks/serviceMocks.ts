import { EventEmitter } from 'events';
import { Keypoint } from '@tensorflow-models/pose-detection';

// Define types locally if they're not accessible
export interface JointAngle {
  value: number;
  confidence: number;
}

export interface JointAngles {
  [key: string]: JointAngle;
}

export interface FormFeedbackItem {
  text: string;
  severity: 'low' | 'medium' | 'high';
  type: 'form' | 'posture' | 'movement';
  confidence: number;
  timestamp: number;
  details: string;
}

export interface PoseAlignment {
  overall: number;
  vertical: number;
  lateral: number;
}

export interface MovementMetrics {
  range: number;
  smoothness: number;
  stability: number;
  speed: number;
}

export interface PoseAnalysisResult {
  timestamp: number;
  confidence: number;
  keypoints: Keypoint[];
  angles: JointAngles;
  score: number;
  feedback: FormFeedbackItem[];
  alignment: PoseAlignment;
  movement: MovementMetrics;
  exerciseType: string;
  stage: 'start' | 'middle' | 'end' | 'unknown';
  repetitionCount: number;
}

// Helper to create mock keypoints
export const createMockKeypoints = (
  confidence: number = 0.9
): Keypoint[] => [
  { x: 0, y: 0, score: confidence, name: 'nose' },
  { x: 10, y: 10, score: confidence, name: 'left_shoulder' },
  { x: -10, y: 10, score: confidence, name: 'right_shoulder' },
  { x: 15, y: 20, score: confidence, name: 'left_elbow' },
  { x: -15, y: 20, score: confidence, name: 'right_elbow' },
  { x: 20, y: 30, score: confidence, name: 'left_wrist' },
  { x: -20, y: 30, score: confidence, name: 'right_wrist' },
  { x: 10, y: 40, score: confidence, name: 'left_hip' },
  { x: -10, y: 40, score: confidence, name: 'right_hip' },
  { x: 15, y: 60, score: confidence, name: 'left_knee' },
  { x: -15, y: 60, score: confidence, name: 'right_knee' },
  { x: 20, y: 80, score: confidence, name: 'left_ankle' },
  { x: -20, y: 80, score: confidence, name: 'right_ankle' },
];

// Helper to create mock joint angles
export const createMockJointAngles = (): JointAngles => ({
  left_knee: { value: 90, confidence: 0.9 },
  right_knee: { value: 92, confidence: 0.9 },
  left_hip: { value: 120, confidence: 0.9 },
  right_hip: { value: 118, confidence: 0.9 },
  left_elbow: { value: 170, confidence: 0.9 },
  right_elbow: { value: 168, confidence: 0.9 },
  left_shoulder: { value: 80, confidence: 0.9 },
  right_shoulder: { value: 82, confidence: 0.9 },
  left_ankle: { value: 95, confidence: 0.9 },
  right_ankle: { value: 93, confidence: 0.9 }
});

// Helper to create a mock analysis result
export const createMockAnalysisResult = (
  overrides: Partial<PoseAnalysisResult> = {}
): PoseAnalysisResult => ({
  timestamp: Date.now(),
  confidence: 0.85,
  keypoints: createMockKeypoints(),
  angles: createMockJointAngles(),
  score: 85,
  feedback: [
    {
      text: 'Good form detected',
      severity: 'low',
      type: 'form',
      confidence: 0.9,
      timestamp: Date.now(),
      details: 'Continue with current form'
    }
  ],
  alignment: {
    overall: 0.9,
    vertical: 0.9,
    lateral: 0.9
  },
  movement: {
    range: 0.9,
    smoothness: 0.9,
    stability: 0.9,
    speed: 0.8
  },
  exerciseType: 'squat',
  stage: 'middle',
  repetitionCount: 2,
  ...overrides
});

// Helper to create a mock pose analysis service
export const createMockPoseAnalysisService = () => {
  const eventEmitter = new EventEmitter();
  const mockService = {
    startAnalysis: jest.fn(),
    stopAnalysis: jest.fn(),
    initialize: jest.fn().mockResolvedValue(undefined),
    on: eventEmitter.on.bind(eventEmitter),
    off: eventEmitter.off.bind(eventEmitter),
    emit: eventEmitter.emit.bind(eventEmitter),
    isAnalyzing: false,
    getLastResult: jest.fn().mockReturnValue(null),
    _emitResult: (result: PoseAnalysisResult) => {
      eventEmitter.emit('analysisResult', result);
    },
    _emitError: (error: Error) => {
      eventEmitter.emit('error', error);
    }
  };

  // Mock the startAnalysis method to update isAnalyzing state
  mockService.startAnalysis.mockImplementation(() => {
    mockService.isAnalyzing = true;
    return Promise.resolve();
  });

  // Mock the stopAnalysis method to update isAnalyzing state
  mockService.stopAnalysis.mockImplementation(() => {
    mockService.isAnalyzing = false;
  });

  return mockService;
};

// Helper to setup media devices mock
export const setupMediaDevicesMock = () => {
  const mockMediaStream = {
    getTracks: jest.fn().mockReturnValue([
      { stop: jest.fn() }
    ])
  };

  // Save original getUserMedia
  const originalGetUserMedia = navigator.mediaDevices?.getUserMedia;

  // Create mock getUserMedia
  const mockGetUserMedia = jest.fn().mockResolvedValue(mockMediaStream);

  // Set up mock navigator.mediaDevices
  Object.defineProperty(navigator, 'mediaDevices', {
    value: {
      getUserMedia: mockGetUserMedia,
      enumerateDevices: jest.fn().mockResolvedValue([
        { kind: 'videoinput', deviceId: 'mock-device-id' }
      ])
    },
    writable: true
  });

  // Return function to restore original getUserMedia
  return {
    mockMediaStream,
    mockGetUserMedia,
    cleanup: () => {
      if (originalGetUserMedia) {
        Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
          value: originalGetUserMedia,
          writable: true
        });
      }
    }
  };
}; 