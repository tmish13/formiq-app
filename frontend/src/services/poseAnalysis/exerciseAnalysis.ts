import * as poseDetection from '@tensorflow-models/pose-detection';
import { ExerciseType, FeedbackItem } from '../poseAnalysisService';
import { calculateDistance, calculatePointToLineDistance } from './utils';

interface ExerciseConfig {
  targetAngles: Record<string, { angle: number; tolerance: number }>;
  keyPoints: string[];
  movementPhases: string[];
  safetyChecks: string[];
}

interface AngleResult {
  angle: number;
  confidence: number;
}

function calculateAngle(p1: poseDetection.Keypoint, p2: poseDetection.Keypoint, p3: poseDetection.Keypoint): AngleResult {
  const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
  const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
  
  const dot = v1.x * v2.x + v1.y * v2.y;
  const det = v1.x * v2.y - v1.y * v2.x;
  
  const angle = Math.atan2(det, dot) * (180 / Math.PI);
  const confidence = Math.min(p1.score || 0, p2.score || 0, p3.score || 0);
  
  return { angle, confidence };
}

const EXERCISE_CONFIGS: Record<ExerciseType, ExerciseConfig> = {
  squat: {
    targetAngles: {
      knee: { angle: 90, tolerance: 15 },
      hip: { angle: 90, tolerance: 15 },
      ankle: { angle: 70, tolerance: 15 }
    },
    keyPoints: ['left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle'],
    movementPhases: ['descent', 'bottom', 'ascent'],
    safetyChecks: ['knee_alignment', 'spine_alignment', 'depth']
  },
  pushup: {
    targetAngles: {
      elbow: { angle: 90, tolerance: 15 },
      shoulder: { angle: 0, tolerance: 15 }
    },
    keyPoints: ['left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist'],
    movementPhases: ['descent', 'bottom', 'ascent'],
    safetyChecks: ['elbow_alignment', 'spine_alignment', 'depth']
  },
  plank: {
    targetAngles: {
      elbow: { angle: 90, tolerance: 15 },
      shoulder: { angle: 0, tolerance: 15 },
      hip: { angle: 0, tolerance: 15 }
    },
    keyPoints: ['left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow', 'left_hip', 'right_hip'],
    movementPhases: ['hold'],
    safetyChecks: ['spine_alignment', 'hip_alignment', 'duration']
  },
  lunges: {
    targetAngles: {
      frontKnee: { angle: 90, tolerance: 15 },
      backKnee: { angle: 90, tolerance: 15 },
      hip: { angle: 0, tolerance: 15 }
    },
    keyPoints: ['left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle'],
    movementPhases: ['descent', 'bottom', 'ascent'],
    safetyChecks: ['knee_alignment', 'spine_alignment', 'depth']
  },
  deadlift: {
    targetAngles: {
      hip: { angle: 0, tolerance: 15 },
      knee: { angle: 20, tolerance: 15 },
      spine: { angle: 0, tolerance: 15 }
    },
    keyPoints: ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip', 'left_knee', 'right_knee'],
    movementPhases: ['setup', 'lift', 'lower'],
    safetyChecks: ['spine_alignment', 'hip_hinge', 'bar_path']
  },
  burpees: {
    targetAngles: {
      squat: { angle: 90, tolerance: 15 },
      pushup: { angle: 90, tolerance: 15 }
    },
    keyPoints: ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip', 'left_knee', 'right_knee'],
    movementPhases: ['squat', 'pushup', 'jump'],
    safetyChecks: ['landing', 'spine_alignment', 'rhythm']
  },
  mountain_climbers: {
    targetAngles: {
      hip: { angle: 0, tolerance: 15 },
      knee: { angle: 90, tolerance: 15 }
    },
    keyPoints: ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip', 'left_knee', 'right_knee'],
    movementPhases: ['alternate', 'rhythm'],
    safetyChecks: ['spine_alignment', 'hip_stability', 'rhythm']
  }
};

