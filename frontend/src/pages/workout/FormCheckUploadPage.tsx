import React, { useState } from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { CameraCapture } from '../../components/camera/CameraCapture';
import { useNetworkStatus } from '../../services/networkService';
import { storageService } from '../../services/storageService';
import { apiService } from '../../services/apiService';
import { videoService } from '../../services/videoService';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { ApiResponse } from '../../services/apiService';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

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
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [exerciseType, setExerciseType] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isCompressing, setIsCompressing] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isQueued, setIsQueued] = useState<boolean>(false);
  const { status } = useNetworkStatus();
  const navigate = useNavigate();

  const handleVideoCapture = async (video: File, thumbnail?: File) => {
    try {
      setIsCompressing(true);
      setError(null);

      // Compress video before setting it
      const compressedVideo = await videoService.compressVideo(video, {
        maxSizeMB: 50,
        maxWidth: 1280,
        maxHeight: 720,
        quality: 0.8,
      });

      // Set the compressed video file
      setVideoFile(new File([compressedVideo.data], video.name, { 
        type: compressedVideo.type 
      }));

      // Set the thumbnail file if provided, otherwise generate one
      if (thumbnail) {
        setThumbnailFile(thumbnail);
      } else {
        const videoThumbnail = await videoService.generateThumbnail(video);
        if (videoThumbnail) {
          setThumbnailFile(new File([videoThumbnail], 'thumbnail.jpg', { 
            type: 'image/jpeg' 
          }));
        }
      }
    } catch (err) {
      console.error('Error processing video:', err);
      setError('Failed to process video. Please try again.');
    } finally {
      setIsCompressing(false);
    }
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
    setUploadProgress(0);
    
    try {
      // Create form data for the API request
      const formData = new FormData();
      formData.append('video', videoFile);
      formData.append('exercise_type', exerciseType);
      
      if (notes) {
        formData.append('notes', notes);
      }
      
      if (thumbnailFile) {
        formData.append('thumbnail', thumbnailFile);
      }
      
      // Make API request with offline capability and progress tracking
      const response = await apiService.formChecks.upload(formData, {
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(progress);
          }
        }
      });
      
      const formCheckData = (response.data as ApiResponse<FormCheckResponse>).data;
      
      // Check if the request is being processed
      if (formCheckData.status === 'processing') {
        setIsQueued(true);
        
        // Store the form check data locally for offline access
        await storageService.addToWorkoutQueue({
          method: 'post',
          url: '/form-checks',
          data: {
            exercise_type: exerciseType,
            notes,
            video_filename: videoFile.name,
            recorded_at: new Date().toISOString(),
          },
          queueId: formCheckData.id || `offline-${Date.now()}`,
          queuedAt: new Date().toISOString(),
        });
        
        setSuccess('Your form check has been saved and will be processed shortly');
      } else {
        setSuccess('Your form check has been uploaded successfully!');
        
        // Navigate to analysis page after successful upload
        setTimeout(() => {
          navigate('/analysis', { 
            state: { 
              formCheckId: formCheckData.id,
              exerciseType: exerciseType
            }
          });
        }, 2000);
      }
    } catch (err) {
      console.error('Error uploading form check:', err);
      setError('Failed to upload form check. Please try again.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <PageContainer>
      <Heading>Record Exercise Form</Heading>
      
      {!status.connected && (
        <OfflineNotice>
          You are currently offline. You can still record videos, and they'll be uploaded when you're back online.
        </OfflineNotice>
      )}
      
      {error && <ErrorMessage>{error}</ErrorMessage>}
      {success && <SuccessMessage>{success}</SuccessMessage>}
      
      <CameraCapture onVideoCapture={handleVideoCapture} maxDuration={60} />
      
      <FormContainer>
        <form onSubmit={handleSubmit}>
          <SelectContainer>
            <Label htmlFor="exercise-type">Exercise Type</Label>
            <Select
              id="exercise-type"
              value={exerciseType}
              onChange={(e) => setExerciseType(e.target.value)}
              required
            >
              <option value="">Select Exercise Type</option>
              {EXERCISE_TYPES.map((exercise) => (
                <option key={exercise.value} value={exercise.value}>
                  {exercise.label}
                </option>
              ))}
            </Select>
          </SelectContainer>
          
          <Label htmlFor="notes">Additional Notes (Optional)</Label>
          <TextArea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any notes about your form, weight used, or concerns..."
          />
          
          <Button type="submit" disabled={isUploading || isCompressing || !videoFile}>
            {isCompressing ? 'Processing Video...' : isUploading ? `Uploading... ${uploadProgress}%` : isQueued ? 'Queued for Upload' : 'Submit Form Check'}
          </Button>
          {(isUploading || isCompressing) && <ProgressBar progress={uploadProgress} />}
        </form>
      </FormContainer>

      {(isUploading || isCompressing) && (
        <LoadingOverlay>
          <div>
            <LoadingSpinner size="large" />
            <LoadingText>
              {isCompressing ? 'Processing video...' : `Uploading video... ${uploadProgress}%`}
            </LoadingText>
          </div>
        </LoadingOverlay>
      )}
    </PageContainer>
  );
}; 