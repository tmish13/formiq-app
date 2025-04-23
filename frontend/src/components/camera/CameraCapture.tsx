import React, { useState, useCallback, useEffect } from 'react';
import styled from 'styled-components';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Filesystem, Directory } from '@capacitor/filesystem';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { FormTipsOverlay, FormTip } from './FormTipsOverlay';

// Styled components
const CaptureContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
`;

const VideoPreview = styled.video`
  width: 100%;
  max-height: 70vh;
  border-radius: 8px;
  margin-bottom: 16px;
  background-color: ${({ theme }) => theme.colors.secondaryLight};
`;

const ButtonsContainer = styled.div`
  display: flex;
  justify-content: center;
  gap: 16px;
  width: 100%;
  margin-top: 16px;
`;

const CaptureButton = styled.button`
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.color.primary)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    transform: scale(1.05);
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.primaryDark', fallbacks.color.primaryDark)};
  }
  
  &:disabled {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.color.disabled)};
    cursor: not-allowed;
    transform: none;
  }
`;

const ActionButton = styled.button`
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.secondary', fallbacks.color.secondary)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  border: none;
  border-radius: 8px;
  padding: 12px 16px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.secondaryDark', fallbacks.color.secondaryDark)};
  }
  
  &:disabled {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.color.disabled)};
    cursor: not-allowed;
  }
`;

const ErrorMessage = styled.div`
  color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.color.error)};
  margin: 16px 0;
  padding: 8px 16px;
  border-radius: 4px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.errorLight', fallbacks.color.errorLight)};
  width: 100%;
  text-align: center;
`;

const FileInput = styled.input`
  display: none;
`;

const VideoWrapper = styled.div`
  position: relative;
  width: 100%;
  max-height: 70vh;
  border-radius: 8px;
  overflow: hidden;
