export interface Keypoint {
  x: number;
  y: number;
  score: number;
  name: string;
}

export interface JointAngles {
  leftElbow: number;
  rightElbow: number;
  leftShoulder: number;
  rightShoulder: number;
  leftHip: number;
  rightHip: number;
  leftKnee: number;
  rightKnee: number;
  leftAnkle: number;
  rightAnkle: number;
}

export interface PoseAnalysisResult {
  keypoints: Keypoint[];
  score: number;
  angles: JointAngles;
} 