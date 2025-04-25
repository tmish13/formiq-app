import { ExerciseType } from '../services/poseAnalysis/exerciseTypes';
import type { FormAnalysisResult, FormFeedback } from '../types/formAnalysis';

export const generateTestFormAnalysis = (): FormAnalysisResult => {
  return {
    confidence: 0.85,
    isReliable: true,
    keypoints: [
      { x: 100, y: 200, score: 0.95, name: 'leftShoulder' },
      { x: 150, y: 250, score: 0.92, name: 'rightShoulder' }
    ],
    angles: {
      leftKnee: { value: 90, confidence: 0.95 },
      rightKnee: { value: 88, confidence: 0.93 }
    },
    feedback: [
      {
        message: 'Good form overall',
        confidence: 0.9,
        type: 'success'
      },
      {
        message: 'Knees slightly caving inward',
        confidence: 0.8,
        type: 'warning',
        jointName: 'knee'
      }
    ],
    timestamp: Date.now()
  };
}; 