import React from 'react';
import styled from 'styled-components';
import { useCameraPermissions } from '../../hooks/useCameraPermissions';
import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';

const FallbackContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: ${({ theme }) => theme.spacing.xl};
  text-align: center;
  min-height: 60vh;
`;

const Title = styled.h2`
  color: ${({ theme }) => theme.colors.primary};
  margin-bottom: ${({ theme }) => theme.spacing.md};
  font-size: 1.5rem;
`;

const Message = styled.p`
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.lg};
  max-width: 500px;
  line-height: 1.6;
`;

const Button = styled.button`
  background-color: ${({ theme }) => theme.colors.primary};
  color: white;
  border: none;
  border-radius: ${({ theme }) => theme.borderRadius.md};
  padding: ${({ theme }) => `${theme.spacing.sm} ${theme.spacing.lg}`};
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  margin: ${({ theme }) => theme.spacing.sm} 0;
  
  &:hover {
    background-color: ${({ theme }) => theme.colors.primaryDark};
  }
  
  &:disabled {
    background-color: ${({ theme }) => theme.colors.disabled};
    cursor: not-allowed;
  }
`;

const UploadContainer = styled.div`
  margin-top: ${({ theme }) => theme.spacing.lg};
  border: 2px dashed ${({ theme }) => theme.colors.border};
  padding: ${({ theme }) => theme.spacing.lg};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  width: 100%;
  max-width: 500px;
`;

const UploadLabel = styled.label`
  display: block;
  text-align: center;
  cursor: pointer;
  color: ${({ theme }) => theme.colors.primary};
`;

const UploadInput = styled.input`
  display: none;
`;

interface CameraPermissionFallbackProps {
  onFileUpload?: (file: File) => void;
  onRetry?: () => void;
}

/**
 * Fallback UI displayed when camera permissions are denied
 * Provides options to retry permission request or upload a file as alternative
 */
export const CameraPermissionFallback: React.FC<CameraPermissionFallbackProps> = ({
  onFileUpload,
  onRetry,
}) => {
  const { requestPermission, isLoading } = useCameraPermissions();
  const isNative = Capacitor.isNativePlatform();
  
  const handleRetry = async () => {
    const granted = await requestPermission();
    if (granted && onRetry) {
      onRetry();
    } else if (isNative) {
      // On native platforms, guide users to app settings
      App.openUrl({ url: 'app-settings:' });
    }
  };
  
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0 && onFileUpload) {
      onFileUpload(files[0]);
    }
  };
  
  return (
    <FallbackContainer>
      <Title>Camera Access Required</Title>
      
      <Message>
        To capture your form and provide analysis, we need permission to use your camera.
        You can either try again or upload a pre-recorded video.
      </Message>
      
      <Button onClick={handleRetry} disabled={isLoading}>
        {isLoading ? 'Loading...' : 'Try Again'}
      </Button>
      
      {isNative && (
        <Button onClick={() => App.openUrl({ url: 'app-settings:' })}>
          Open App Settings
        </Button>
      )}
      
      <UploadContainer>
        <UploadLabel>
          <UploadInput 
            type="file" 
            accept="video/*" 
            onChange={handleFileChange} 
          />
          Or click here to upload a video
        </UploadLabel>
      </UploadContainer>
    </FallbackContainer>
  );
}; 