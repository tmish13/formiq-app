import { Keypoint } from '@tensorflow-models/pose-detection';

export const mockVideoElement = {
  videoWidth: 640,
  videoHeight: 480,
  readyState: 4,
  play: jest.fn(),
  pause: jest.fn(),
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  dispatchEvent: jest.fn(),
} as unknown as HTMLVideoElement;

export const mockPoseData = {
  score: 0.9,
  keypoints: [
    { x: 200, y: 100, score: 0.9, name: 'nose' },
    { x: 220, y: 110, score: 0.85, name: 'left_eye' },
    { x: 180, y: 110, score: 0.88, name: 'right_eye' },
    { x: 230, y: 150, score: 0.92, name: 'left_ear' },
    { x: 170, y: 150, score: 0.91, name: 'right_ear' },
    { x: 250, y: 200, score: 0.95, name: 'left_shoulder' },
    { x: 150, y: 200, score: 0.94, name: 'right_shoulder' },
    { x: 270, y: 300, score: 0.93, name: 'left_elbow' },
    { x: 130, y: 300, score: 0.92, name: 'right_elbow' },
    { x: 290, y: 380, score: 0.89, name: 'left_wrist' },
    { x: 110, y: 380, score: 0.88, name: 'right_wrist' },
    { x: 260, y: 400, score: 0.96, name: 'left_hip' },
    { x: 140, y: 400, score: 0.95, name: 'right_hip' },
    { x: 280, y: 500, score: 0.94, name: 'left_knee' },
    { x: 120, y: 500, score: 0.93, name: 'right_knee' },
    { x: 290, y: 580, score: 0.87, name: 'left_ankle' },
    { x: 110, y: 580, score: 0.86, name: 'right_ankle' }
  ] as Keypoint[],
  id: 0
}; 