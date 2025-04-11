import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Card, Button, Space, Progress, Alert } from 'antd';
import { VideoCameraOutlined, StopOutlined } from '@ant-design/icons';
import { poseAnalysisService } from '../../services/poseAnalysisService';
import { PoseAnalysisResult } from '../../types/formAnalysis';
import styles from './RealTimeAnalysis.module.css';

const ANALYSIS_INTERVAL = 100; // Analyze every 100ms

export const RealTimeAnalysis: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analysisIntervalRef = useRef<number | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentAnalysis, setCurrentAnalysis] = useState<PoseAnalysisResult | null>(null);

  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: 640,
          height: 480,
          facingMode: 'user'
        }
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
      }

      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError('Failed to access camera. Please make sure you have granted camera permissions.');
      console.error('Error accessing camera:', err);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsRecording(false);
  }, []);

  const drawPoseOverlay = useCallback((analysis: PoseAnalysisResult) => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !videoRef.current) return;

    // Clear previous drawing
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Set canvas size to match video
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;

    // Draw keypoints
    analysis.keypoints.forEach(keypoint => {
      if (keypoint.score > 0.3) {
        ctx.beginPath();
        ctx.arc(keypoint.x, keypoint.y, 5, 0, 2 * Math.PI);
        ctx.fillStyle = 'red';
        ctx.fill();
      }
    });

    // Draw connections between keypoints
    const connections = [
      ['left_shoulder', 'right_shoulder'],
      ['left_shoulder', 'left_elbow'],
      ['right_shoulder', 'right_elbow'],
      ['left_elbow', 'left_wrist'],
      ['right_elbow', 'right_wrist'],
      ['left_shoulder', 'left_hip'],
      ['right_shoulder', 'right_hip'],
      ['left_hip', 'right_hip'],
      ['left_hip', 'left_knee'],
      ['right_hip', 'right_knee'],
      ['left_knee', 'left_ankle'],
      ['right_knee', 'right_ankle']
    ];

    ctx.strokeStyle = 'blue';
    ctx.lineWidth = 2;

    connections.forEach(([start, end]) => {
      const startPoint = analysis.keypoints.find(kp => kp.name === start);
      const endPoint = analysis.keypoints.find(kp => kp.name === end);

      if (startPoint && endPoint && startPoint.score > 0.3 && endPoint.score > 0.3) {
        ctx.beginPath();
        ctx.moveTo(startPoint.x, startPoint.y);
        ctx.lineTo(endPoint.x, endPoint.y);
        ctx.stroke();
      }
    });
  }, []);

  const analyzeFrame = useCallback(async () => {
    if (!videoRef.current || !videoRef.current.videoWidth) return;

    try {
      const analysis = await poseAnalysisService.analyzePose(videoRef.current);
      setCurrentAnalysis(analysis);
      drawPoseOverlay(analysis);
    } catch (err) {
      console.error('Error analyzing frame:', err);
    }
  }, [drawPoseOverlay]);

  useEffect(() => {
    if (isRecording) {
      analysisIntervalRef.current = window.setInterval(analyzeFrame, ANALYSIS_INTERVAL);
    } else {
      if (analysisIntervalRef.current) {
        clearInterval(analysisIntervalRef.current);
        analysisIntervalRef.current = null;
      }
    }

    return () => {
      if (analysisIntervalRef.current) {
        clearInterval(analysisIntervalRef.current);
      }
      stopCamera();
    };
  }, [isRecording, analyzeFrame, stopCamera]);

  const renderMetrics = () => {
    if (!currentAnalysis) return null;

    return (
      <div className={styles.metrics}>
        <div className={styles.metric}>
          <span>Alignment</span>
          <Progress
            type="circle"
            percent={Math.round(currentAnalysis.metrics.alignment * 100)}
            size="small"
          />
        </div>
        <div className={styles.metric}>
          <span>Stability</span>
          <Progress
            type="circle"
            percent={Math.round(currentAnalysis.metrics.stability * 100)}
            size="small"
          />
        </div>
        <div className={styles.metric}>
          <span>Symmetry</span>
          <Progress
            type="circle"
            percent={Math.round(currentAnalysis.metrics.symmetry * 100)}
            size="small"
          />
        </div>
        <div className={styles.metric}>
          <span>Consistency</span>
          <Progress
            type="circle"
            percent={Math.round(currentAnalysis.metrics.consistency * 100)}
            size="small"
          />
        </div>
      </div>
    );
  };

  return (
    <Card className={styles.container}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {error && (
          <Alert
            message="Error"
            description={error}
            type="error"
            showIcon
            closable
            onClose={() => setError(null)}
          />
        )}

        <div className={styles.videoContainer}>
          <video
            ref={videoRef}
            className={styles.video}
            autoPlay
            playsInline
            muted
          />
          <canvas
            ref={canvasRef}
            className={styles.overlay}
          />
        </div>

        <Space>
          {!isRecording ? (
            <Button
              type="primary"
              icon={<VideoCameraOutlined />}
              onClick={startCamera}
            >
              Start Analysis
            </Button>
          ) : (
            <Button
              danger
              icon={<StopOutlined />}
              onClick={stopCamera}
            >
              Stop Analysis
            </Button>
          )}
        </Space>

        {renderMetrics()}
      </Space>
    </Card>
  );
}; 