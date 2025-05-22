import { FormCheck, FormCheckStatus } from '../../types/formCheck';
import { PoseAnalysisService } from '../../services/poseAnalysisService';
import { Keypoint } from '@tensorflow-models/pose-detection';
import { EventEmitter } from 'events';
import { FormFeedback, JointAngle, JointAngles, PoseAnalysisResult } from '../../types/formAnalysis';

// Helper to create a mock form check
export const createMockFormCheck = (
  overrides: Partial<FormCheck> = {}
): FormCheck => ({
  id: 1,
  user_id: 1,
  exercise_type: 'squat',
  video_url: 'https://example.com/video.mp4',
  status: 'completed' as FormCheckStatus,
  feedback_items: [
    {
      id: 1,
      form_check_id: 1,
      type: 'form',
      severity: 'medium',
      message: 'Keep your knees aligned with your toes',
      timestamp: 1000,
      description: 'Your knees are moving inward during the squat',
      suggestions: 'Focus on pushing your knees outward'
    },
    {
      id: 2,
      form_check_id: 1,
      type: 'posture',
      severity: 'high',
      message: 'Maintain a neutral spine',
      timestamp: 2000,
      description: 'Your back is rounding at the bottom of the squat',
      suggestions: 'Keep your chest up and core engaged'
    }
  ],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  ...overrides
});

// Helper to create an array of mock form checks
export const createMockFormChecks = (
  count: number,
  overridesFn?: (index: number) => Partial<FormCheck>
): FormCheck[] => {
  return Array.from({ length: count }, (_, index) => {
    const overrides = overridesFn ? overridesFn(index) : {};
    return createMockFormCheck({
      id: `mock-form-check-id-${index}`,
      ...overrides
    });
  });
};

// Helper to create mock feedback items
export const createMockFeedbackItems = (
  count: number,
  overridesFn?: (index: number) => Partial<FormFeedback>
): FormFeedback[] => {
  return Array.from({ length: count }, (_, index) => ({
    id: `feedback-${index}`,
    severity: index % 3 === 0 ? 'high' : index % 2 === 0 ? 'medium' : 'low',
    type: index % 2 === 0 ? 'form' : 'posture',
    message: `Mock feedback item ${index}`,
    timestamp: index * 1000,
    details: `Details for feedback item ${index}`,
    ...(overridesFn ? overridesFn(index) : {})
  }));
};

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

// Helper to setup canvas context mock
export const setupCanvasMock = () => {
  const mockCanvasContext = {
    clearRect: jest.fn(),
    beginPath: jest.fn(),
    arc: jest.fn(),
    fill: jest.fn(),
    stroke: jest.fn(),
    moveTo: jest.fn(),
    lineTo: jest.fn(),
    fillText: jest.fn(),
    strokeStyle: '',
    fillStyle: '',
    lineWidth: 0,
    font: '',
    textAlign: ''
  };

  const mockGetContext = jest.fn().mockReturnValue(mockCanvasContext);
  const originalGetContext = HTMLCanvasElement.prototype.getContext;

  // Mock the getContext method
  HTMLCanvasElement.prototype.getContext = mockGetContext;

  return {
    mockCanvasContext,
    mockGetContext,
    cleanup: () => {
      HTMLCanvasElement.prototype.getContext = originalGetContext;
    }
  };
};

// Helper to create a mock file
export const createMockFile = (
  name: string = 'test.mp4', 
  type: string = 'video/mp4', 
  size: number = 1024 * 1024
): File => {
  const blob = new Blob(['mock file content'], { type });
  return new File([blob], name, { type });
}; 