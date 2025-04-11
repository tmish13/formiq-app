import React, { useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import * as poseDetection from '@tensorflow-models/pose-detection';
import { PoseAnalysisService, PoseAnalysisResult, ExerciseType } from '../../services/poseAnalysisService';
import type { FeedbackItem } from '../../services/poseAnalysisService';
import { useTheme } from '../../hooks/useTheme';
import type { DefaultTheme } from 'styled-components';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  gap: ${({ theme }) => theme.spacing.md};
`;

const VideoContainer = styled.div`
  position: relative;
  width: 100%;
  max-width: 640px;
  aspect-ratio: 16/9;
  background-color: ${({ theme }) => theme.colors.background};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  overflow: hidden;
  box-shadow: ${({ theme }) => theme.shadows.md};
`;

const Video = styled.video`
  width: 100%;
  height: 100%;
  object-fit: cover;
`;

const Canvas = styled.canvas`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
`;

const FeedbackContainer = styled.div`
  width: 100%;
  max-width: 640px;
  padding: ${({ theme }) => theme.spacing.lg};
  background-color: ${({ theme }) => theme.colors.background};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  box-shadow: ${({ theme }) => theme.shadows.sm};
`;

const Score = styled.div`
  font-size: ${({ theme }) => theme.typography.fontSize.xl};
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
  color: ${({ theme }) => theme.colors.primary};
  margin-bottom: ${({ theme }) => theme.spacing.md};
  text-align: center;
`;

const FeedbackList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const FeedbackItem = styled.li`
  padding: ${({ theme }) => `${theme.spacing.sm} 0`};
  color: ${({ theme }) => theme.colors.text};
  border-bottom: 1px solid ${({ theme }) => theme.colors.border};
  
  &:last-child {
    border-bottom: none;
  }
`;

const GuidelineContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
`;

const AngleDisplay = styled.div<{ x: number; y: number; isCorrect: boolean }>`
  position: absolute;
  left: ${props => props.x}px;
  top: ${props => props.y}px;
  transform: translate(-50%, -50%);
  background-color: ${props => props.isCorrect ? 'rgba(46, 213, 115, 0.8)' : 'rgba(255, 71, 87, 0.8)'};
  color: ${({ theme }) => theme.colors.white};
  padding: ${({ theme }) => `${theme.spacing.xs} ${theme.spacing.sm}`};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  font-size: ${({ theme }) => theme.typography.fontSize.xs};
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
`;

const GuideText = styled.div<{ x: number; y: number }>`
  position: absolute;
  left: ${props => props.x}px;
  top: ${props => props.y}px;
  transform: translate(-50%, -50%);
  color: ${({ theme }) => theme.colors.white};
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.5);
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
`;

const AnalysisContainer = styled.div`
  position: relative;
  width: 100%;
  height: 100%;
`;

const FeedbackText = styled.p<{ type: 'success' | 'warning' | 'error' }>`
  color: ${({ type, theme }) => {
    switch (type) {
      case 'success':
        return theme.colors.success;
      case 'warning':
        return theme.colors.warning;
      case 'error':
        return theme.colors.error;
      default:
        return theme.colors.text;
    }
  }};
  margin: 0;
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
`;

interface PoseAnalysisProps {
  exerciseType: ExerciseType;
  onAnalysisComplete?: (result: PoseAnalysisResult) => void;
  theme?: DefaultTheme;
}

export const PoseAnalysis: React.FC<PoseAnalysisProps> = ({
  exerciseType,
  onAnalysisComplete,
  theme: propTheme
}) => {
  const defaultTheme = useTheme();
  const theme = propTheme || defaultTheme;
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [currentAnalysis, setCurrentAnalysis] = useState<PoseAnalysisResult | null>(null);
  const poseAnalysisService = useRef<PoseAnalysisService>();

  useEffect(() => {
    const initializeService = async () => {
      const service = PoseAnalysisService.getInstance({
        minConfidence: 0.3,
        modelType: 'MoveNet',
        exerciseType,
        onAnalysisResult: (analysis) => {
          setCurrentAnalysis(analysis);
          onAnalysisComplete?.(analysis);
          drawPoseOnCanvas(analysis);
        }
      });

      poseAnalysisService.current = service;
      await service.initialize();
    };

    initializeService();

    return () => {
      poseAnalysisService.current?.cleanup();
    };
  }, [exerciseType, onAnalysisComplete]);

  const startCamera = async () => {
    if (!videoRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: 640,
          height: 360,
          facingMode: 'user'
        }
      });

      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      
      setIsAnalyzing(true);
      await poseAnalysisService.current?.startAnalysis(videoRef.current);
    } catch (error) {
      console.error('Error accessing camera:', error);
    }
  };

  const stopCamera = () => {
    if (!videoRef.current?.srcObject) return;

    const stream = videoRef.current.srcObject as MediaStream;
    stream.getTracks().forEach(track => track.stop());
    videoRef.current.srcObject = null;
    
    poseAnalysisService.current?.stopAnalysis();
    setIsAnalyzing(false);
    setCurrentAnalysis(null);

    // Clear canvas
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    }
  };

  const drawPoseOnCanvas = (analysis: PoseAnalysisResult) => {
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;

    // Clear previous frame
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    // Set drawing styles
    ctx.strokeStyle = 'rgba(46, 213, 115, 0.8)';
    ctx.fillStyle = 'rgba(46, 213, 115, 0.8)';
    ctx.lineWidth = 2;

    // Draw keypoints with different colors based on confidence
    analysis.keypoints.forEach((keypoint: poseDetection.Keypoint) => {
      if (keypoint.score && keypoint.score > 0.3) {
        ctx.fillStyle = keypoint.score > 0.7 
          ? 'rgba(46, 213, 115, 0.8)'
          : 'rgba(255, 71, 87, 0.8)';
        
        ctx.beginPath();
        ctx.arc(keypoint.x, keypoint.y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    });

    // Draw skeleton with dynamic colors
    drawSkeleton(ctx, analysis.keypoints);
    
    // Draw form guidelines
    drawFormGuidelines(ctx, analysis.keypoints);
  };

  const drawSkeleton = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    // Define connections between keypoints for a basic skeleton
    const connections: [string, string][] = [
      ['nose', 'left_eye'], ['nose', 'right_eye'],
      ['left_eye', 'left_ear'], ['right_eye', 'right_ear'],
      ['nose', 'left_shoulder'], ['nose', 'right_shoulder'],
      ['left_shoulder', 'right_shoulder'],
      ['left_shoulder', 'left_elbow'], ['right_shoulder', 'right_elbow'],
      ['left_elbow', 'left_wrist'], ['right_elbow', 'right_wrist'],
      ['left_shoulder', 'left_hip'], ['right_shoulder', 'right_hip'],
      ['left_hip', 'right_hip'],
      ['left_hip', 'left_knee'], ['right_hip', 'right_knee'],
      ['left_knee', 'left_ankle'], ['right_knee', 'right_ankle']
    ];

    connections.forEach(([from, to]) => {
      const fromPoint = keypoints.find(kp => kp.name === from);
      const toPoint = keypoints.find(kp => kp.name === to);

      if (fromPoint?.score && toPoint?.score &&
          fromPoint.score > 0.3 && toPoint.score > 0.3) {
        ctx.beginPath();
        ctx.moveTo(fromPoint.x, fromPoint.y);
        ctx.lineTo(toPoint.x, toPoint.y);
        ctx.stroke();
      }
    });
  };

  const drawFormGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    switch (exerciseType) {
      case 'squat':
        drawSquatGuidelines(ctx, keypoints);
        break;
      case 'pushup':
        drawPushupGuidelines(ctx, keypoints);
        break;
      case 'plank':
        drawPlankGuidelines(ctx, keypoints);
        break;
      case 'lunges':
        drawLungeGuidelines(ctx, keypoints);
        break;
      case 'deadlift':
        drawDeadliftGuidelines(ctx, keypoints);
        break;
      case 'burpees':
        drawBurpeeGuidelines(ctx, keypoints);
        break;
      case 'mountain_climbers':
        drawMountainClimberGuidelines(ctx, keypoints);
        break;
    }
  };

  const drawSquatGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');

    if (leftHip && rightHip && leftKnee && rightKnee) {
      // Draw parallel line for hip level
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(0, (leftHip.y + rightHip.y) / 2);
      ctx.lineTo(ctx.canvas.width, (leftHip.y + rightHip.y) / 2);
      ctx.stroke();

      // Draw knee alignment guides
      ctx.strokeStyle = theme.colors.warning;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(leftKnee.x, 0);
      ctx.lineTo(leftKnee.x, ctx.canvas.height);
      ctx.moveTo(rightKnee.x, 0);
      ctx.lineTo(rightKnee.x, ctx.canvas.height);
      ctx.stroke();
    }
  };

  const drawPushupGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftWrist = keypoints.find(kp => kp.name === 'left_wrist');
    const rightWrist = keypoints.find(kp => kp.name === 'right_wrist');

    if (leftShoulder && rightShoulder && leftWrist && rightWrist) {
      // Draw shoulder alignment guide
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(0, (leftShoulder.y + rightShoulder.y) / 2);
      ctx.lineTo(ctx.canvas.width, (leftShoulder.y + rightShoulder.y) / 2);
      ctx.stroke();

      // Draw wrist-shoulder vertical alignment
      ctx.strokeStyle = theme.colors.warning;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(leftWrist.x, leftWrist.y);
      ctx.lineTo(leftWrist.x, leftShoulder.y);
      ctx.moveTo(rightWrist.x, rightWrist.y);
      ctx.lineTo(rightWrist.x, rightShoulder.y);
      ctx.stroke();
    }
  };

  const drawPlankGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');

    if (leftShoulder && rightShoulder && leftHip && rightHip && leftAnkle && rightAnkle) {
      // Draw body alignment line
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([5, 5]);
      const midShoulder = {
        x: (leftShoulder.x + rightShoulder.x) / 2,
        y: (leftShoulder.y + rightShoulder.y) / 2
      };
      const midHip = {
        x: (leftHip.x + rightHip.x) / 2,
        y: (leftHip.y + rightHip.y) / 2
      };
      const midAnkle = {
        x: (leftAnkle.x + rightAnkle.x) / 2,
        y: (leftAnkle.y + rightAnkle.y) / 2
      };

      ctx.beginPath();
      ctx.moveTo(midShoulder.x, midShoulder.y);
      ctx.lineTo(midHip.x, midHip.y);
      ctx.lineTo(midAnkle.x, midAnkle.y);
      ctx.stroke();
    }
  };

  const drawLungeGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');
    const leftAnkle = keypoints.find(kp => kp.name === 'left_ankle');
    const rightAnkle = keypoints.find(kp => kp.name === 'right_ankle');

    if (leftKnee && rightKnee && leftAnkle && rightAnkle) {
      // Draw front knee alignment guide (90 degrees)
      ctx.strokeStyle = theme.colors.warning;
      ctx.setLineDash([5, 5]);
      const frontKnee = leftKnee.y > rightKnee.y ? leftKnee : rightKnee;
      const frontAnkle = leftKnee.y > rightKnee.y ? leftAnkle : rightAnkle;

      ctx.beginPath();
      ctx.moveTo(frontKnee.x, frontKnee.y);
      ctx.lineTo(frontAnkle.x, frontKnee.y);
      ctx.stroke();

      // Draw vertical line for knee tracking
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(frontAnkle.x, 0);
      ctx.lineTo(frontAnkle.x, ctx.canvas.height);
      ctx.stroke();
    }
  };

  const drawDeadliftGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');

    if (leftShoulder && rightShoulder && leftHip && rightHip) {
      // Draw bar path guide
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([]);
      const midShoulder = {
        x: (leftShoulder.x + rightShoulder.x) / 2,
        y: (leftShoulder.y + rightShoulder.y) / 2
      };

      // Draw hip hinge angle guide
      ctx.strokeStyle = theme.colors.warning;
      ctx.setLineDash([5, 5]);
      const midHip = {
        x: (leftHip.x + rightHip.x) / 2,
        y: (leftHip.y + rightHip.y) / 2
      };

      ctx.beginPath();
      ctx.moveTo(midShoulder.x, 0);
      ctx.lineTo(midShoulder.x, ctx.canvas.height);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(midHip.x, midHip.y);
      ctx.lineTo(midHip.x + 100, midHip.y);
      ctx.stroke();
    }
  };

  const drawBurpeeGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftWrist = keypoints.find(kp => kp.name === 'left_wrist');
    const rightWrist = keypoints.find(kp => kp.name === 'right_wrist');

    if (leftShoulder && rightShoulder && leftHip && rightHip && leftWrist && rightWrist) {
      // Draw plank alignment guide
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([5, 5]);
      const midShoulder = {
        x: (leftShoulder.x + rightShoulder.x) / 2,
        y: (leftShoulder.y + rightShoulder.y) / 2
      };
      const midHip = {
        x: (leftHip.x + rightHip.x) / 2,
        y: (leftHip.y + rightHip.y) / 2
      };

      ctx.beginPath();
      ctx.moveTo(midShoulder.x, midShoulder.y);
      ctx.lineTo(midHip.x, midHip.y);
      ctx.stroke();

      // Draw hand position guides
      ctx.strokeStyle = theme.colors.warning;
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.moveTo(leftWrist.x, leftWrist.y);
      ctx.lineTo(leftWrist.x, leftShoulder.y);
      ctx.moveTo(rightWrist.x, rightWrist.y);
      ctx.lineTo(rightWrist.x, rightShoulder.y);
      ctx.stroke();
    }
  };

  const drawMountainClimberGuidelines = (ctx: CanvasRenderingContext2D, keypoints: poseDetection.Keypoint[]) => {
    const leftShoulder = keypoints.find(kp => kp.name === 'left_shoulder');
    const rightShoulder = keypoints.find(kp => kp.name === 'right_shoulder');
    const leftHip = keypoints.find(kp => kp.name === 'left_hip');
    const rightHip = keypoints.find(kp => kp.name === 'right_hip');
    const leftKnee = keypoints.find(kp => kp.name === 'left_knee');
    const rightKnee = keypoints.find(kp => kp.name === 'right_knee');

    if (leftShoulder && rightShoulder && leftHip && rightHip && leftKnee && rightKnee) {
      // Draw plank alignment guide
      ctx.strokeStyle = theme.colors.info;
      ctx.setLineDash([5, 5]);
      const midShoulder = {
        x: (leftShoulder.x + rightShoulder.x) / 2,
        y: (leftShoulder.y + rightShoulder.y) / 2
      };
      const midHip = {
        x: (leftHip.x + rightHip.x) / 2,
        y: (leftHip.y + rightHip.y) / 2
      };

      ctx.beginPath();
      ctx.moveTo(midShoulder.x, midShoulder.y);
      ctx.lineTo(midHip.x, midHip.y);
      ctx.stroke();

      // Draw knee drive height guides
      ctx.strokeStyle = theme.colors.warning;
      ctx.setLineDash([]);
      const targetKneeHeight = midHip.y - 50; // Target height for knee drive

      ctx.beginPath();
      ctx.moveTo(0, targetKneeHeight);
      ctx.lineTo(ctx.canvas.width, targetKneeHeight);
      ctx.stroke();
    }
  };

  return (
    <Container>
      <VideoContainer>
        <Video
          ref={videoRef}
          playsInline
          muted
        />
        <Canvas
          ref={canvasRef}
          width={640}
          height={360}
        />
        <GuidelineContainer>
          {currentAnalysis?.keypoints.map((keypoint, index) => (
            keypoint.score && keypoint.score > 0.7 && (
              <GuideText
                key={index}
                x={keypoint.x}
                y={keypoint.y - 20}
              >
                {keypoint.name}
              </GuideText>
            )
          ))}
        </GuidelineContainer>
      </VideoContainer>

      <button onClick={isAnalyzing ? stopCamera : startCamera}>
        {isAnalyzing ? 'Stop Analysis' : 'Start Analysis'}
      </button>

      {currentAnalysis && (
        <FeedbackContainer>
          <Score>Score: {Math.round(currentAnalysis.score * 100)}%</Score>
          <FeedbackList>
            {currentAnalysis.feedback.map((feedback: FeedbackItem, index: number) => (
              <FeedbackItem key={index}>{feedback.text}</FeedbackItem>
            ))}
          </FeedbackList>
        </FeedbackContainer>
      )}
    </Container>
  );
}; 