`;

// Mock form tips data
const mockFormTips: Record<string, FormTip[]> = {
  squat: [
    {
      id: 'squat-1',
      message: 'Knees slightly too forward',
      type: 'warning',
      position: { top: '30%', left: '50%' },
    },
    {
      id: 'squat-2',
      message: 'Keep your back straight',
      type: 'error',
      position: { top: '40%', left: '30%' },
    },
  ],
  pushup: [
    {
      id: 'pushup-1',
      message: 'Lower your chest closer to the ground',
      type: 'warning',
      position: { top: '50%', left: '40%' },
    },
    {
      id: 'pushup-2',
      message: 'Keep your core tight',
      type: 'success',
      position: { top: '60%', left: '60%' },
    },
  ],
  deadlift: [
    {
      id: 'deadlift-1',
      message: 'Bend your knees more',
      type: 'warning',
      position: { top: '40%', left: '50%' },
    },
    {
      id: 'deadlift-2',
      message: 'Keep the bar close to your body',
      type: 'error',
      position: { top: '50%', left: '30%' },
    },
  ],
  lunge: [
    {
      id: 'lunge-1',
      message: 'Front knee over toes',
      type: 'warning',
      position: { top: '40%', left: '40%' },
    },
    {
      id: 'lunge-2',
      message: 'Keep torso upright',
      type: 'success',
      position: { top: '50%', left: '60%' },
    },
  ],
};

interface CameraCaptureProps {
  onVideoCapture: (videoFile: File, thumbnailFile?: File) => void;
  maxDuration?: number; // in seconds
  exerciseType?: string;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({ 
  onVideoCapture, 
  maxDuration = 60,
  exerciseType = 'squat'
}) => {
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isMobile] = useState(Capacitor.isNativePlatform());
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [currentTips, setCurrentTips] = useState<FormTip[]>(mockFormTips[exerciseType] || []);
  const [formScore, setFormScore] = useState(85);

  // Simulate form tips updates
  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        setCurrentTips(prevTips => {
          const newTips = prevTips.map(tip => ({
            ...tip,
            position: {
              top: `${Math.random() * 60 + 20}%`,
              left: `${Math.random() * 60 + 20}%`,
            },
          }));
          return newTips;
        });
        
        // Randomly update form score
        setFormScore(prev => Math.max(0, Math.min(100, prev + (Math.random() * 10 - 5))));
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [isRecording]);

  // Function to handle file selection
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('video/')) {
        const videoUrl = URL.createObjectURL(file);
        setVideoSrc(videoUrl);
        
        // Create a thumbnail
        const video = document.createElement('video');
        video.src = videoUrl;
        video.muted = true;
        
        video.onloadeddata = () => {
          video.currentTime = 1; // Set to 1 second
          
          setTimeout(() => {
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            if (ctx) {
              ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
              canvas.toBlob((thumbnailBlob) => {
                if (thumbnailBlob) {
                  const thumbnailFile = new File(
                    [thumbnailBlob], 
                    `thumbnail_${file.name.replace(/\.[^/.]+$/, '.jpg')}`, 
                    { type: 'image/jpeg' }
                  );
                  onVideoCapture(file, thumbnailFile);
                } else {
                  onVideoCapture(file);
                }
              }, 'image/jpeg', 0.7);
            } else {
              onVideoCapture(file);
            }
          }, 500);
        };
      } else {
        setError('Please select a video file');
      }
    }
  };

  // Function to capture video
  const captureVideo = useCallback(async () => {
    try {
      setError(null);
      
      // For mobile (native) platforms, use input file or prompt for video selection
      if (isMobile) {
        // For now, we'll use the file input as Capacitor Camera doesn't directly support video recording
        // We could use a native plugin like @capacitor/camera-preview in a future update
        if (fileInputRef.current) {
          fileInputRef.current.click();
        }
      } 
      // For web platforms
      else {
        // Use the MediaDevices API for web
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const chunks: BlobPart[] = [];
        
        mediaRecorder.ondataavailable = (e) => {
          chunks.push(e.data);
        };
        
        mediaRecorder.onstop = () => {
          const blob = new Blob(chunks, { type: 'video/mp4' });
          const videoUrl = URL.createObjectURL(blob);
          setVideoSrc(videoUrl);
          
          const fileName = `formiq_video_${new Date().getTime()}.mp4`;
          const file = new File([blob], fileName, { type: 'video/mp4' });
          
          // Create a thumbnail
          const video = document.createElement('video');
          video.src = videoUrl;
          video.muted = true;
          
          video.onloadeddata = () => {
            video.currentTime = 1; // Set to 1 second
            
            setTimeout(() => {
              const canvas = document.createElement('canvas');
              canvas.width = video.videoWidth;
              canvas.height = video.videoHeight;
              const ctx = canvas.getContext('2d');
              if (ctx) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                canvas.toBlob((thumbnailBlob) => {
                  if (thumbnailBlob) {
                    const thumbnailFile = new File(
                      [thumbnailBlob], 
                      `thumbnail_${fileName}`.replace('.mp4', '.jpg'), 
                      { type: 'image/jpeg' }
                    );
                    onVideoCapture(file, thumbnailFile);
                  } else {
                    onVideoCapture(file);
                  }
                }, 'image/jpeg', 0.7);
              } else {
                onVideoCapture(file);
              }
            }, 500);
          };
          
          // Clean up
          stream.getTracks().forEach((track) => track.stop());
        };
        
        setIsRecording(true);
        
        // Stop recording after maxDuration
        mediaRecorder.start();
        
        setTimeout(() => {
          if (mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
            setIsRecording(false);
          }
        }, maxDuration * 1000);
      }
    } catch (error) {
      console.error('Error capturing video', error);
      setError('Failed to access camera. Please make sure you have given permission to access the camera.');
    }
  }, [isMobile, maxDuration, onVideoCapture]);

  // Function to cancel recording
  const cancelRecording = () => {
    if (videoSrc) {
      URL.revokeObjectURL(videoSrc);
      setVideoSrc(null);
    }
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Function to handle retrying after an error
  const retryCapture = () => {
    setError(null);
    captureVideo();
  };

  return (
    <CaptureContainer>
      <VideoWrapper>
        <VideoPreview
          src={videoSrc || undefined}
          autoPlay
          playsInline
          muted
        />
        {isRecording && (
          <FormTipsOverlay
            tips={currentTips}
            score={formScore}
          />
        )}
      </VideoWrapper>

      <ButtonsContainer>
        {!videoSrc ? (
          <CaptureButton
            onClick={captureVideo}
            disabled={isRecording}
          >
            {isRecording ? 'Recording...' : 'Start Recording'}
          </CaptureButton>
        ) : (
          <>
            <ActionButton onClick={cancelRecording}>
              Cancel
            </ActionButton>
            <CaptureButton onClick={captureVideo}>
              Record Again
            </CaptureButton>
          </>
        )}
      </ButtonsContainer>

      {error && <ErrorMessage>{error}</ErrorMessage>}
      <FileInput
        type="file"
        accept="video/*"
        onChange={handleFileChange}
        ref={fileInputRef}
      />
    </CaptureContainer>
  );
}; 