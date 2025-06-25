import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useNavigate, useLocation } from 'react-router-dom';
import { CameraCapture } from '../../components/camera/CameraCapture';
import { useNetworkStatus } from '../../services/networkService';
import { storageService } from '../../services/storageService';
import { videoUploadService, VideoUploadProgress } from '../../services/videoUploadService';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { LoadingSpinner } from '../../components/atoms/LoadingSpinner';
import { exerciseLibraryService } from '../../services/exerciseLibraryService';

const PageContainer = styled.div`
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 16px;
`;

const Heading = styled.h1`
  margin-bottom: 24px;
  text-align: center;
`;

const FormContainer = styled.div`
  margin-top: 24px;
`;

const SelectContainer = styled.div`
  margin-bottom: 24px;
`;

const Label = styled.label`
  display: block;
  margin-bottom: 8px;
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
`;

const Select = styled.select`
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  background-color: ${({ theme }) => theme.colors.white};
  font-size: 16px;
  font-family: inherit;
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  background-color: ${({ theme }) => theme.colors.white};
  font-size: 16px;
  font-family: inherit;
  min-height: 100px;
  resize: vertical;
  margin-bottom: 24px;
`;

const Button = styled.button`
  background-color: ${({ theme }) => theme.colors.primary};
  color: ${({ theme }) => theme.colors.white};
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  
  &:hover {
    background-color: ${({ theme }) => theme.colors.primaryDark};
  }
  
  &:disabled {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.color.disabled)};
    cursor: not-allowed;
  }
`;

const OfflineNotice = styled.div`
  background-color: ${({ theme }) => theme.colors.warningLight};
  color: ${({ theme }) => theme.colors.warning};
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
`;

const SuccessMessage = styled.div`
  background-color: ${({ theme }) => theme.colors.successLight};
  color: ${({ theme }) => theme.colors.success};
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
`;

const ErrorMessage = styled.div`
  background-color: ${({ theme }) => theme.colors.errorLight};
  color: ${({ theme }) => theme.colors.error};
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

const LoadingOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
`;

const LoadingText = styled.div`
  color: ${({ theme }) => theme.colors.white};
  margin-top: 16px;
  text-align: center;
`;

const ProgressBar = styled.div<{ progress: number }>`
  width: 100%;
  height: 4px;
  background-color: ${({ theme }) => theme.colors.border};
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;

  &::after {
    content: '';
    display: block;
    width: ${({ progress }) => progress}%;
    height: 100%;
    background-color: ${({ theme }) => theme.colors.primary};
    transition: width 0.3s ease;
  }
`;

const ProgressStage = styled.div<{ active: boolean }>`
  padding: 12px 16px;
  margin: 8px 0;
  border-radius: 8px;
  border: 2px solid ${({ theme, active }) => 
    active ? theme.colors.primary : theme.colors.border};
  background-color: ${({ theme, active }) => 
    active ? theme.colors.primaryLight : theme.colors.white};
  opacity: ${({ active }) => active ? 1 : 0.6};
  transition: all 0.3s ease;
`;

const StageTitle = styled.h4`
  margin: 0 0 4px 0;
  color: ${({ theme }) => theme.colors.text};
  font-size: ${({ theme }) => theme.typography.fontSize.md};
`;

const StageDescription = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

const ProcessingContainer = styled.div`
  background-color: ${({ theme }) => theme.colors.background};
  border-radius: 12px;
  padding: 24px;
  margin-top: 24px;
  border: 1px solid ${({ theme }) => theme.colors.border};
`;

const PreselectedExercise = styled.div`
  background-color: ${({ theme }) => theme.colors.primaryLight};
  border: 2px solid ${({ theme }) => theme.colors.primary};
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const ExerciseInfo = styled.div`
  h3 {
    margin: 0 0 4px 0;
    color: ${({ theme }) => theme.colors.primary};
  }
  p {
    margin: 0;
    color: ${({ theme }) => theme.colors.textSecondary};
    font-size: ${({ theme }) => theme.typography.fontSize.sm};
  }
`;

const ChangeButton = styled.button`
  background: transparent;
  border: 1px solid ${({ theme }) => theme.colors.primary};
  color: ${({ theme }) => theme.colors.primary};
  border-radius: 4px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  
  &:hover {
    background-color: ${({ theme }) => theme.colors.primary};
    color: ${({ theme }) => theme.colors.white};
  }
