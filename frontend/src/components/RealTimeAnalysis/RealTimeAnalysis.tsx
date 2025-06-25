import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Card, Button, Stack, Alert, Box, Typography, Grid, Chip } from '@mui/material';
import { Videocam, Stop, Assessment, TrendingUp } from '@mui/icons-material';
import { poseAnalysisService } from '../../services/poseAnalysisService';
import { PoseAnalysisResult } from '../../types/formAnalysis';
import { MLScoreCard } from '../molecules/MLScoreCard';
import { PoseOverlayCanvas } from '../molecules/PoseOverlayCanvas';
import { MLScores, PoseData, RealTimeAnalysisState } from '../../types/ml';
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
  const [realTimeState, setRealTimeState] = useState<RealTimeAnalysisState>({
    isAnalyzing: false,
    analysisQuality: 'poor'
  });
  const [sessionMLScores, setSessionMLScores] = useState<MLScores | null>(null);
  const [currentPoseData, setCurrentPoseData] = useState<PoseData | null>(null);

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
      setRealTimeState(prev => ({ ...prev, isAnalyzing: true }));
      
      const analysis = await poseAnalysisService.analyzePose(videoRef.current);
      setCurrentAnalysis(analysis);
      drawPoseOverlay(analysis);

      // Convert analysis to pose data format
      if (analysis.keypoints && analysis.keypoints.length > 0) {
        const poseData: PoseData = {
          keypoints: analysis.keypoints.map(kp => ({
            x: kp.x,
            y: kp.y,
            score: kp.score,
            name: kp.name,
            visible: kp.score > 0.3
          })),
          score: analysis.keypoints.reduce((sum, kp) => sum + kp.score, 0) / analysis.keypoints.length,
          timestamp: Date.now()
        };
        setCurrentPoseData(poseData);

        // Update analysis quality based on keypoint confidence
        const avgConfidence = poseData.score;
        const quality = avgConfidence > 0.8 ? 'excellent' : 
                       avgConfidence > 0.6 ? 'good' : 
                       avgConfidence > 0.4 ? 'fair' : 'poor';
        
        setRealTimeState(prev => ({
          ...prev,
          analysisQuality: quality,
          currentPose: poseData
        }));

        // Calculate real-time ML scores if analysis includes them
        if (analysis.ml_scores) {
          setSessionMLScores(analysis.ml_scores);
          setRealTimeState(prev => ({
            ...prev,
            liveScores: analysis.ml_scores
          }));
        }
      }
    } catch (err) {
      console.error('Error analyzing frame:', err);
      setRealTimeState(prev => ({ ...prev, analysisQuality: 'poor' }));
    } finally {
      setRealTimeState(prev => ({ ...prev, isAnalyzing: false }));
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

  // Get analysis quality color
  const getQualityColor = (quality: RealTimeAnalysisState['analysisQuality']) => {
    switch (quality) {
      case 'excellent': return 'success';
      case 'good': return 'primary';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'grey';
    }
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Main Video Analysis */}
        <Grid item xs={12} lg={8}>
          <Card>
            <Box p={3}>
              <Box display="flex" alignItems="center" justifyContent="between" mb={2}>
                <Typography variant="h5" fontWeight="bold">
                  Real-Time Form Analysis
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <Chip
                    icon={<Assessment />}
                    label={`Quality: ${realTimeState.analysisQuality}`}
                    color={getQualityColor(realTimeState.analysisQuality)}
                    size="small"
                  />
                  {realTimeState.isAnalyzing && (
                    <Chip
                      label="Analyzing..."
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  )}
                </Box>
              </Box>

              {error && (
                <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Box position="relative" height={400} bgcolor="grey.100" borderRadius={1} mb={2}>
                <video
                  ref={videoRef}
                  style={{
                    width: '100%',
                    height: '100%',
                    objectFit: 'cover',
                    borderRadius: 8
                  }}
                  autoPlay
                  playsInline
                  muted
                />
                <canvas
                  ref={canvasRef}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none'
                  }}
                />
                
                {/* Pose Overlay */}
                {currentPoseData && (
                  <Box position="absolute" top={0} left={0} width="100%" height="100%">
                    <PoseOverlayCanvas
                      userPose={currentPoseData}
                      config={{
                        showSkeleton: true,
                        showKeypoints: true,
                        showConfidenceThreshold: 0.3,
                        keypointRadius: 4,
                        lineWidth: 2
                      }}
                    />
                  </Box>
                )}
              </Box>

              <Stack direction="row" spacing={2} justifyContent="center">
                {!isRecording ? (
                  <Button
                    variant="contained"
                    startIcon={<Videocam />}
                    onClick={startCamera}
                    size="large"
                  >
                    Start Analysis
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<Stop />}
                    onClick={stopCamera}
                    size="large"
                  >
                    Stop Analysis
                  </Button>
                )}
              </Stack>
            </Box>
          </Card>
        </Grid>

        {/* ML Scores and Analysis */}
        <Grid item xs={12} lg={4}>
          <Stack spacing={2}>
            {/* Real-time ML Scores */}
            {sessionMLScores && (
              <MLScoreCard
                scores={sessionMLScores}
                variant="compact"
                showConfidence={true}
              />
            )}

            {/* Traditional Metrics (for backward compatibility) */}
            {currentAnalysis && (
              <Card>
                <Box p={2}>
                  <Typography variant="h6" gutterBottom>
                    Live Metrics
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Box textAlign="center">
                        <Typography variant="body2" color="text.secondary">
                          Alignment
                        </Typography>
                        <Typography variant="h6" color="primary">
                          {Math.round(currentAnalysis.metrics.alignment * 100)}%
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center">
                        <Typography variant="body2" color="text.secondary">
                          Stability
                        </Typography>
                        <Typography variant="h6" color="primary">
                          {Math.round(currentAnalysis.metrics.stability * 100)}%
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center">
                        <Typography variant="body2" color="text.secondary">
                          Symmetry
                        </Typography>
                        <Typography variant="h6" color="primary">
                          {Math.round(currentAnalysis.metrics.symmetry * 100)}%
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={6}>
                      <Box textAlign="center">
                        <Typography variant="body2" color="text.secondary">
                          Consistency
                        </Typography>
                        <Typography variant="h6" color="primary">
                          {Math.round(currentAnalysis.metrics.consistency * 100)}%
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Box>
              </Card>
            )}

            {/* Analysis Tips */}
            <Card>
              <Box p={2}>
                <Typography variant="h6" gutterBottom>
                  💡 Real-time Tips
                </Typography>
                {realTimeState.analysisQuality === 'poor' && (
                  <Alert severity="warning" sx={{ mb: 1 }}>
                    <Typography variant="body2">
                      Improve lighting and move closer to the camera for better analysis.
                    </Typography>
                  </Alert>
                )}
                {realTimeState.analysisQuality === 'excellent' && isRecording && (
                  <Alert severity="success" sx={{ mb: 1 }}>
                    <Typography variant="body2">
                      Great pose detection! Keep your form steady for accurate analysis.
                    </Typography>
                  </Alert>
                )}
                {realTimeState.detectedIssues && realTimeState.detectedIssues.length > 0 && (
                  <Alert severity="info" sx={{ mb: 1 }}>
                    <Typography variant="body2">
                      {realTimeState.detectedIssues.length} form issue(s) detected. 
                      Check the pose overlay for details.
                    </Typography>
                  </Alert>
                )}
              </Box>
            </Card>
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}; 