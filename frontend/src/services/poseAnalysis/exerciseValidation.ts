import { Keypoint } from '@tensorflow-models/pose-detection';
import { ExerciseType, ExerciseConfig } from './exerciseTypes';
import { JointAngle, FormValidationResult } from './types';
import { calculateJointAngles } from './utils';

interface ValidationRule {
  check: (keypoints: Keypoint[], angles: JointAngle[]) => boolean;
  message: string;
  severity: 'error' | 'warning';
}

export class ExerciseValidator {
  private static readonly VALIDATION_RULES: Record<ExerciseType, ValidationRule[]> = {
    [ExerciseType.SQUAT]: [
      {
        check: (keypoints, angles) => {
          const kneeAngle = angles.find(a => a.joint === 'knee')?.angle || 0;
          return kneeAngle >= 90;
        },
        message: 'Squat depth is too shallow. Try to go deeper.',
        severity: 'warning'
      },
      {
        check: (keypoints, angles) => {
          const backAngle = angles.find(a => a.joint === 'back')?.angle || 0;
          return backAngle >= 160;
        },
        message: 'Keep your back straight throughout the movement.',
        severity: 'error'
      },
      {
        check: (keypoints, angles) => {
          const kneeAlignment = this.checkKneeAlignment(keypoints);
          return kneeAlignment;
        },
        message: 'Keep your knees aligned with your toes.',
        severity: 'error'
      }
    ],
    [ExerciseType.PUSHUP]: [
      {
        check: (keypoints, angles) => {
          const elbowAngle = angles.find(a => a.joint === 'elbow')?.angle || 0;
          return elbowAngle <= 90;
        },
        message: 'Go lower in your push-up.',
        severity: 'warning'
      },
      {
        check: (keypoints, angles) => {
          const bodyAlignment = this.checkBodyAlignment(keypoints);
          return bodyAlignment;
        },
        message: 'Keep your body in a straight line.',
        severity: 'error'
      }
    ],
    [ExerciseType.PLANK]: [
      {
        check: (keypoints, angles) => {
          const bodyAlignment = this.checkBodyAlignment(keypoints);
          return bodyAlignment;
        },
        message: 'Keep your body in a straight line from head to heels.',
        severity: 'error'
      },
      {
        check: (keypoints, angles) => {
          const hipHeight = this.checkHipHeight(keypoints);
          return hipHeight;
        },
        message: 'Your hips are too high or too low.',
        severity: 'warning'
      }
    ]
  };

  private static checkKneeAlignment(keypoints: Keypoint[]): boolean {
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');

    if (!leftKnee || !rightKnee || !leftAnkle || !rightAnkle) return true;

    const leftAlignment = Math.abs(leftKnee.x - leftAnkle.x);
    const rightAlignment = Math.abs(rightKnee.x - rightAnkle.x);

    return leftAlignment < 0.1 && rightAlignment < 0.1;
  }

  private static checkBodyAlignment(keypoints: Keypoint[]): boolean {
    const shoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const hip = keypoints.find(kp => kp.name === 'left_hip');
    const ankle = keypoints.find(kp => kp.name === 'left_ankle');

    if (!shoulder || !hip || !ankle) return true;

    const slope = Math.abs((hip.y - shoulder.y) / (hip.x - shoulder.x));
    return slope < 0.1;
  }

  private static checkHipHeight(keypoints: Keypoint[]): boolean {
    const shoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const hip = keypoints.find(kp => kp.name === 'left_hip');
    const ankle = keypoints.find(kp => kp.name === 'left_ankle');

    if (!shoulder || !hip || !ankle) return true;

    const shoulderHeight = shoulder.y;
    const hipHeight = hip.y;
    const ankleHeight = ankle.y;

    return Math.abs(hipHeight - shoulderHeight) < 0.1 && 
           Math.abs(hipHeight - ankleHeight) < 0.1;
  }

  public static validateForm(
    exerciseType: ExerciseType,
    keypoints: Keypoint[],
    config: ExerciseConfig
  ): FormValidationResult {
    const angles = calculateJointAngles(keypoints);
    const rules = this.VALIDATION_RULES[exerciseType] || [];
    
    const issues = rules
      .filter(rule => !rule.check(keypoints, angles))
      .map(rule => ({
        message: rule.message,
        severity: rule.severity
      }));

    const score = Math.max(0, 100 - (issues.length * 10));
    
    return {
      isValid: issues.length === 0,
      score,
      issues,
      feedback: issues.map(issue => issue.message)
    };
  }
} 