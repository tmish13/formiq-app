import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { CameraService } from '../../services/CameraService';
import { UploadGuidance } from '../UploadGuidance';
import { LoadingSpinner } from '../atoms/LoadingSpinner';

const Container = styled.div`
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
`;

const VideoContainer = styled.div`
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
`;

const Controls = styled.div`
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
`;

const Button = styled.button<{ variant?: 'primary' | 'danger' }>`
  padding: 10px 20px;
  border-radius: 4px;
  border: none;
  background: ${({ variant, theme }) =>
    variant === 'danger' ? theme.colors.error.main : theme.colors.primary.main};
  color: white;
  cursor: pointer;
  font-size: 16px;
  
  &:hover {
    opacity: 0.9;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartRecording = async () => {
    try {
      await CameraService.startRecording();
      setIsRecording(true);
      setError(null);
    } catch (err) {
      setError('Failed to start recording. Please check camera permissions.');
    }
  };

  const handleStopRecording = async () => {
    try {
      setIsUploading(true);
      const { videoUrl } = await CameraService.stopRecording();
      setIsRecording(false);
      
      // Upload video for analysis
      const response = await fetch('/api/form-analysis/upload', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ videoUrl }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to upload video');
      }
      
      const { id } = await response.json();
      navigate(`/results/${id}`);
    } catch (err) {
      setError('Failed to upload video. Please try again.');
      setIsUploading(false);
    }
  };

  return (
    <Container>
      <UploadGuidance onChange={() => {}} />
      
      <VideoContainer>
        {isRecording && <video autoPlay muted />}
      </VideoContainer>
      
      <Controls>
        {!isRecording ? (
          <Button
            onClick={handleStartRecording}
            disabled={isUploading}
            data-testid="start-recording"
          >
            Start Recording
          </Button>
        ) : (
          <Button
            onClick={handleStopRecording}
            variant="danger"
            disabled={isUploading}
            data-testid="stop-recording"
          >
            Stop Recording
          </Button>
        )}
      </Controls>
      
      {isUploading && <LoadingSpinner />}
      {error && <div style={{ color: 'red', marginTop: '10px' }}>{error}</div>}
    </Container>
  );
}; 