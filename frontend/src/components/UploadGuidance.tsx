import React from 'react';
import styled from 'styled-components';
import OnboardingTooltip from './onboarding/OnboardingTooltip';

interface UploadGuidanceProps {
  onChange: (files: FileList | null) => void;
}

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.md}px;
`;

const UploadBox = styled.div`
  border: 2px dashed ${({ theme }) => theme.colors.primary.main};
  border-radius: 8px;
  padding: ${({ theme }) => theme.spacing.lg}px;
  width: 100%;
  max-width: 500px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: ${({ theme }) => theme.colors.background};
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: rgba(0, 0, 0, 0.02);
  }
`;

const Icon = styled.div`
  font-size: 48px;
  color: ${({ theme }) => theme.colors.primary.main};
  margin-bottom: ${({ theme }) => theme.spacing.sm}px;
`;

const Text = styled.p`
  text-align: center;
  margin: ${({ theme }) => theme.spacing.sm}px 0;
  color: ${({ theme }) => theme.colors.text};
`;

const HiddenInput = styled.input`
  display: none;
`;

const GuidanceList = styled.ul`
  list-style-type: none;
  padding: 0;
  margin: ${({ theme }) => theme.spacing.md}px 0;
  width: 100%;
  max-width: 500px;
`;

const GuidanceItem = styled.li`
  display: flex;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.sm}px;
  color: ${({ theme }) => theme.colors.text};
  
  &:before {
    content: "✓";
    color: ${({ theme }) => theme.colors.success.main};
    margin-right: ${({ theme }) => theme.spacing.sm}px;
    font-weight: bold;
  }
`;

export const UploadGuidance: React.FC<UploadGuidanceProps> = ({ onChange }) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  
  const handleClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };
  
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onChange(event.target.files);
  };
  
  const uploadGuidanceItems = [
    "Position your camera to capture your full body during the exercise",
    "Ensure good lighting conditions",
    "Record from the side angle for best form analysis",
    "Keep the camera stable during recording",
    "Wear clothing that allows form visibility"
  ];
  
  return (
    <Container>
      <OnboardingTooltip
        id="form-upload"
        content={
          <div>
            <p>Upload a video of your exercise to get form feedback.</p>
            <p>We support MP4, WebM, and MOV files up to 100MB.</p>
          </div>
        }
        position="top"
      >
        <UploadBox onClick={handleClick}>
          <Icon>📤</Icon>
          <Text>Drag & drop your video here or click to browse</Text>
          <Text style={{ fontSize: '14px', opacity: 0.7 }}>
            Supported formats: MP4, WebM, MOV
          </Text>
          <HiddenInput
            type="file"
            ref={fileInputRef}
            onChange={handleChange}
            accept="video/mp4,video/webm,video/quicktime"
          />
        </UploadBox>
      </OnboardingTooltip>
      
      <OnboardingTooltip
        id="recording-tips"
        content="Following these guidelines will help our AI provide the most accurate form feedback."
        position="bottom"
        showOnlyOnce={false}
      >
        <GuidanceList>
          {uploadGuidanceItems.map((item, index) => (
            <GuidanceItem key={index}>{item}</GuidanceItem>
          ))}
        </GuidanceList>
      </OnboardingTooltip>
    </Container>
  );
};

export default UploadGuidance; 