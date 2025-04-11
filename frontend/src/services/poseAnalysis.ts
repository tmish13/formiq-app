import * as poseDetection from '@tensorflow-models/pose-detection';
import { Keypoint } from '@tensorflow-models/pose-detection';
import { JointAngle, FormFeedback } from '../types/formAnalysis';

export class PoseAnalysis {
  private detector: poseDetection.PoseDetector | null = null;
  private modelConfig = {
    modelType: poseDetection.movenet.modelType.SINGLEPOSE_THUNDER,
    enableSmoothing: true,
    minPoseScore: 0.3,
  };

  async initialize(): Promise<void> {
    try {
      this.detector = await poseDetection.createDetector(
        poseDetection.SupportedModels.MoveNet,
        this.modelConfig
      );
    } catch (error) {
      console.error('Failed to initialize pose detector:', error);
      throw new Error('Failed to initialize pose detection model');
    }
  }

  async detectPose(videoElement: HTMLVideoElement): Promise<Keypoint[]> {
    if (!this.detector) {
      throw new Error('Pose detector not initialized');
    }

    try {
      const poses = await this.detector.estimatePoses(videoElement);
      return poses[0]?.keypoints || [];
    } catch (error) {
      console.error('Failed to detect pose:', error);
      throw new Error('Failed to detect pose');
    }
  }

  calculateJointAngles(keypoints: Keypoint[]): JointAngle[] {
    const angles: JointAngle[] = [];

    // Calculate elbow angles
    const leftElbowAngle = this.calculateAngle(
      this.findKeypoint(keypoints, 'left_shoulder'),
      this.findKeypoint(keypoints, 'left_elbow'),
      this.findKeypoint(keypoints, 'left_wrist')
    );
    if (leftElbowAngle !== null) {
      angles.push({ joint: 'left_elbow', angle: leftElbowAngle });
    }

    const rightElbowAngle = this.calculateAngle(
      this.findKeypoint(keypoints, 'right_shoulder'),
      this.findKeypoint(keypoints, 'right_elbow'),
      this.findKeypoint(keypoints, 'right_wrist')
    );
    if (rightElbowAngle !== null) {
      angles.push({ joint: 'right_elbow', angle: rightElbowAngle });
    }

    // Calculate knee angles
    const leftKneeAngle = this.calculateAngle(
      this.findKeypoint(keypoints, 'left_hip'),
      this.findKeypoint(keypoints, 'left_knee'),
      this.findKeypoint(keypoints, 'left_ankle')
    );
    if (leftKneeAngle !== null) {
      angles.push({ joint: 'left_knee', angle: leftKneeAngle });
    }

    const rightKneeAngle = this.calculateAngle(
      this.findKeypoint(keypoints, 'right_hip'),
      this.findKeypoint(keypoints, 'right_knee'),
      this.findKeypoint(keypoints, 'right_ankle')
    );
    if (rightKneeAngle !== null) {
      angles.push({ joint: 'right_knee', angle: rightKneeAngle });
    }

    return angles;
  }

  private findKeypoint(keypoints: Keypoint[], name: string): Keypoint | null {
    return keypoints.find(kp => kp.name === name) || null;
  }

  private calculateAngle(p1: Keypoint | null, p2: Keypoint | null, p3: Keypoint | null): number | null {
    if (!p1 || !p2 || !p3) return null;

    const angle = Math.atan2(p3.y - p2.y, p3.x - p2.x) - Math.atan2(p1.y - p2.y, p1.x - p2.x);
    let degrees = angle * (180 / Math.PI);
    degrees = (degrees + 360) % 360;
    return degrees;
  }

  analyzePose(keypoints: Keypoint[], angles: JointAngle[]): FormFeedback[] {
    const feedback: FormFeedback[] = [];

    // Check pose visibility
    const visibleKeypoints = keypoints.filter(kp => kp.score && kp.score > 0.3).length;
    if (visibleKeypoints < 10) {
      feedback.push({
        type: 'error',
        message: 'Poor pose visibility',
        suggestion: 'Please ensure your full body is visible in the frame'
      });
    }

    // Analyze joint angles
    angles.forEach(angle => {
      switch (angle.joint) {
        case 'left_elbow':
        case 'right_elbow':
          if (angle.angle < 30) {
            feedback.push({
              type: 'warning',
              message: `${angle.joint} angle too small`,
              suggestion: 'Try to extend your arm more'
            });
          } else if (angle.angle > 160) {
            feedback.push({
              type: 'warning',
              message: `${angle.joint} angle too large`,
              suggestion: 'Try to bend your arm more'
            });
          }
          break;
        case 'left_knee':
        case 'right_knee':
          if (angle.angle < 60) {
            feedback.push({
              type: 'warning',
              message: `${angle.joint} angle too small`,
              suggestion: 'Try to straighten your leg more'
            });
          } else if (angle.angle > 170) {
            feedback.push({
              type: 'warning',
              message: `${angle.joint} angle too large`,
              suggestion: 'Try to bend your knee more'
            });
          }
          break;
      }
    });

    return feedback;
  }
}

export const poseAnalysis = new PoseAnalysis(); 