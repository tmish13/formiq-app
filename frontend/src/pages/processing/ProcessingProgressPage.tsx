import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { 
  Container, 
  Typography, 
  Box, 
  Card, 
  CardContent, 
  Button,
  LinearProgress,
  Chip,
  Alert
} from '@mui/material';
import { 
  VideoLibrary as VideoIcon,
  Psychology as AIIcon,
  Analytics as AnalyticsIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import apiService from '../../services/apiService';
import { videoUploadService } from '../../services/videoUploadService';

const PageContainer = styled(Container)`
  padding-top: 32px;
  padding-bottom: 32px;
`;

const ProgressCard = styled(Card)`
  margin-bottom: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
`;

const StageContainer = styled.div<{ active: boolean; completed: boolean }>`
  display: flex;
  align-items: center;
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 8px;
  border: 2px solid ${({ theme, active, completed }) => 
    completed ? '#4CAF50' : active ? '#2196F3' : '#E0E0E0'};
  background-color: ${({ theme, active, completed }) => 
    completed ? '#E8F5E8' : active ? '#E3F2FD' : '#F5F5F5'};
  opacity: ${({ active, completed }) => (active || completed) ? 1 : 0.6};
  transition: all 0.3s ease;
`;

const StageIcon = styled.div<{ active: boolean; completed: boolean }>`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  margin-right: 16px;
  background-color: ${({ theme, active, completed }) => 
    completed ? '#4CAF50' : active ? '#2196F3' : '#BDBDBD'};
  color: white;
  font-size: 24px;
`;

const StageContent = styled.div`
  flex: 1;
`;

const StageTitle = styled(Typography)`
  font-weight: 600;
  margin-bottom: 4px;
`;

const StageDescription = styled(Typography)`
  color: #666;
  font-size: 14px;
`;

const VideoInfoCard = styled(Card)`
  margin-bottom: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
`;

const EstimatedTime = styled(Box)`
  text-align: center;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 24px;
`;

interface ProcessingStage {
  key: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  estimatedTime: string;
}

interface VideoStatus {
  status: 'uploading' | 'processing' | 'analyzing' | 'completed' | 'failed';
  progress?: number;
  error?: string;
  processedUrl?: string;
  exerciseType?: string;
  exerciseName?: string;
  uploadedAt?: string;
}

export const ProcessingProgressPage: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [videoStatus, setVideoStatus] = useState<VideoStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState<string>('processing');

  // Get additional info from navigation state
  const locationState = location.state as any;
  const exerciseType = locationState?.exerciseType;
  const exerciseName = locationState?.exerciseName;

  const stages: ProcessingStage[] = [
    {
      key: 'processing',
      title: 'Processing Video',
      description: 'Extracting frames and preparing for analysis',
      icon: <VideoIcon />,
      estimatedTime: '30-60 seconds'
    },
    {
      key: 'analyzing',
      title: 'AI Analysis',
      description: 'Running pose detection and form analysis',
      icon: <AIIcon />,
      estimatedTime: '1-2 minutes'
    },
    {
      key: 'completed',
      title: 'Analysis Complete',
      description: 'Results are ready for review',
      icon: <CheckIcon />,
      estimatedTime: 'Ready now!'
    }
  ];

  useEffect(() => {
    if (!videoId) {
      setError('No video ID provided');
      setLoading(false);
      return;
    }

    const pollStatus = async () => {
      try {
        const status = await apiService.getVideoStatus(videoId);
        setVideoStatus(status);
        setCurrentStage(status.status);

        // If completed, stop polling and redirect to results
        if (status.status === 'completed') {
          setLoading(false);
          setTimeout(() => {
            navigate('/analysis', {
              state: {
                videoId,
                exerciseType,
                exerciseName,
                fromProcessing: true
              }
            });
          }, 2000);
          return;
        }

        // If failed, stop polling
        if (status.status === 'failed') {
          setError(status.error || 'Processing failed');
          setLoading(false);
          return;
        }

        // Continue polling
        setTimeout(pollStatus, 3000);

      } catch (err) {
        console.error('Error polling video status:', err);
        setError('Unable to check processing status');
        setLoading(false);
      }
    };

    pollStatus();
  }, [videoId, navigate, exerciseType, exerciseName]);

  const getStageStatus = (stageKey: string) => {
    const stageIndex = stages.findIndex(s => s.key === stageKey);
    const currentIndex = stages.findIndex(s => s.key === currentStage);
    
    if (stageIndex < currentIndex) return { active: false, completed: true };
    if (stageIndex === currentIndex) return { active: true, completed: false };
    return { active: false, completed: false };
  };

  const getProgressPercentage = () => {
    if (videoStatus?.status === 'processing') return 30;
    if (videoStatus?.status === 'analyzing') return 70;
    if (videoStatus?.status === 'completed') return 100;
    return 0;
  };

  const getEstimatedTimeRemaining = () => {
    const currentStageObj = stages.find(s => s.key === currentStage);
    return currentStageObj?.estimatedTime || 'Calculating...';
  };

  if (error) {
    return (
      <PageContainer maxWidth="md">
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="h6">Processing Error</Typography>
          <Typography>{error}</Typography>
        </Alert>
        <Button 
          variant="contained" 
          onClick={() => navigate('/dashboard')}
          sx={{ mr: 2 }}
        >
          Back to Dashboard
        </Button>
        <Button 
          variant="outlined" 
          onClick={() => navigate('/workout/form-check/upload')}
        >
          Upload New Video
        </Button>
      </PageContainer>
    );
  }

  return (
    <PageContainer maxWidth="md">
      <Typography variant="h4" component="h1" gutterBottom align="center">
        Processing Your Form Analysis
      </Typography>

      {/* Video Information */}
      <VideoInfoCard>
        <CardContent>
          <Box display="flex" alignItems="center" mb={2}>
            <VideoIcon sx={{ mr: 2, fontSize: 32 }} />
            <Box>
              <Typography variant="h6">
                {exerciseName || 'Exercise Analysis'}
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.9 }}>
                Video ID: {videoId}
              </Typography>
            </Box>
          </Box>
          
          <LinearProgress 
            variant="determinate" 
            value={getProgressPercentage()} 
            sx={{ 
              height: 8, 
              borderRadius: 4,
              backgroundColor: 'rgba(255,255,255,0.3)',
              '& .MuiLinearProgress-bar': {
                backgroundColor: 'white'
              }
            }} 
          />
          
          <Box display="flex" justifyContent="space-between" mt={1}>
            <Typography variant="body2">
              {getProgressPercentage()}% Complete
            </Typography>
            <Typography variant="body2">
              {videoStatus?.status === 'completed' ? 'Done!' : `~${getEstimatedTimeRemaining()} remaining`}
            </Typography>
          </Box>
        </CardContent>
      </VideoInfoCard>

      {/* Estimated Time */}
      <EstimatedTime>
        <Typography variant="h6" color="primary" gutterBottom>
          Estimated Processing Time
        </Typography>
        <Typography variant="body1">
          Total: 2-4 minutes • Remaining: ~{getEstimatedTimeRemaining()}
        </Typography>
      </EstimatedTime>

      {/* Processing Stages */}
      <ProgressCard>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Processing Stages
          </Typography>
          
          {stages.map((stage) => {
            const { active, completed } = getStageStatus(stage.key);
            
            return (
              <StageContainer key={stage.key} active={active} completed={completed}>
                <StageIcon active={active} completed={completed}>
                  {completed ? <CheckIcon /> : stage.icon}
                </StageIcon>
                <StageContent>
                  <StageTitle variant="subtitle1">
                    {stage.title}
                  </StageTitle>
                  <StageDescription>
                    {stage.description}
                  </StageDescription>
                  {active && (
                    <Box mt={1}>
                      <Chip 
                        label="In Progress" 
                        color="primary" 
                        size="small" 
                      />
                    </Box>
                  )}
                  {completed && (
                    <Box mt={1}>
                      <Chip 
                        label="Completed" 
                        color="success" 
                        size="small" 
                      />
                    </Box>
                  )}
                </StageContent>
              </StageContainer>
            );
          })}
        </CardContent>
      </ProgressCard>

      {/* Action Buttons */}
      <Box display="flex" justifyContent="center" gap={2}>
        <Button 
          variant="outlined" 
          onClick={() => navigate('/dashboard')}
        >
          Back to Dashboard
        </Button>
        
        {videoStatus?.status === 'completed' && (
          <Button 
            variant="contained" 
            onClick={() => navigate('/analysis', {
              state: { videoId, exerciseType, exerciseName }
            })}
          >
            View Results
          </Button>
        )}
      </Box>

      {/* Additional Information */}
      <Box mt={4} p={2} bgcolor="#f8f9fa" borderRadius={2}>
        <Typography variant="body2" color="textSecondary" align="center">
          💡 <strong>Tip:</strong> You can navigate away from this page and check back later. 
          We'll save your processing status and notify you when it's complete.
        </Typography>
      </Box>
    </PageContainer>
  );
};