`;

// Exercise types
const EXERCISE_TYPES = [
  { value: 'squat', label: 'Squat' },
  { value: 'deadlift', label: 'Deadlift' },
  { value: 'bench_press', label: 'Bench Press' },
  { value: 'overhead_press', label: 'Overhead Press' },
  { value: 'pull_up', label: 'Pull-up' },
  { value: 'push_up', label: 'Push-up' },
  { value: 'row', label: 'Row' },
];

// Interface for the offline response format
interface OfflineResponse {
  queued: boolean;
  queuedRequestId?: string;
  message?: string;
}

interface FormCheckResponse {
  id: string;
  video_url: string;
  exercise_id: string;
  user_id: string;
  status: 'pending' | 'processing' | 'completed';
  score?: number;
  overall_feedback?: string;
  analysis_url?: string;
  created_at: string;
  updated_at?: string;
}

export const FormCheckUploadPage: React.FC = () => {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [exerciseType, setExerciseType] = useState<string>('');
  const [exerciseName, setExerciseName] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<VideoUploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [exercises, setExercises] = useState<any[]>([]);
  const { status } = useNetworkStatus();
  const navigate = useNavigate();
  const location = useLocation();

  // Check for preselected exercise from Exercise Library
  useEffect(() => {
    const state = location.state as any;
    if (state?.exerciseId && state?.exerciseName) {
      setExerciseType(state.exerciseId);
      setExerciseName(state.exerciseName);
    }
  }, [location.state]);

  // Load exercises for dropdown
  useEffect(() => {
    const loadExercises = async () => {
      try {
        const exerciseList = await exerciseLibraryService.getExercises();
        setExercises(exerciseList);
      } catch (error) {
        console.error('Failed to load exercises:', error);
      }
    };
    loadExercises();
  }, []);

  const handleVideoCapture = async (video: File, thumbnail?: File) => {
    try {
      setError(null);
      setVideoFile(video);
      setSuccess('Video captured successfully!');
    } catch (err) {
      console.error('Error processing video:', err);
      setError('Failed to process video. Please try again.');
    }
  };

  const handleExerciseChange = (exerciseId: string) => {
    setExerciseType(exerciseId);
    const exercise = exercises.find(ex => ex.id === exerciseId);
    if (exercise) {
      setExerciseName(exercise.name);
    }
  };

  const clearPreselectedExercise = () => {
    setExerciseType('');
    setExerciseName('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!videoFile) {
      setError('Please record or upload a video first');
      return;
    }
    
    if (!exerciseType) {
      setError('Please select an exercise type');
      return;
    }
    
    setError(null);
    setSuccess(null);
    setIsUploading(true);
    setUploadProgress(null);
    setVideoId(null);
    
    try {
      // Use the new video upload service with real backend integration
      const uploadedVideoId = await videoUploadService.uploadVideo(videoFile, {
        exerciseId: exerciseType,
        exerciseName: exerciseName,
        onProgress: (progress: VideoUploadProgress) => {
          setUploadProgress(progress);
          if (progress.videoId) {
            setVideoId(progress.videoId);
          }
        },
        onStatusUpdate: (status) => {
          console.log('Video status update:', status);
        }
      });

      setSuccess('Upload complete! Redirecting to processing page...');
      
      // Navigate to processing page for real-time monitoring
      setTimeout(() => {
        navigate(`/processing/${uploadedVideoId}`, { 
          state: { 
            exerciseType: exerciseType,
            exerciseName: exerciseName,
            fromUpload: true
          }
        });
      }, 1500);

    } catch (err) {
      console.error('Error uploading form check:', err);
      setError(err instanceof Error ? err.message : 'Failed to upload form check. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const renderProgressStages = () => {
    if (!uploadProgress) return null;

    const stages = [
      { key: 'preparing', title: 'Preparing Video', description: 'Validating and preparing video for upload' },
      { key: 'uploading', title: 'Uploading to Cloud', description: 'Securely uploading your video to our servers' },
      { key: 'processing', title: 'Processing Video', description: 'Extracting frames and analyzing movement' },
      { key: 'analyzing', title: 'AI Analysis', description: 'Running pose detection and form analysis' },
      { key: 'completed', title: 'Analysis Complete', description: 'Your form check results are ready!' }
    ];

    return (
      <ProcessingContainer>
        <h3>Processing Your Form Check</h3>
        <ProgressBar progress={uploadProgress.progress} />
        <p>{uploadProgress.message}</p>
        {videoId && (
          <p style={{ fontSize: '14px', color: '#666' }}>
            Video ID: {videoId}
          </p>
        )}
        
        {stages.map((stage) => (
          <ProgressStage key={stage.key} active={uploadProgress.stage === stage.key}>
            <StageTitle>{stage.title}</StageTitle>
            <StageDescription>{stage.description}</StageDescription>
          </ProgressStage>
        ))}
      </ProcessingContainer>
    );
  };

  return (
    <PageContainer>
      <Heading>AI-Powered Form Analysis</Heading>
      
      {!status.connected && (
        <OfflineNotice>
          You are currently offline. You can still record videos, and they'll be uploaded when you're back online.
        </OfflineNotice>
      )}
      
      {error && <ErrorMessage>{error}</ErrorMessage>}
      {success && <SuccessMessage>{success}</SuccessMessage>}
      
      {/* Show preselected exercise */}
      {exerciseName && (
        <PreselectedExercise>
          <ExerciseInfo>
            <h3>{exerciseName}</h3>
            <p>Exercise preselected from library</p>
          </ExerciseInfo>
          <ChangeButton onClick={clearPreselectedExercise}>
            Change Exercise
          </ChangeButton>
        </PreselectedExercise>
      )}
      
      <CameraCapture onVideoCapture={handleVideoCapture} maxDuration={60} />
      
      {/* Show upload progress */}
      {isUploading && renderProgressStages()}
      
      {!isUploading && (
        <FormContainer>
          <form onSubmit={handleSubmit}>
            {!exerciseName && (
              <SelectContainer>
                <Label htmlFor="exercise-type">Exercise Type</Label>
                <Select
                  id="exercise-type"
                  value={exerciseType}
                  onChange={(e) => handleExerciseChange(e.target.value)}
                  required
                >
                  <option value="">Select Exercise Type</option>
                  {exercises.length > 0 ? (
                    exercises.map((exercise) => (
                      <option key={exercise.id} value={exercise.id}>
                        {exercise.name}
                      </option>
                    ))
                  ) : (
                    EXERCISE_TYPES.map((exercise) => (
                      <option key={exercise.value} value={exercise.value}>
                        {exercise.label}
                      </option>
                    ))
                  )}
                </Select>
              </SelectContainer>
            )}
            
            <Label htmlFor="notes">Additional Notes (Optional)</Label>
            <TextArea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add any notes about your form, weight used, or concerns..."
            />
            
            <Button type="submit" disabled={isUploading || !videoFile || !exerciseType}>
              {isUploading ? 'Processing...' : 'Start AI Analysis'}
            </Button>
          </form>
        </FormContainer>
      )}
    </PageContainer>
  );
}; 