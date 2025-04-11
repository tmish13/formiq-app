import * as poseDetection from '@tensorflow-models/pose-detection';
import type { 
  JointAngle, 
  BodyAlignment, 
  MovementMetrics, 
  MovementPathway, 
  AlignmentIssue, 
  PathwayDeviation,
  Point
} from './types';
import { Keypoint } from '@tensorflow-models/pose-detection';

interface AngleResult {
  angle: number;
  confidence: number;
}

/**
 * Finds a keypoint by name in the array of keypoints
 */
function findKeypoint(keypoints: poseDetection.Keypoint[], name: string): poseDetection.Keypoint | undefined {
  return keypoints.find(kp => kp.name === name);
}

/**
 * Calculates the raw angle between three points with confidence score
 */
function calculateRawAngle(p1: poseDetection.Keypoint, p2: poseDetection.Keypoint, p3: poseDetection.Keypoint): AngleResult {
  const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
  const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
  
  const dot = v1.x * v2.x + v1.y * v2.y;
  const det = v1.x * v2.y - v1.y * v2.x;
  
  const angle = Math.atan2(det, dot) * (180 / Math.PI);
  const confidence = Math.min(p1.score || 0, p2.score || 0, p3.score || 0);
  
  return { angle, confidence };
}

/**
 * Calculates the angle between three points
 */
function calculateAngle(p1: poseDetection.Keypoint, p2: poseDetection.Keypoint, p3: poseDetection.Keypoint): AngleResult {
  return calculateRawAngle(p1, p2, p3);
}

/**
 * Calculates the distance between two points
 */
function calculateDistance(p1: Point, p2: Point): number {
  return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
}

/**
 * Calculates the distance from a point to a line segment
 */
