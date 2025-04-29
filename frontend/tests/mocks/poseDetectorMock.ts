import { jest } from '@jest/globals';
import { 
  PoseDetector, 
  Pose, 
  Keypoint,
  MoveNetEstimationConfig,
  BlazePoseTfjsEstimationConfig,
  BlazePoseMediaPipeEstimationConfig,
  PoseNetEstimationConfig
} from '@tensorflow-models/pose-detection';

/**
 * Mock implementation of the PoseDetector interface for testing
 */
export class MockPoseDetector implements PoseDetector {
  /**
   * Mock implementation of estimatePoses
   * @param image An image or video frame
   * @param config Optional configuration
   * @param timestamp Optional timestamp
   * @returns A promise that resolves to an array of poses
   */
  estimatePoses(
    image: HTMLVideoElement | HTMLImageElement | HTMLCanvasElement | ImageData,
    config?: MoveNetEstimationConfig | BlazePoseTfjsEstimationConfig | BlazePoseMediaPipeEstimationConfig | PoseNetEstimationConfig,
    timestamp?: number
  ): Promise<Pose[]> {
    return Promise.resolve([{
      keypoints: [
        { name: 'nose', x: 150, y: 50, score: 0.9 },
        { name: 'left_eye', x: 135, y: 45, score: 0.9 },
        { name: 'right_eye', x: 165, y: 45, score: 0.9 },
        { name: 'left_ear', x: 120, y: 55, score: 0.9 },
        { name: 'right_ear', x: 180, y: 55, score: 0.9 },
        { name: 'left_shoulder', x: 100, y: 100, score: 0.9 },
        { name: 'right_shoulder', x: 200, y: 100, score: 0.9 },
        { name: 'left_elbow', x: 90, y: 150, score: 0.9 },
        { name: 'right_elbow', x: 210, y: 150, score: 0.9 },
        { name: 'left_wrist', x: 80, y: 200, score: 0.9 },
        { name: 'right_wrist', x: 220, y: 200, score: 0.9 },
        { name: 'left_hip', x: 100, y: 200, score: 0.9 },
        { name: 'right_hip', x: 200, y: 200, score: 0.9 },
        { name: 'left_knee', x: 100, y: 300, score: 0.9 },
        { name: 'right_knee', x: 200, y: 300, score: 0.9 },
        { name: 'left_ankle', x: 100, y: 400, score: 0.9 },
        { name: 'right_ankle', x: 200, y: 400, score: 0.9 }
      ],
      score: 0.9
    }]);
  }

  /**
   * Mock implementation of dispose
   */
  dispose(): void {
    // No-op in mock
  }

  /**
   * Mock implementation of reset
   */
  reset(): void {
    // No-op in mock
  }
}

/**
 * Helper function to create a mock pose with custom keypoints
 * @param keypoints Array of keypoints to use
 * @param score Optional score for the pose
 * @returns A pose object
 */
export function createMockPose(keypoints: Keypoint[], score: number = 0.9): Pose {
  return {
    keypoints,
    score
  };
}

/**
 * Helper function to generate mock keypoints for testing
 * @param count Number of keypoints to generate
 * @param baseX Base X coordinate
 * @param baseY Base Y coordinate
 * @param score Score for all keypoints
 * @returns Array of keypoints
 */
export function generateMockKeypoints(
  count: number = 17,
  baseX: number = 150,
  baseY: number = 150,
  score: number = 0.9
): Keypoint[] {
  const keypointNames = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
  ];
  
  return Array.from({ length: count }, (_, i) => ({
    name: keypointNames[i % keypointNames.length],
    x: baseX + (i * 10),
    y: baseY + (i * 10),
    score
  }));
} 