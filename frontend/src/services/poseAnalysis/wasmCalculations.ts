import { Keypoint } from '@tensorflow-models/pose-detection';
import { JointAngle } from './types';

// WebAssembly module interface
interface WasmModule {
  calculateAngles: (points: Float32Array) => Float32Array;
  calculateVelocities: (currentPoints: Float32Array, previousPoints: Float32Array) => Float32Array;
  calculateConfidence: (scores: Float32Array) => number;
  calculateSmoothness: (velocities: Float32Array) => number;
  calculateCenterOfMass: (points: Float32Array) => Float32Array;
}

let wasmModule: WasmModule | null = null;

export async function initializeWasm(): Promise<void> {
  try {
    const response = await fetch('/wasm/pose_calculations.wasm');
    const wasmBytes = await response.arrayBuffer();
    const wasmObj = await WebAssembly.instantiate(wasmBytes, {
      env: {
        memory: new WebAssembly.Memory({ initial: 256 }),
        abort: () => console.error('Wasm aborted')
      }
    });

    wasmModule = wasmObj.instance.exports as unknown as WasmModule;
  } catch (error) {
    console.error('Failed to initialize WebAssembly module:', error);
  }
}

export function calculateJointAnglesWasm(keypoints: Keypoint[]): JointAngle[] {
  if (!wasmModule) {
    throw new Error('WebAssembly module not initialized');
  }

  const points = new Float32Array(keypoints.length * 3);
  keypoints.forEach((kp, i) => {
    points[i * 3] = kp.x;
    points[i * 3 + 1] = kp.y;
    points[i * 3 + 2] = kp.score || 0;
  });

  const angles = wasmModule.calculateAngles(points);
  const result: JointAngle[] = [];

  for (let i = 0; i < angles.length; i += 2) {
    result.push({
      joint: getJointName(i / 2),
      angle: angles[i],
      confidence: angles[i + 1]
    });
  }

  return result;
}

export function calculateMovementMetricsWasm(
  currentKeypoints: Keypoint[],
  previousKeypoints: Keypoint[]
): { velocity: number; acceleration: number; jerk: number; smoothness: number } {
  if (!wasmModule) {
    throw new Error('WebAssembly module not initialized');
  }

  const currentPoints = new Float32Array(currentKeypoints.length * 3);
  const previousPoints = new Float32Array(previousKeypoints.length * 3);

  currentKeypoints.forEach((kp, i) => {
    currentPoints[i * 3] = kp.x;
    currentPoints[i * 3 + 1] = kp.y;
    currentPoints[i * 3 + 2] = kp.score || 0;
  });

  previousKeypoints.forEach((kp, i) => {
    previousPoints[i * 3] = kp.x;
    previousPoints[i * 3 + 1] = kp.y;
    previousPoints[i * 3 + 2] = kp.score || 0;
  });

  const velocities = wasmModule.calculateVelocities(currentPoints, previousPoints);
  const smoothness = wasmModule.calculateSmoothness(velocities);

  return {
    velocity: velocities[0],
    acceleration: velocities[1],
    jerk: velocities[2],
    smoothness
  };
}

export function calculateConfidenceScoreWasm(keypoints: Keypoint[]): number {
  if (!wasmModule) {
    throw new Error('WebAssembly module not initialized');
  }

  const scores = new Float32Array(keypoints.map(kp => kp.score || 0));
  return wasmModule.calculateConfidence(scores);
}

export function calculateCenterOfMassWasm(keypoints: Keypoint[]): { x: number; y: number } {
  if (!wasmModule) {
    throw new Error('WebAssembly module not initialized');
  }

  const points = new Float32Array(keypoints.length * 3);
  keypoints.forEach((kp, i) => {
    points[i * 3] = kp.x;
    points[i * 3 + 1] = kp.y;
    points[i * 3 + 2] = kp.score || 0;
  });

  const result = wasmModule.calculateCenterOfMass(points);
  return { x: result[0], y: result[1] };
}

function getJointName(index: number): string {
  const joints = [
    'left_knee',
    'right_knee',
    'left_hip',
    'right_hip',
    'left_elbow',
    'right_elbow',
    'left_shoulder',
    'right_shoulder'
  ];
  return joints[index] || 'unknown';
} 