function calculatePointToLineDistance(point: Point, lineStart: Point, lineEnd: Point): number {
  const A = point.x - lineStart.x;
  const B = point.y - lineStart.y;
  const C = lineEnd.x - lineStart.x;
  const D = lineEnd.y - lineStart.y;

  const dot = A * C + B * D;
  const len_sq = C * C + D * D;

  let param = -1;
  if (len_sq !== 0) {
    param = dot / len_sq;
  }

  let xx, yy;

  if (param < 0) {
    xx = lineStart.x;
    yy = lineStart.y;
  } else if (param > 1) {
    xx = lineEnd.x;
    yy = lineEnd.y;
  } else {
    xx = lineStart.x + param * C;
    yy = lineStart.y + param * D;
  }

  const dx = point.x - xx;
  const dy = point.y - yy;

  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Calculates deviations from the ideal path
 */
function calculatePathDeviations(path: Point[]): PathwayDeviation[] {
  if (path.length < 2) return [];
  
  const deviations: PathwayDeviation[] = [];
  const start = path[0];
  const end = path[path.length - 1];
  
  // Calculate ideal path (straight line from start to end)
  const idealPath = {
    start,
    end,
    length: calculateDistance(start, end)
  };
  
  // Calculate deviations for each point
  for (let i = 1; i < path.length - 1; i++) {
    const point = path[i];
    const deviation = calculatePointToLineDistance(point, start, end);
    
    // Only add deviation if it's significant
    if (deviation > idealPath.length * 0.1) { // 10% of path length threshold
      deviations.push({
        type: 'position',
        severity: deviation / idealPath.length, // Normalize severity
        timestamp: Date.now(),
        description: `Path deviation at point ${i}`
      });
    }
  }
  
  return deviations;
}

/**
 * Calculates path symmetry score
 */
function calculatePathSymmetry(path: Point[]): number {
  if (path.length < 2) return 0;
  
  const midPoint = Math.floor(path.length / 2);
  let totalSymmetry = 0;
  let validPairs = 0;
  
  // Compare points equidistant from the middle
  for (let i = 0; i < midPoint; i++) {
    const leftPoint = path[i];
    const rightPoint = path[path.length - 1 - i];
    
    // Calculate symmetry score for this pair
    const distance = calculateDistance(leftPoint, rightPoint);
    const idealDistance = calculateDistance(path[0], path[path.length - 1]);
    const symmetryScore = 1 - (distance / idealDistance);
    
    totalSymmetry += symmetryScore;
    validPairs++;
  }
  
  return validPairs > 0 ? totalSymmetry / validPairs : 0;
}

/**
 * Calculates path consistency score
 */
function calculatePathConsistency(path: Point[]): number {
  if (path.length < 3) return 0;
  
  let totalDeviation = 0;
  let validSegments = 0;
  
  // Calculate average deviation from straight line segments
  for (let i = 1; i < path.length - 1; i++) {
    const prevPoint = path[i - 1];
    const currentPoint = path[i];
    const nextPoint = path[i + 1];
    
    const deviation = calculatePointToLineDistance(currentPoint, prevPoint, nextPoint);
    totalDeviation += deviation;
    validSegments++;
  }
  
  // Normalize consistency score (higher score means more consistent)
  const avgDeviation = validSegments > 0 ? totalDeviation / validSegments : 0;
  const maxAllowedDeviation = calculateDistance(path[0], path[path.length - 1]) * 0.2; // 20% of total path length
  return Math.max(0, 1 - (avgDeviation / maxAllowedDeviation));
}

/**
 * Calculates body alignment metrics
 */
function calculateBodyAlignment(keypoints: poseDetection.Keypoint[]): BodyAlignment {
  const vertical = calculateVerticalAlignment(keypoints);
  const lateral = calculateLateralAlignment(keypoints);
  const core = calculateCoreStability(keypoints);
  
  const issues: AlignmentIssue[] = [];
  
  if (vertical < 0.8) {
    issues.push({
      type: 'vertical',
      severity: 1 - vertical,
      description: 'Poor vertical alignment detected'
    });
  }
  
  if (lateral < 0.8) {
    issues.push({
      type: 'lateral',
      severity: 1 - lateral,
      description: 'Poor lateral alignment detected'
    });
  }
  
  if (core < 0.8) {
    issues.push({
      type: 'core',
      severity: 1 - core,
      description: 'Core instability detected'
    });
  }
  
  return {
    verticalAlignment: vertical,
    lateralAlignment: lateral,
    coreStability: core,
    issues
  };
}

/**
 * Calculates joint angles for all detected joints
 */
function calculateJointAngles(keypoints: poseDetection.Keypoint[]): Record<string, JointAngle> {
  const angles: Record<string, JointAngle> = {};
  
  // Helper function to safely get keypoint
  const getKeypoint = (index: number): poseDetection.Keypoint | null => {
    const kp = keypoints[index];
    return kp && kp.score && kp.score > 0.5 ? kp : null;
  };
  
  // Calculate angles for each joint
  for (let i = 0; i < keypoints.length; i++) {
    const current = getKeypoint(i);
    if (!current) continue;
    
    const prev = i > 0 ? getKeypoint(i - 1) : null;
    const next = i < keypoints.length - 1 ? getKeypoint(i + 1) : null;
    
    if (prev && next) {
      const angleResult = calculateRawAngle(prev, current, next);
      angles[`joint_${i}`] = {
        angle: angleResult.angle,
        confidence: angleResult.confidence,
        isCorrect: Math.abs(angleResult.angle - 0) < 10
      };
    }
  }
  
  return angles;
}

/**
 * Calculates vertical alignment score
 */
function calculateVerticalAlignment(keypoints: poseDetection.Keypoint[]): number {
  const validKeypoints = keypoints.filter(kp => kp.score && kp.score > 0.5);
  if (validKeypoints.length < 2) return 0;

  // Calculate average x-coordinate
  const avgX = validKeypoints.reduce((sum, kp) => sum + kp.x, 0) / validKeypoints.length;
  
  // Calculate deviation from vertical line
  const maxDeviation = Math.max(...validKeypoints.map(kp => Math.abs(kp.x - avgX)));
  const normalizedDeviation = maxDeviation / (Math.max(...validKeypoints.map(kp => kp.x)) - Math.min(...validKeypoints.map(kp => kp.x)));
  
  return Math.max(0, 1 - normalizedDeviation);
}

/**
 * Calculates lateral alignment score
 */
function calculateLateralAlignment(keypoints: poseDetection.Keypoint[]): number {
  const validKeypoints = keypoints.filter(kp => kp.score && kp.score > 0.5);
  if (validKeypoints.length < 2) return 0;

  // Calculate average y-coordinate
  const avgY = validKeypoints.reduce((sum, kp) => sum + kp.y, 0) / validKeypoints.length;
  
  // Calculate deviation from horizontal line
  const maxDeviation = Math.max(...validKeypoints.map(kp => Math.abs(kp.y - avgY)));
  const normalizedDeviation = maxDeviation / (Math.max(...validKeypoints.map(kp => kp.y)) - Math.min(...validKeypoints.map(kp => kp.y)));
  
  return Math.max(0, 1 - normalizedDeviation);
}

/**
 * Calculates core stability score
 */
function calculateCoreStability(keypoints: poseDetection.Keypoint[]): number {
  const hipLeft = keypoints.find(kp => kp.name === 'left_hip');
  const hipRight = keypoints.find(kp => kp.name === 'right_hip');
  const shoulderLeft = keypoints.find(kp => kp.name === 'left_shoulder');
  const shoulderRight = keypoints.find(kp => kp.name === 'right_shoulder');

  if (!hipLeft?.score || !hipRight?.score || !shoulderLeft?.score || !shoulderRight?.score) {
    return 0;
  }

  // Calculate torso angle
  const torsoMidpointTop = {
    x: (shoulderLeft.x + shoulderRight.x) / 2,
    y: (shoulderLeft.y + shoulderRight.y) / 2
  };

  const torsoMidpointBottom = {
    x: (hipLeft.x + hipRight.x) / 2,
    y: (hipLeft.y + hipRight.y) / 2
  };

  const torsoAngle = Math.abs(Math.atan2(
    torsoMidpointTop.y - torsoMidpointBottom.y,
    torsoMidpointTop.x - torsoMidpointBottom.x
  ) * (180 / Math.PI));

  // Calculate hip stability
  const hipWidth = calculateDistance(hipLeft, hipRight);
  const shoulderWidth = calculateDistance(shoulderLeft, shoulderRight);
  const hipStability = Math.min(hipWidth / shoulderWidth, shoulderWidth / hipWidth);

  // Combine scores
  const angleScore = Math.max(0, 1 - Math.abs(90 - torsoAngle) / 90);
  const stabilityScore = Math.max(0, hipStability);

  return (angleScore + stabilityScore) / 2;
}

/**
 * Calculates overall confidence score for keypoints
 */
function calculateConfidenceScore(keypoints: poseDetection.Keypoint[]): number {
  if (!keypoints.length) return 0;
  
  // Calculate average confidence score
  const totalConfidence = keypoints.reduce((sum, kp) => sum + (kp.score || 0), 0);
  return totalConfidence / keypoints.length;
}

export function isMobileDevice(): boolean {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

export function calculateConfidenceScore(keypoints: Keypoint[]): number {
  const visibleKeypoints = keypoints.filter(kp => kp.score && kp.score > 0.3);
  if (!visibleKeypoints.length) return 0;

  const avgConfidence = visibleKeypoints.reduce((sum, kp) => sum + (kp.score || 0), 0) / visibleKeypoints.length;
  const coverageScore = visibleKeypoints.length / keypoints.length;

  return avgConfidence * coverageScore;
}

export function calculateJointAngles(keypoints: Keypoint[]): JointAngle[] {
  const angles: JointAngle[] = [];

  // Calculate knee angles
  const leftKneeAngle = calculateAngle(
    findKeypoint(keypoints, 'left_hip'),
    findKeypoint(keypoints, 'left_knee'),
    findKeypoint(keypoints, 'left_ankle')
  );
  if (leftKneeAngle) {
    angles.push({
      joint: 'left_knee',
      angle: leftKneeAngle.angle,
      confidence: leftKneeAngle.confidence
    });
  }

  const rightKneeAngle = calculateAngle(
    findKeypoint(keypoints, 'right_hip'),
    findKeypoint(keypoints, 'right_knee'),
    findKeypoint(keypoints, 'right_ankle')
  );
  if (rightKneeAngle) {
    angles.push({
      joint: 'right_knee',
      angle: rightKneeAngle.angle,
      confidence: rightKneeAngle.confidence
    });
  }

  // Calculate hip angles
  const leftHipAngle = calculateAngle(
    findKeypoint(keypoints, 'left_shoulder'),
    findKeypoint(keypoints, 'left_hip'),
    findKeypoint(keypoints, 'left_knee')
  );
  if (leftHipAngle) {
    angles.push({
      joint: 'left_hip',
      angle: leftHipAngle.angle,
      confidence: leftHipAngle.confidence
    });
  }

  const rightHipAngle = calculateAngle(
    findKeypoint(keypoints, 'right_shoulder'),
    findKeypoint(keypoints, 'right_hip'),
    findKeypoint(keypoints, 'right_knee')
  );
  if (rightHipAngle) {
    angles.push({
      joint: 'right_hip',
      angle: rightHipAngle.angle,
      confidence: rightHipAngle.confidence
    });
  }

  // Calculate elbow angles
  const leftElbowAngle = calculateAngle(
    findKeypoint(keypoints, 'left_shoulder'),
    findKeypoint(keypoints, 'left_elbow'),
    findKeypoint(keypoints, 'left_wrist')
  );
  if (leftElbowAngle) {
    angles.push({
      joint: 'left_elbow',
      angle: leftElbowAngle.angle,
      confidence: leftElbowAngle.confidence
    });
  }

  const rightElbowAngle = calculateAngle(
    findKeypoint(keypoints, 'right_shoulder'),
    findKeypoint(keypoints, 'right_elbow'),
    findKeypoint(keypoints, 'right_wrist')
  );
  if (rightElbowAngle) {
    angles.push({
      joint: 'right_elbow',
      angle: rightElbowAngle.angle,
      confidence: rightElbowAngle.confidence
    });
  }

  // Calculate shoulder angles
  const leftShoulderAngle = calculateAngle(
    findKeypoint(keypoints, 'left_hip'),
    findKeypoint(keypoints, 'left_shoulder'),
    findKeypoint(keypoints, 'left_elbow')
  );
  if (leftShoulderAngle) {
    angles.push({
      joint: 'left_shoulder',
      angle: leftShoulderAngle.angle,
      confidence: leftShoulderAngle.confidence
    });
  }

  const rightShoulderAngle = calculateAngle(
    findKeypoint(keypoints, 'right_hip'),
    findKeypoint(keypoints, 'right_shoulder'),
    findKeypoint(keypoints, 'right_elbow')
  );
  if (rightShoulderAngle) {
    angles.push({
      joint: 'right_shoulder',
      angle: rightShoulderAngle.angle,
      confidence: rightShoulderAngle.confidence
    });
  }

  return angles;
}

export function calculateMovementMetrics(
  currentKeypoints: Keypoint[],
  previousKeypoints: Keypoint[]
): MovementMetrics {
  if (!previousKeypoints.length) {
    return {
      velocity: 0,
      acceleration: 0,
      jerk: 0,
      smoothness: 1
    };
  }

  const currentCenter = calculateCenterOfMass(currentKeypoints);
  const previousCenter = calculateCenterOfMass(previousKeypoints);
  const timeStep = 1/30; // Assuming 30 FPS

  const velocity = calculateVelocity(currentCenter, previousCenter, timeStep);
  const acceleration = calculateAcceleration(velocity, timeStep);
  const jerk = calculateJerk(acceleration, timeStep);
  const smoothness = calculateSmoothness(velocity, acceleration, jerk);

  return {
    velocity,
    acceleration,
    jerk,
    smoothness
  };
}

function calculateCenterOfMass(keypoints: Keypoint[]): Point {
  const validPoints = keypoints.filter(kp => kp.score && kp.score > 0.3);
  if (!validPoints.length) {
    return { x: 0, y: 0 };
  }

  const sumX = validPoints.reduce((sum, kp) => sum + kp.x, 0);
  const sumY = validPoints.reduce((sum, kp) => sum + kp.y, 0);

  return {
    x: sumX / validPoints.length,
    y: sumY / validPoints.length
  };
}

function calculateVelocity(current: Point, previous: Point, timeStep: number): number {
  const dx = current.x - previous.x;
  const dy = current.y - previous.y;
  return Math.sqrt(dx * dx + dy * dy) / timeStep;
}

function calculateAcceleration(velocity: number, timeStep: number): number {
  return velocity / timeStep;
}

function calculateJerk(acceleration: number, timeStep: number): number {
  return acceleration / timeStep;
}

function calculateSmoothness(velocity: number, acceleration: number, jerk: number): number {
  const maxVelocity = 10; // Normalized maximum velocity
  const maxAcceleration = 5; // Normalized maximum acceleration
  const maxJerk = 2; // Normalized maximum jerk

  const velocityScore = 1 - (velocity / maxVelocity);
  const accelerationScore = 1 - (acceleration / maxAcceleration);
  const jerkScore = 1 - (jerk / maxJerk);

  return (velocityScore + accelerationScore + jerkScore) / 3;
}

export {
  findKeypoint,
  calculateAngle,
  calculateRawAngle,
  calculatePathDeviations,
  calculatePathSymmetry,
  calculatePathConsistency,
  calculateBodyAlignment,
  calculateJointAngles,
  calculatePointToLineDistance,
  calculateDistance,
  calculateCoreStability,
  calculateVerticalAlignment,
  calculateLateralAlignment,
  calculateConfidenceScore
};