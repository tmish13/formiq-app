import React, { useRef, useState } from 'react';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import { useFormAnalysis } from '../../hooks/useFormAnalysis';
import { PoseVisualization } from './PoseVisualization';
import { FeedbackDisplay } from './FeedbackDisplay';

export const FormValidation: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);

  const { isInitialized, isAnalyzing, error, analysisResult } = useFormAnalysis({
    videoRef,
    isRecording
  });

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false
      });
      setMediaStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err) {
      console.error('Failed to access camera:', err);
    }
  };

  const stopCamera = () => {
    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      setMediaStream(null);
    }
    setIsRecording(false);
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
  };

  if (!isInitialized) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ mb: 2 }}>
        {!mediaStream ? (
          <Button variant="contained" onClick={startCamera}>
            Start Camera
          </Button>
        ) : (
          <Button variant="contained" color="secondary" onClick={stopCamera}>
            Stop Camera
          </Button>
        )}
      </Box>

      {mediaStream && (
        <>
          <Box sx={{ position: 'relative', width: '100%', maxWidth: 640, mb: 2 }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              style={{ width: '100%', borderRadius: '8px' }}
            />
            <Button
              variant="contained"
              color={isRecording ? 'error' : 'primary'}
              onClick={toggleRecording}
              sx={{ position: 'absolute', bottom: 16, right: 16 }}
            >
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </Button>
          </Box>

          {error && (
            <Typography color="error" sx={{ mb: 2 }}>
              {error}
            </Typography>
          )}

          {isAnalyzing && (
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              <Typography>Analyzing pose...</Typography>
            </Box>
          )}

          {analysisResult && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <PoseVisualization
                keypoints={analysisResult.keypoints}
                angles={analysisResult.angles}
              />
              <FeedbackDisplay result={analysisResult} />
            </Box>
          )}
        </>
      )}
    </Box>
  );
}; 