import * as poseDetection from '@tensorflow-models/pose-detection';
import {
  findKeypoint,
  calculateAngle,
  calculateRawAngle,
  calculatePathDeviations,
  calculateBodyAlignment,
  calculateJointAngles,
  calculatePointToLineDistance,
  calculateDistance,
  calculateCoreStability,
  calculateVerticalAlignment,
  calculateLateralAlignment,
  calculateConfidenceScore
} from '../utils';
import { Point } from '../types';

// Mock keypoints for testing
const createKeypoint = (name: string, x: number, y: number, score: number = 1): poseDetection.Keypoint => ({
  name,
  x,
  y,
  score
});

// Create a complete set of keypoints for body alignment calculations
const createCompleteKeypoints = () => {
  return [
    createKeypoint('nose', 150, 50),
    createKeypoint('left_shoulder', 100, 100),
    createKeypoint('right_shoulder', 200, 100),
    createKeypoint('left_hip', 100, 200),
    createKeypoint('right_hip', 200, 200),
    createKeypoint('left_knee', 100, 300),
    createKeypoint('right_knee', 200, 300),
    createKeypoint('left_ankle', 100, 400),
    createKeypoint('right_ankle', 200, 400),
    createKeypoint('joint_0', 0, 0),
    createKeypoint('joint_1', 50, 50),
    createKeypoint('joint_2', 100, 0),
  ];
};

