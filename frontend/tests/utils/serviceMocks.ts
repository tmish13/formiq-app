/**
 * Utility file containing mock implementations for various services used in tests
 */

/**
 * Creates a mock for the PoseAnalysisService
 */
export function createMockPoseAnalysisService() {
  // Define the mock service object
  const mockService = {
    initialize: jest.fn().mockResolvedValue(undefined),
    startAnalysis: jest.fn().mockResolvedValue(undefined),
    stopAnalysis: jest.fn(),
    cleanup: jest.fn(),
    drawPose: jest.fn(),
    drawSkeleton: jest.fn(),
    drawKeypoints: jest.fn(),
    triggerAnalysisResult: null as ((result: any) => void) | null
  };

  // Mock the static getInstance method
  const mockGetInstance = jest.fn().mockImplementation((config: any) => {
    // Store the callback for later use
    if (config.onAnalysisResult) {
      mockService.triggerAnalysisResult = (result) => {
        config.onAnalysisResult(result);
      };
    }
    return mockService;
  });

  return {
    mockService,
    mockGetInstance
  };
}

/**
 * Types for the PoseAnalysis test data
 */
export interface FeedbackItem {
  type: 'success' | 'warning' | 'error';
  text: string;
}

export interface Keypoint {
  name: string;
  x: number;
  y: number;
  score?: number;
}

export interface JointAngle {
  angle: number;
  isCorrect: boolean;
}

export interface PoseAnalysisResult {
  score: number;
  keypoints: Keypoint[];
  feedback: FeedbackItem[];
  angles: Record<string, JointAngle | number>;
  exerciseType: string;
}

/**
 * Creates a mock analysis result with proper typing
 */
export function createMockAnalysisResult(
  exerciseType: string,
  score: number = 85,
  customFeedback: FeedbackItem[] = []
): PoseAnalysisResult {
  const feedback: FeedbackItem[] = customFeedback.length > 0 ? customFeedback : [
    createFeedbackItem({ type: 'success', text: 'Good form overall' }),
    createFeedbackItem({ type: 'warning', text: 'Keep knees aligned with toes' })
  ];

  return {
    score,
    keypoints: [],
    feedback,
    angles: {
      leftKnee: { angle: 90, isCorrect: true },
      rightKnee: { angle: 85, isCorrect: true },
      leftElbow: { angle: 170, isCorrect: false },
      rightElbow: { angle: 175, isCorrect: false }
    },
    exerciseType
  };
}

/**
 * Create a feedback item for pose analysis tests
 */
export function createFeedbackItem(props: { type: 'success' | 'warning' | 'error'; text: string }): FeedbackItem {
  return {
    type: props.type,
    text: props.text
  };
}

/**
 * Mock setup for navigator.mediaDevices.getUserMedia
 */
export function setupMediaDevicesMock() {
  const mockGetUserMedia = jest.fn().mockResolvedValue({
    getTracks: () => [{ stop: jest.fn() }]
  });

  Object.defineProperty(navigator, 'mediaDevices', {
    value: {
      getUserMedia: mockGetUserMedia,
    },
    writable: true,
  });

  // Mock HTMLVideoElement play method
  const mockVideoPlay = jest.fn().mockImplementation(() => Promise.resolve());
  Object.defineProperty(HTMLVideoElement.prototype, 'play', {
    writable: true,
    value: mockVideoPlay,
  });

  return {
    mockGetUserMedia,
    mockVideoPlay
  };
} 