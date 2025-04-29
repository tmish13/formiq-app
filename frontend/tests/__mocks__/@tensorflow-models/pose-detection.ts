import { jest } from '@jest/globals';

// Define the interfaces and types
export interface Keypoint {
  x: number;
  y: number;
  z?: number;
  score?: number;
  name?: string;
}

export interface Pose {
  keypoints: Keypoint[];
  score?: number;
}

export interface PoseDetector {
  estimatePoses(image: HTMLVideoElement | HTMLImageElement | HTMLCanvasElement | ImageData, config?: { flipHorizontal?: boolean; maxPoses?: number }): Promise<Pose[]>;
  dispose(): void;
  reset?(): void;
}

export interface PoseDetectorConfig {
  modelType?: string;
  enableSmoothing?: boolean;
  runtime?: string;
}

// Export the enum
export const SupportedModels = {
  MoveNet: 'movenet',
  BlazePose: 'blazepose',
  PoseNet: 'posenet'
};

// Export model objects
export const movenet = {
  modelType: {
    SINGLEPOSE_LIGHTNING: 'SINGLEPOSE_LIGHTNING',
    SINGLEPOSE_THUNDER: 'SINGLEPOSE_THUNDER',
    MULTIPOSE_LIGHTNING: 'MULTIPOSE_LIGHTNING'
  }
};

export const blazepose = {
  modelType: SupportedModels.BlazePose
};

export const posenet = {
  modelType: SupportedModels.PoseNet
};

const mockKeypoints: Keypoint[] = [
  { x: 150, y: 50, score: 0.9, name: 'nose' },
  { x: 135, y: 45, score: 0.9, name: 'left_eye' },
  { x: 165, y: 45, score: 0.9, name: 'right_eye' },
  { x: 120, y: 55, score: 0.9, name: 'left_ear' },
  { x: 180, y: 55, score: 0.9, name: 'right_ear' },
  { x: 100, y: 100, score: 0.9, name: 'left_shoulder' },
  { x: 200, y: 100, score: 0.9, name: 'right_shoulder' },
  { x: 90, y: 150, score: 0.9, name: 'left_elbow' },
  { x: 210, y: 150, score: 0.9, name: 'right_elbow' },
  { x: 80, y: 200, score: 0.9, name: 'left_wrist' },
  { x: 220, y: 200, score: 0.9, name: 'right_wrist' },
  { x: 100, y: 200, score: 0.9, name: 'left_hip' },
  { x: 200, y: 200, score: 0.9, name: 'right_hip' },
  { x: 100, y: 300, score: 0.9, name: 'left_knee' },
  { x: 200, y: 300, score: 0.9, name: 'right_knee' },
  { x: 100, y: 400, score: 0.9, name: 'left_ankle' },
  { x: 200, y: 400, score: 0.9, name: 'right_ankle' }
];

const mockPose: Pose = {
  keypoints: mockKeypoints,
  score: 0.9
};

class MockPoseDetector implements PoseDetector {
  async estimatePoses(
    image: HTMLVideoElement | HTMLImageElement | HTMLCanvasElement | ImageData,
    config?: { flipHorizontal?: boolean; maxPoses?: number }
  ): Promise<Pose[]> {
    return [mockPose];
  }

  dispose(): void {}
  reset(): void {}
}

// Mock the createDetector function
export const createDetector = jest.fn().mockImplementation(() => {
  return Promise.resolve({
    estimatePoses: jest.fn().mockImplementation(() => {
      return Promise.resolve([
        {
          keypoints: [
            { name: 'nose', x: 0, y: 0, score: 0.9 },
            { name: 'left_shoulder', x: -0.2, y: 0.2, score: 0.9 },
            { name: 'right_shoulder', x: 0.2, y: 0.2, score: 0.9 },
            { name: 'left_elbow', x: -0.3, y: 0.4, score: 0.9 },
            { name: 'right_elbow', x: 0.3, y: 0.4, score: 0.9 },
            { name: 'left_wrist', x: -0.4, y: 0.6, score: 0.9 },
            { name: 'right_wrist', x: 0.4, y: 0.6, score: 0.9 },
            { name: 'left_hip', x: -0.1, y: 0.7, score: 0.9 },
            { name: 'right_hip', x: 0.1, y: 0.7, score: 0.9 },
            { name: 'left_knee', x: -0.15, y: 0.85, score: 0.9 },
            { name: 'right_knee', x: 0.15, y: 0.85, score: 0.9 },
            { name: 'left_ankle', x: -0.2, y: 1.0, score: 0.9 },
            { name: 'right_ankle', x: 0.2, y: 1.0, score: 0.9 }
          ],
          score: 0.9
        }
      ]);
    })
  });
}); 