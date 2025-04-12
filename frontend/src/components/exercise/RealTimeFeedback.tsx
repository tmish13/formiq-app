import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Alert,
  Paper,
  CircularProgress,
  Chip,
  Stack
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  SportsGymnastics as ExerciseIcon
} from '@mui/icons-material';
import { PoseAnalysisService } from '../../services/poseAnalysis';
import { FeedbackItem } from '../../types/exercise';

interface RealTimeFeedbackProps {
  videoStream: MediaStream;
  exerciseType: string;
  onFeedbackUpdate?: (feedback: FeedbackItem[]) => void;
}

const RealTimeFeedback: React.FC<RealTimeFeedbackProps> = ({
  videoStream,
  exerciseType,
  onFeedbackUpdate
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>('preparing');
  const [repCount, setRepCount] = useState(0);

  useEffect(() => {
    let poseAnalysisService: PoseAnalysisService | null = null;
    let animationFrameId: number;

    const analyzePose = async () => {
      if (!poseAnalysisService) return;

      try {
        const analysis = await poseAnalysisService.analyzeFrame();
        
        // Update feedback
        setFeedback(analysis.feedback);
        if (onFeedbackUpdate) {
          onFeedbackUpdate(analysis.feedback);
        }

        // Update exercise phase and rep count
        if (analysis.phase !== currentPhase) {
          setCurrentPhase(analysis.phase);
          if (analysis.phase === 'complete') {
            setRepCount(prev => prev + 1);
          }
        }

        // Continue analysis loop
        animationFrameId = requestAnimationFrame(analyzePose);
      } catch (err) {
        setError('Error analyzing pose. Please check your camera position.');
        console.error('Pose analysis error:', err);
      }
    };

    const initializeAnalysis = async () => {
      try {
        setIsAnalyzing(true);
        setError(null);

        // Initialize pose analysis service
        poseAnalysisService = new PoseAnalysisService({
          exerciseType,
          videoStream
        });
        await poseAnalysisService.initialize();

        // Start analysis loop
        analyzePose();
      } catch (err) {
        setError('Failed to initialize pose analysis. Please try again.');
        console.error('Initialization error:', err);
      } finally {
        setIsAnalyzing(false);
      }
    };

    initializeAnalysis();

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
      if (poseAnalysisService) {
        poseAnalysisService.dispose();
      }
    };
  }, [videoStream, exerciseType, onFeedbackUpdate]);

  const getFeedbackIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <ErrorIcon color="error" />;
      case 'medium':
        return <WarningIcon color="warning" />;
      default:
        return <CheckCircleIcon color="success" />;
    }
  };

  if (isAnalyzing) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" p={3}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>
          Initializing real-time analysis...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Box mb={2}>
        <Stack direction="row" spacing={2} alignItems="center">
          <ExerciseIcon color="primary" />
          <Typography variant="h6">
            Real-time Form Analysis
          </Typography>
          <Chip
            label={`Rep Count: ${repCount}`}
            color="primary"
            variant="outlined"
          />
          <Chip
            label={`Phase: ${currentPhase}`}
            color="secondary"
            variant="outlined"
          />
        </Stack>
      </Box>

      <Stack spacing={1}>
        {feedback.map((item, index) => (
          <Alert
            key={index}
            icon={getFeedbackIcon(item.severity)}
            severity={item.severity === 'high' ? 'error' : item.severity === 'medium' ? 'warning' : 'success'}
            sx={{
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <Box>
              <Typography variant="body1">
                {item.message}
              </Typography>
              {item.details && (
                <Typography variant="body2" color="text.secondary">
                  {item.details}
                </Typography>
              )}
            </Box>
          </Alert>
        ))}
      </Stack>
    </Paper>
  );
};

export default RealTimeFeedback; 