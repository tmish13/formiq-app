// Mock implementation of Tensorflow pose detection library
export interface Keypoint {
  name: string;
  x: number;
  y: number;
  z?: number;
  score?: number;
  visibility?: number;
}

export interface Pose {
  keypoints: Keypoint[];
  score?: number;
}

// Mock detector classes and factory functions
export class PoseDetector {
  constructor() {}
  
  async estimatePoses(): Promise<Pose[]> {
    return [
      {
        keypoints: [
          { name: 'nose', x: 150, y: 50, score: 0.9 },
          { name: 'left_shoulder', x: 100, y: 100, score: 0.9 },
          { name: 'right_shoulder', x: 200, y: 100, score: 0.9 },
          { name: 'left_hip', x: 100, y: 200, score: 0.9 },
          { name: 'right_hip', x: 200, y: 200, score: 0.9 },
          { name: 'left_knee', x: 100, y: 300, score: 0.9 },
          { name: 'right_knee', x: 200, y: 300, score: 0.9 },
          { name: 'left_ankle', x: 100, y: 400, score: 0.9 },
          { name: 'right_ankle', x: 200, y: 400, score: 0.9 }
        ],
        score: 0.9
      }
    ];
  }
  
  static async createDetector(): Promise<PoseDetector> {
    return new PoseDetector();
  }
}

// Export model objects and enums
export const SupportedModels = {
  MoveNet: 'MoveNet',
  BlazePose: 'BlazePose',
  PoseNet: 'PoseNet'
};

export const createDetector = async () => {
  return new PoseDetector();
};

// Mock any other exports needed by the components
export const movenet = {
  modelType: SupportedModels.MoveNet
}; 