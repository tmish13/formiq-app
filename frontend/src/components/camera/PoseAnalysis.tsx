import React, { useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import * as poseDetection from '@tensorflow-models/pose-detection';
import * as tf from '@tensorflow/tfjs';
import '@tensorflow/tfjs-backend-webgl';

const AnalysisContainer = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
`;

const Canvas = styled.canvas`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
`;

const FeedbackContainer = styled.div`
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
  padding: 12px 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 2;
  max-width: 80%;
`;

const FeedbackText = styled.p<{ type: 'success' | 'warning' | 'error' }>`
  color: ${({ theme, type }) => {
    switch (type) {
      case 'success':
        return getThemeValue(theme, 'colors.success', fallbacks.colors.success);
      case 'warning':
        return getThemeValue(theme, 'colors.warning', fallbacks.colors.warning);
      case 'error':
        return getThemeValue(theme, 'colors.error', fallbacks.colors.error);
      default:
        return getThemeValue(theme, 'colors.text', fallbacks.colors.text);
    }
  }};
  margin: 0;
  font-size: 14px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
`;

interface Keypoint {
  x: number;
  y: number;
  score?: number;
  name?: string;
}

interface PoseAnalysisProps {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  exerciseType: string;
  onAnalysisComplete?: (analysis: {
    score: number;
    feedback: string[];
    keypoints: Keypoint[];
  }) => void;
}

export const PoseAnalysis: React.FC<PoseAnalysisProps> = ({
  videoRef,
  exerciseType,
  onAnalysisComplete,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [detector, setDetector] = useState<poseDetection.PoseDetector | null>(null);
  const [feedback, setFeedback] = useState<{ text: string; type: 'success' | 'warning' | 'error' }[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    const initializeDetector = async () => {
      try {
        // Initialize TensorFlow.js backend
        await tf.setBackend('webgl');
        await tf.ready();

        // Load the BlazePose model
        const model = poseDetection.SupportedModels.BlazePose;
        const detectorConfig = {
          runtime: 'tfjs',
          modelType: 'full',
        };
        
        const poseDetector = await poseDetection.createDetector(model, detectorConfig);
        setDetector(poseDetector);
      } catch (error) {
        console.error('Error initializing pose detector:', error);
      }
    };

    initializeDetector();
  }, []);

  useEffect(() => {
    if (!detector || !videoRef.current || !canvasRef.current) return;

    const analyzePose = async () => {
      if (!videoRef.current || !canvasRef.current || !detector) return;

      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      
      if (!ctx) return;

      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      try {
        // Detect poses
        const poses = await detector.estimatePoses(video);
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw video frame
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        if (poses.length > 0) {
          const pose = poses[0];
          
          // Draw keypoints
          pose.keypoints.forEach((keypoint) => {
            if (keypoint.score && keypoint.score > 0.3) {
              ctx.beginPath();
              ctx.arc(keypoint.x, keypoint.y, 5, 0, 2 * Math.PI);
              ctx.fillStyle = '#00ff00';
              ctx.fill();
            }
          });

          // Analyze form based on exercise type
          const analysis = analyzeExerciseForm(pose, exerciseType);
          setFeedback(analysis.feedback);

          if (onAnalysisComplete) {
            onAnalysisComplete({
              score: analysis.score,
              feedback: analysis.feedback.map(f => f.text),
              keypoints: pose.keypoints,
            });
          }
        }
      } catch (error) {
        console.error('Error analyzing pose:', error);
      }
    };

    const animationFrame = requestAnimationFrame(analyzePose);
    return () => cancelAnimationFrame(animationFrame);
  }, [detector, videoRef, exerciseType, onAnalysisComplete]);

  const analyzeExerciseForm = (pose: poseDetection.Pose, exerciseType: string) => {
    const keypoints = pose.keypoints;
    const feedback: { text: string; type: 'success' | 'warning' | 'error' }[] = [];
    let score = 100;

    switch (exerciseType) {
      case 'squat':
        const hipAngle = calculateAngle(
          keypoints.find(k => k.name === 'left_hip'),
          keypoints.find(k => k.name === 'left_knee'),
          keypoints.find(k => k.name === 'left_ankle')
        );

        if (hipAngle < 90) {
          feedback.push({
            text: 'Squat deeper - aim for 90 degrees',
            type: 'warning',
          });
          score -= 10;
        }

        const kneeAlignment = checkKneeAlignment(keypoints);
        if (!kneeAlignment.aligned) {
          feedback.push({
            text: kneeAlignment.message,
            type: 'error',
          });
          score -= 20;
        }
        break;

      default:
        feedback.push({
          text: 'Exercise type not supported',
          type: 'error',
        });
        score = 0;
    }

    return { score, feedback };
  };

  const calculateAngle = (point1: Keypoint | undefined, point2: Keypoint | undefined, point3: Keypoint | undefined) => {
    if (!point1 || !point2 || !point3) return 0;

    const angle = Math.atan2(point3.y - point2.y, point3.x - point2.x) -
                 Math.atan2(point1.y - point2.y, point1.x - point2.x);
    
    return Math.abs(angle * (180 / Math.PI));
  };

  const checkKneeAlignment = (keypoints: Keypoint[]) => {
    const leftKnee = keypoints.find(k => k.name === 'left_knee');
    const leftAnkle = keypoints.find(k => k.name === 'left_ankle');
    const leftHip = keypoints.find(k => k.name === 'left_hip');

    if (!leftKnee || !leftAnkle || !leftHip) {
      return { aligned: false, message: 'Unable to detect knee alignment' };
    }

    const kneeAngle = Math.abs(leftAnkle.x - leftKnee.x);
    if (kneeAngle > 20) {
      return {
        aligned: false,
        message: 'Keep knees aligned with toes',
      };
    }

    return { aligned: true, message: '' };
  };

  return (
    <AnalysisContainer>
      <Canvas ref={canvasRef} />
      {feedback.length > 0 && (
        <FeedbackContainer>
          {feedback.map((item, index) => (
            <FeedbackText key={index} type={item.type}>
              {item.text}
            </FeedbackText>
          ))}
        </FeedbackContainer>
      )}
    </AnalysisContainer>
  );
}; 