describe('Pose Analysis Utils', () => {
  describe('findKeypoint', () => {
    it('should find a keypoint by name', () => {
      const keypoints = [
        createKeypoint('left_shoulder', 100, 100),
        createKeypoint('right_shoulder', 200, 100),
        createKeypoint('left_hip', 100, 200),
        createKeypoint('right_hip', 200, 200)
      ];
      
      const result = findKeypoint(keypoints, 'left_shoulder');
      expect(result).toBeDefined();
      expect(result?.name).toBe('left_shoulder');
      expect(result?.x).toBe(100);
      expect(result?.y).toBe(100);
    });
    
    it('should return undefined for non-existent keypoint', () => {
      const keypoints = [
        createKeypoint('left_shoulder', 100, 100),
        createKeypoint('right_shoulder', 200, 100)
      ];
      
      const result = findKeypoint(keypoints, 'left_hip');
      expect(result).toBeUndefined();
    });
  });
  
  describe('calculateRawAngle', () => {
    it('should calculate angle between three points', () => {
      // Create a right angle (90 degrees / 2 = 45 degrees)
      const p1 = createKeypoint('p1', 0, 0);
      const p2 = createKeypoint('p2', 50, 50); // Center point
      const p3 = createKeypoint('p3', 100, 50);
      
      const result = calculateRawAngle(p1, p2, p3);
      expect(result.angle).toBeCloseTo(45, 1);
      expect(result.confidence).toBe(1);
    });
    
    it('should handle points with different confidence scores', () => {
      const p1 = createKeypoint('p1', 0, 0, 0.8);
      const p2 = createKeypoint('p2', 0, 0, 0.9);
      const p3 = createKeypoint('p3', 1, 1, 0.7);
      
      const result = calculateRawAngle(p1, p2, p3);
      expect(result.confidence).toBe(0.7); // Should use the minimum confidence
    });
  });
  
  describe('calculateAngle', () => {
    it('should return the angle from calculateRawAngle', () => {
      // Create a right angle (90 degrees / 2 = 45 degrees)
      const p1 = createKeypoint('p1', 0, 0);
      const p2 = createKeypoint('p2', 50, 50); // Center point
      const p3 = createKeypoint('p3', 100, 50);
      
      const result = calculateAngle(p1, p2, p3);
      expect(result.angle).toBeCloseTo(45, 1);
      expect(result.confidence).toBe(1);
    });
  });
  
  describe('calculatePathDeviations', () => {
    it('should return empty array for path with less than 2 points', () => {
      const path: Point[] = [{ x: 0, y: 0 }];
      const result = calculatePathDeviations(path);
      expect(result).toEqual([]);
    });
    
    it('should calculate deviations for a path', () => {
      const path: Point[] = [
        { x: 0, y: 0 },
        { x: 1, y: 2 }, // Deviation from straight line
        { x: 2, y: 0 }
      ];
      
      const result = calculatePathDeviations(path);
      expect(result.length).toBe(1);
      expect(result[0].type).toBe('position');
      // Check severity is either 'error' or 'warning' string, not a number
      expect(['error', 'warning']).toContain(result[0].severity);
    });
  });
  
  describe('calculateBodyAlignment', () => {
    it('should calculate body alignment with all metrics', () => {
      const keypoints = createCompleteKeypoints();
      
      const result = calculateBodyAlignment(keypoints);
      expect(result.verticalAlignment).toBeGreaterThan(0);
      expect(result.lateralAlignment).toBeGreaterThan(0);
      expect(result.coreStability).toBeGreaterThan(0);
      expect(Array.isArray(result.issues)).toBe(true);
    });
    
    it('should handle missing keypoints', () => {
      const keypoints = [
        createKeypoint('left_shoulder', 100, 100),
        createKeypoint('right_shoulder', 200, 100)
      ];
      
      const result = calculateBodyAlignment(keypoints);
      expect(result.verticalAlignment).toBe(0);
      expect(result.lateralAlignment).toBe(0);
      expect(result.coreStability).toBe(0);
    });
  });
  
  describe('calculateJointAngles', () => {
    it('should calculate angles for joints', () => {
      // Include joint_1 name explicitly for the test
      const keypoints = [
        createKeypoint('joint_0', 0, 0),
        createKeypoint('joint_1', 50, 50),
        createKeypoint('joint_2', 100, 50)
      ];
      
      const result = calculateJointAngles(keypoints);
      expect(Object.keys(result).length).toBeGreaterThan(0);
      expect(result['joint_1']).toBeDefined();
      expect(result['joint_1'].angle).toBeCloseTo(45, 1);
    });
    
    it('should handle low confidence keypoints', () => {
      const keypoints = [
        createKeypoint('joint_0', 0, 0, 0.3), // Low confidence
        createKeypoint('joint_1', 0, 0),
        createKeypoint('joint_2', 1, 1)
      ];
      
      // Log keypoints details for debugging
      console.log('Low confidence keypoints test: ', JSON.stringify(keypoints));
      
      const result = calculateJointAngles(keypoints);
      // We're expecting an empty object back
      expect(Object.keys(result).length).toBe(0); // Should skip low confidence keypoints
    });
  });
  
  describe('calculatePointToLineDistance', () => {
    it('should calculate distance from point to line', () => {
      const point: Point = { x: 1, y: 1 };
      const lineStart: Point = { x: 0, y: 0 };
      const lineEnd: Point = { x: 2, y: 0 };
      
      const result = calculatePointToLineDistance(point, lineStart, lineEnd);
      expect(result).toBe(1); // Distance from (1,1) to line from (0,0) to (2,0) is 1
    });
  });
  
  describe('calculateDistance', () => {
    it('should calculate Euclidean distance between points', () => {
      const p1: Point = { x: 0, y: 0 };
      const p2: Point = { x: 3, y: 4 };
      
      const result = calculateDistance(p1, p2);
      expect(result).toBe(5); // 3-4-5 triangle
    });
  });
  
  describe('calculateCoreStability', () => {
    it('should calculate core stability score', () => {
      const keypoints = [
        createKeypoint('left_shoulder', 100, 100),
        createKeypoint('right_shoulder', 200, 100),
        createKeypoint('left_hip', 100, 200),
        createKeypoint('right_hip', 200, 200)
      ];
      
      const result = calculateCoreStability(keypoints);
      expect(result).toBeGreaterThan(0);
      expect(result).toBeLessThanOrEqual(1);
    });
  });
  
  describe('calculateVerticalAlignment', () => {
    it('should calculate vertical alignment score', () => {
      const keypoints = createCompleteKeypoints();
      
      const result = calculateVerticalAlignment(keypoints);
      expect(result).toBeGreaterThan(0);
      expect(result).toBeLessThanOrEqual(1);
    });
  });
  
  describe('calculateLateralAlignment', () => {
    it('should calculate lateral alignment score', () => {
      const keypoints = createCompleteKeypoints();
      
      const result = calculateLateralAlignment(keypoints);
      expect(result).toBeGreaterThan(0);
      expect(result).toBeLessThanOrEqual(1);
    });
  });
  
  describe('calculateConfidenceScore', () => {
    it('should calculate average confidence score', () => {
      const keypoints = [
        createKeypoint('kp1', 0, 0, 0.8),
        createKeypoint('kp2', 0, 0, 0.9),
        createKeypoint('kp3', 0, 0, 0.7)
      ];
      
      const result = calculateConfidenceScore(keypoints);
      expect(result).toBeCloseTo(0.8, 1); // (0.8 + 0.9 + 0.7) / 3 = 0.8
    });
    
    it('should handle keypoints with no confidence score', () => {
      const keypoints = [
        createKeypoint('kp1', 0, 0, 0.8),
        // @ts-ignore - simulate undefined score
        { name: 'kp2', x: 0, y: 0 }, 
        createKeypoint('kp3', 0, 0, 0.7)
      ];
      
      const result = calculateConfidenceScore(keypoints);
      expect(result).toBeCloseTo(0.5, 1); // (0.8 + 0 + 0.7) / 3 = 0.5
    });
  });
}); 