export function analyzeExerciseForm(
  exerciseType: ExerciseType,
  keypoints: poseDetection.Keypoint[],
  previousKeypoints?: poseDetection.Keypoint[]
): FeedbackItem[] {
  const config = EXERCISE_CONFIGS[exerciseType];
  const feedback: FeedbackItem[] = [];

  // Check if all required keypoints are present
  const missingKeypoints = config.keyPoints.filter(
    kp => !keypoints.find(k => k.name === kp && k.score && k.score > 0.5)
  );

  if (missingKeypoints.length > 0) {
    feedback.push({
      text: `Missing keypoints: ${missingKeypoints.join(', ')}`,
      severity: 'high',
      type: 'form',
      details: 'Some body parts are not visible in the frame',
      confidence: 1,
      timestamp: Date.now()
    });
    return feedback;
  }

  // Exercise-specific analysis
  switch (exerciseType) {
    case 'squat':
      feedback.push(...analyzeSquatForm(keypoints, config));
      break;
    case 'pushup':
      feedback.push(...analyzePushupForm(keypoints, config));
      break;
    case 'plank':
      feedback.push(...analyzePlankForm(keypoints, config));
      break;
    case 'lunges':
      feedback.push(...analyzeLungeForm(keypoints, config));
      break;
    case 'deadlift':
      feedback.push(...analyzeDeadliftForm(keypoints, config));
      break;
    case 'burpees':
      feedback.push(...analyzeBurpeeForm(keypoints, config));
      break;
    case 'mountain_climbers':
      feedback.push(...analyzeMountainClimberForm(keypoints, config));
      break;
  }

  // Add movement phase analysis if previous keypoints are available
  if (previousKeypoints) {
    const phaseFeedback = analyzeMovementPhase(exerciseType, keypoints, previousKeypoints, config);
    feedback.push(...phaseFeedback);
  }

  return feedback;
}

function analyzeSquatForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftHip = keypoints.find(kp => kp.name === 'left_hip')!;
  const rightHip = keypoints.find(kp => kp.name === 'right_hip')!;
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee')!;
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee')!;
  const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle')!;
  const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle')!;

  // Check knee alignment
  const leftKneeAngle = calculateAngle(leftHip, leftKnee, leftAnkle).angle;
  const rightKneeAngle = calculateAngle(rightHip, rightKnee, rightAnkle).angle;
  
  if (Math.abs(leftKneeAngle - rightKneeAngle) > 10) {
    feedback.push({
      text: 'Knees are not aligned evenly',
      severity: 'medium',
      type: 'alignment',
      details: 'Try to keep both knees at the same angle',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  // Check depth
  const hipAngle = calculateAngle(leftHip, rightHip, leftKnee).angle;
  if (hipAngle < config.targetAngles.hip.angle - config.targetAngles.hip.tolerance) {
    feedback.push({
      text: 'Squat depth is too low',
      severity: 'medium',
      type: 'range',
      details: 'Try to maintain proper depth without going too low',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  // Check spine alignment
  const spineAlignment = calculateSpineAlignment(keypoints);
  if (spineAlignment < 0.8) {
    feedback.push({
      text: 'Keep your back straight',
      severity: 'high',
      type: 'alignment',
      details: 'Maintain a neutral spine position throughout the movement',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function analyzePushupForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder')!;
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder')!;
  const leftElbow = keypoints.find(kp => kp.name === 'left_elbow')!;
  const rightElbow = keypoints.find(kp => kp.name === 'right_elbow')!;
  const leftWrist = keypoints.find(kp => kp.name === 'left_wrist')!;
  const rightWrist = keypoints.find(kp => kp.name === 'right_wrist')!;

  // Check elbow angles
  const leftElbowAngle = calculateAngle(leftShoulder, leftElbow, leftWrist).angle;
  const rightElbowAngle = calculateAngle(rightShoulder, rightElbow, rightWrist).angle;
  
  if (Math.abs(leftElbowAngle - rightElbowAngle) > 10) {
    feedback.push({
      text: 'Arms are not evenly bent',
      severity: 'medium',
      type: 'alignment',
      details: 'Try to keep both arms at the same angle',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  // Check depth
  if (leftElbowAngle < config.targetAngles.elbow.angle - config.targetAngles.elbow.tolerance) {
    feedback.push({
      text: 'Pushup depth is too low',
      severity: 'medium',
      type: 'range',
      details: 'Try to maintain proper depth without going too low',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  // Check spine alignment
  const spineAlignment = calculateSpineAlignment(keypoints);
  if (spineAlignment < 0.8) {
    feedback.push({
      text: 'Keep your body straight',
      severity: 'high',
      type: 'alignment',
      details: 'Maintain a straight line from head to heels',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function analyzePlankForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder')!;
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder')!;
  const leftElbow = keypoints.find(kp => kp.name === 'left_elbow')!;
  const rightElbow = keypoints.find(kp => kp.name === 'right_elbow')!;
  const leftHip = keypoints.find(kp => kp.name === 'left_hip')!;
  const rightHip = keypoints.find(kp => kp.name === 'right_hip')!;

  // Check spine alignment
  const spineAlignment = calculateSpineAlignment(keypoints);
  if (spineAlignment < 0.9) {
    feedback.push({
      text: 'Keep your body in a straight line',
      severity: 'high',
      type: 'alignment',
      details: 'Maintain a neutral spine position',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  // Check hip position
  const hipAngle = calculateAngle(leftShoulder, leftHip, leftElbow).angle;
  if (Math.abs(hipAngle - config.targetAngles.hip.angle) > config.targetAngles.hip.tolerance) {
    feedback.push({
      text: 'Hips are too high or too low',
      severity: 'medium',
      type: 'alignment',
      details: 'Try to keep your hips level with your shoulders',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function analyzeLungeForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftHip = keypoints.find(kp => kp.name === 'left_hip')!;
  const rightHip = keypoints.find(kp => kp.name === 'right_hip')!;
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee')!;
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee')!;
  const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle')!;
  const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle')!;

  // Check front knee angle
  const frontKneeAngle = calculateAngle(leftHip, leftKnee, leftAnkle).angle;
  if (Math.abs(frontKneeAngle - config.targetAngles.frontKnee.angle) > config.targetAngles.frontKnee.tolerance) {
    feedback.push({
      text: 'Front knee angle needs adjustment',
      severity: 'medium',
      type: 'range',
      details: 'Try to get your front knee to 90 degrees',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  // Check back knee position
  const backKneeAngle = calculateAngle(rightHip, rightKnee, rightAnkle).angle;
  if (backKneeAngle < 80) {
    feedback.push({
      text: 'Back knee is too low',
      severity: 'medium',
      type: 'range',
      details: 'Keep your back knee slightly above the ground',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  // Check vertical alignment
  const spineAlignment = calculateSpineAlignment(keypoints);
  if (spineAlignment < 0.8) {
    feedback.push({
      text: 'Keep your torso upright',
      severity: 'high',
      type: 'alignment',
      details: 'Maintain an upright posture throughout the movement',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function analyzeDeadliftForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder')!;
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder')!;
  const leftHip = keypoints.find(kp => kp.name === 'left_hip')!;
  const rightHip = keypoints.find(kp => kp.name === 'right_hip')!;
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee')!;
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee')!;

  // Check hip hinge
  const hipAngle = calculateAngle(leftShoulder, leftHip, leftKnee).angle;
  if (Math.abs(hipAngle - config.targetAngles.hip.angle) > config.targetAngles.hip.tolerance) {
    feedback.push({
      text: 'Improve hip hinge',
      severity: 'high',
      type: 'form',
      details: 'Hinge at the hips while maintaining a neutral spine',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  // Check spine alignment
  const spineAlignment = calculateSpineAlignment(keypoints);
  if (spineAlignment < 0.8) {
    feedback.push({
      text: 'Keep your back straight',
      severity: 'high',
      type: 'alignment',
      details: 'Maintain a neutral spine position throughout the movement',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function analyzeBurpeeForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder')!;
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder')!;
  const leftHip = keypoints.find(kp => kp.name === 'left_hip')!;
  const rightHip = keypoints.find(kp => kp.name === 'right_hip')!;
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee')!;
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee')!;
  const leftElbow = keypoints.find(kp => kp.name === 'left_elbow')!;
  const rightElbow = keypoints.find(kp => kp.name === 'right_elbow')!;
  const leftWrist = keypoints.find(kp => kp.name === 'left_wrist')!;
  const rightWrist = keypoints.find(kp => kp.name === 'right_wrist')!;

  // Check squat form
  const hipAngle = calculateAngle(leftHip, rightHip, leftKnee).angle;
  if (Math.abs(hipAngle - config.targetAngles.squat.angle) > config.targetAngles.squat.tolerance) {
    feedback.push({
      text: 'Improve squat form',
      severity: 'medium',
      type: 'form',
      details: 'Get proper depth in the squat position',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  // Check pushup form
  const pushupAngle = calculateAngle(leftShoulder, leftElbow, leftWrist).angle;
  if (Math.abs(pushupAngle - config.targetAngles.pushup.angle) > config.targetAngles.pushup.tolerance) {
    feedback.push({
      text: 'Improve pushup form',
      severity: 'medium',
      type: 'form',
      details: 'Maintain proper pushup form during the burpee',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function analyzeMountainClimberForm(keypoints: poseDetection.Keypoint[], config: ExerciseConfig): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Get key points
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder')!;
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder')!;
  const leftHip = keypoints.find(kp => kp.name === 'left_hip')!;
  const rightHip = keypoints.find(kp => kp.name === 'right_hip')!;
  const leftKnee = keypoints.find(kp => kp.name === 'left_knee')!;
  const rightKnee = keypoints.find(kp => kp.name === 'right_knee')!;

  // Check plank position
  const spineAlignment = calculateSpineAlignment(keypoints);
  if (spineAlignment < 0.8) {
    feedback.push({
      text: 'Maintain plank position',
      severity: 'high',
      type: 'alignment',
      details: 'Keep your body in a straight line throughout the movement',
      confidence: 0.9,
      timestamp: Date.now()
    });
  }

  // Check hip stability
  const hipAngle = calculateAngle(leftShoulder, leftHip, leftKnee).angle;
  if (Math.abs(hipAngle - config.targetAngles.hip.angle) > config.targetAngles.hip.tolerance) {
    feedback.push({
      text: 'Control hip movement',
      severity: 'medium',
      type: 'form',
      details: 'Keep your hips stable while alternating legs',
      confidence: 0.8,
      timestamp: Date.now()
    });
  }

  return feedback;
}

function calculateSpineAlignment(keypoints: poseDetection.Keypoint[]): number {
  const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
  const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
  const leftHip = keypoints.find(kp => kp.name === 'left_hip');
  const rightHip = keypoints.find(kp => kp.name === 'right_hip');

  if (!leftShoulder || !rightShoulder || !leftHip || !rightHip) {
    return 0;
  }

  const shoulderMid = {
    x: (leftShoulder.x + rightShoulder.x) / 2,
    y: (leftShoulder.y + rightShoulder.y) / 2
  };

  const hipMid = {
    x: (leftHip.x + rightHip.x) / 2,
    y: (leftHip.y + rightHip.y) / 2
  };

  const dx = shoulderMid.x - hipMid.x;
  const dy = shoulderMid.y - hipMid.y;
  const angle = Math.abs(Math.atan2(dx, dy) * (180 / Math.PI));

  return Math.max(0, 1 - (angle / 45)); // 45 degrees is considered poor alignment
}

function analyzeMovementPhase(
  exerciseType: ExerciseType,
  currentKeypoints: poseDetection.Keypoint[],
  previousKeypoints: poseDetection.Keypoint[],
  config: ExerciseConfig
): FeedbackItem[] {
  const feedback: FeedbackItem[] = [];
  
  // Calculate movement velocity and acceleration
  const velocity = calculateMovementVelocity(currentKeypoints, previousKeypoints);
  const acceleration = calculateMovementAcceleration(velocity, config);
  
  // Analyze movement phase based on exercise type
  switch (exerciseType) {
    case 'squat':
      if (velocity < -0.5) {
        feedback.push({
          text: 'Control your descent',
          severity: 'medium',
          type: 'tempo',
          details: 'Try to lower yourself more slowly and with control',
          confidence: 0.8,
          timestamp: Date.now()
        });
      }
      break;
    // Add phase analysis for other exercises...
  }
  
  return feedback;
}

function calculateMovementVelocity(
  current: poseDetection.Keypoint[],
  previous: poseDetection.Keypoint[]
): number {
  let totalVelocity = 0;
  let validPoints = 0;
  
  current.forEach((kp, i) => {
    if (previous[i] && kp.score && kp.score > 0.5) {
      const dx = kp.x - previous[i].x;
      const dy = kp.y - previous[i].y;
      totalVelocity += Math.sqrt(dx * dx + dy * dy);
      validPoints++;
    }
  });
  
  return validPoints > 0 ? totalVelocity / validPoints : 0;
}

function calculateMovementAcceleration(velocity: number, config: ExerciseConfig): number {
  // Implementation of acceleration calculation
  return 0; // Placeholder
} 