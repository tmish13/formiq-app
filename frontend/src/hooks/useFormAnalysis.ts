import { useState, useEffect, useCallback } from 'react';
import { poseAnalysis } from '../services/poseAnalysis';
import { FormAnalysisResult } from '../types/formAnalysis';
import { Keypoint } from '@tensorflow-models/pose-detection';

interface UseFormAnalysisProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isRecording: boolean;
}

export const useFormAnalysis = ({ videoRef, isRecording }: UseFormAnalysisProps) => {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<FormAnalysisResult | null>(null);

  useEffect(() => {
    const initialize = async () => {
      try {
        await poseAnalysis.initialize();
        setIsInitialized(true);
      } catch (err) {
        setError('Failed to initialize pose detection');
        console.error('Initialization error:', err);
      }
    };

    initialize();
  }, []);

  const analyzeFrame = useCallback(async () => {
    if (!videoRef.current || !isInitialized || !isRecording) return;

    try {
      setIsAnalyzing(true);
      setError(null);

      // Detect pose
      const keypoints = await poseAnalysis.detectPose(videoRef.current);
      
      // Calculate joint angles
      const angles = poseAnalysis.calculateJointAngles(keypoints);
      
      // Analyze pose and get feedback
      const feedback = poseAnalysis.analyzePose(keypoints, angles);

      // Calculate confidence based on keypoint visibility
      const visibleKeypoints = keypoints.filter(kp => kp.score && kp.score > 0.3).length;
      const confidence = visibleKeypoints / keypoints.length;

      const result: FormAnalysisResult = {
        confidence,
        isReliable: confidence > 0.7,
        keypoints,
        angles,
        feedback,
        timestamp: Date.now()
      };

      setAnalysisResult(result);
    } catch (err) {
      setError('Failed to analyze pose');
      console.error('Analysis error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  }, [videoRef, isInitialized, isRecording]);

  useEffect(() => {
    let animationFrameId: number;

    const analyze = async () => {
      if (isRecording) {
        await analyzeFrame();
        animationFrameId = requestAnimationFrame(analyze);
      }
    };

    if (isRecording) {
      animationFrameId = requestAnimationFrame(analyze);
    }

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [isRecording, analyzeFrame]);

  return {
    isInitialized,
    isAnalyzing,
    error,
    analysisResult
  };
}; 