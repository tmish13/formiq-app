import * as poseDetection from '@tensorflow-models/pose-detection';
import { FeedbackItem } from '../types/exercise';

export function analyzeExerciseForm(
  exerciseType: string,
  keypoints: poseDetection.Keypoint[],
  previousKeypoints: poseDetection.Keypoint[] | null
): FeedbackItem[] {
  switch (exerciseType.toLowerCase()) {
    case 'squat':
      return analyzeSquatForm(keypoints, previousKeypoints);
    case 'deadlift':
      return analyzeDeadliftForm(keypoints, previousKeypoints);
    default:
      return [];
  }
}

function analyzeSquatForm(
  keypoints: poseDetection.Keypoint[],
  previousKeypoints: poseDetection.Keypoint[] | null
): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  const timestamp = Date.now();

  // Get key points
  const leftHip = keypoints.find(kp => kp.name === 'left_hip');
  const rightHip = keypoints.find(kp => kp.name === 'right_hip');
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
  const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
  const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');

  if (!leftHip || !rightHip || !leftKnee || !rightKnee || !leftAnkle || !rightAnkle || !leftShoulder || !rightShoulder) {
    return [{
      message: 'Please ensure your full body is visible in the frame',
      severity: 'high',
      type: 'form',
      confidence: 1,
      timestamp
    }];
  }

  // Check knee alignment
  const leftKneeAlignment = checkKneeAlignment(leftHip, leftKnee, leftAnkle);
  const rightKneeAlignment = checkKneeAlignment(rightHip, rightKnee, rightAnkle);

  if (!leftKneeAlignment || !rightKneeAlignment) {
    feedback.push({
      message: 'Keep your knees aligned with your toes',
      severity: 'high',
      type: 'alignment',
      details: 'Your knees should track over your toes throughout the movement',
      confidence: 0.9,
      timestamp
    });
  }

  // Check hip depth
  const hipDepth = calculateHipDepth(leftHip, leftKnee);
  if (hipDepth > 0.2) {
    feedback.push({
      message: 'Lower your hips more to achieve proper squat depth',
      severity: 'medium',
      type: 'range',
      details: 'Aim to get your thighs parallel to the ground',
      confidence: 0.8,
      timestamp
    });
  }

  // Check back angle
  const backAngle = calculateBackAngle(leftShoulder, leftHip);
  if (Math.abs(backAngle) > 30) {
    feedback.push({
      message: 'Keep your back straight',
      severity: 'high',
      type: 'form',
      details: 'Maintain a neutral spine throughout the movement',
      confidence: 0.9,
      timestamp
    });
  }

  return feedback;
}

function analyzeDeadliftForm(
  keypoints: poseDetection.Keypoint[],
  previousKeypoints: poseDetection.Keypoint[] | null
): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  const timestamp = Date.now();

  // Get key points
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
  const leftHip = keypoints.find(kp => kp.name === 'left_hip');
  const rightHip = keypoints.find(kp => kp.name === 'right_hip');
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee');

  if (!leftShoulder || !rightShoulder || !leftHip || !rightHip || !leftKnee || !rightKnee) {
    return [{
      message: 'Please ensure your full body is visible in the frame',
      severity: 'high',
      type: 'form',
      confidence: 1,
      timestamp
    }];
  }

  // Check hip hinge
  const hipHinge = calculateHipHinge(leftShoulder, leftHip, leftKnee);
  if (hipHinge < 0.7) {
    feedback.push({
      message: 'Focus on hinging at your hips',
      severity: 'high',
      type: 'form',
      details: 'Push your hips back while maintaining a straight back',
      confidence: 0.9,
      timestamp
    });
  }

  // Check back angle
  const backAngle = calculateBackAngle(leftShoulder, leftHip);
  if (Math.abs(backAngle) > 20) {
    feedback.push({
      message: 'Keep your back straight',
      severity: 'high',
      type: 'form',
      details: 'Maintain a neutral spine throughout the movement',
      confidence: 0.9,
      timestamp
    });
  }

  // Check bar path
  if (previousKeypoints) {
    const barPath = calculateBarPath(leftHip, previousKeypoints.find(kp => kp.name === 'left_hip')!);
    if (barPath > 0.1) {
      feedback.push({
        message: 'Keep the bar close to your body',
        severity: 'medium',
        type: 'form',
        details: 'The bar should move in a straight vertical line',
        confidence: 0.8,
        timestamp
      });
    }
  }

  return feedback;
}

// Helper functions
function checkKneeAlignment(
  hip: poseDetection.Keypoint,
  knee: poseDetection.Keypoint,
  ankle: poseDetection.Keypoint
): boolean {
  const kneeAngle = Math.atan2(knee.y - ankle.y, knee.x - ankle.x);
  const hipAngle = Math.atan2(hip.y - knee.y, hip.x - knee.x);
  return Math.abs(kneeAngle - hipAngle) < Math.PI / 6; // 30 degrees tolerance
}

function calculateHipDepth(hip: poseDetection.Keypoint, knee: poseDetection.Keypoint): number {
  return Math.abs(hip.y - knee.y) / 100;
}

function calculateBackAngle(shoulder: poseDetection.Keypoint, hip: poseDetection.Keypoint): number {
  return Math.atan2(shoulder.y - hip.y, shoulder.x - hip.x) * 180 / Math.PI;
}

function calculateHipHinge(
  shoulder: poseDetection.Keypoint,
  hip: poseDetection.Keypoint,
  knee: poseDetection.Keypoint
): number {
  const hipToKnee = Math.sqrt(Math.pow(knee.x - hip.x, 2) + Math.pow(knee.y - hip.y, 2));
  const shoulderToHip = Math.sqrt(Math.pow(hip.x - shoulder.x, 2) + Math.pow(hip.y - shoulder.y, 2));
  return hipToKnee / shoulderToHip;
}

function calculateBarPath(
  currentHip: poseDetection.Keypoint,
  previousHip: poseDetection.Keypoint
): number {
  return Math.abs(currentHip.x - previousHip.x);
} 