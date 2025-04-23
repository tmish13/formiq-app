import React, { useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { getThemeValue } from '../../../utils/themeUtils';
import type { VideoAnalyzerProps } from './index';

const VideoContainer = styled.div`
  position: relative;
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '8px')};
  overflow: hidden;
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', '0 4px 6px rgba(0,0,0,0.1)')};
`;

const Video = styled.video`
  width: 100%;
  height: auto;
  display: block;
`;

const VideoAnalyzer: React.FC<VideoAnalyzerProps> = ({
  videoFile,
  exerciseType,
  isAnalyzing,
  onError,
  onAnalysisStart,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');

  useEffect(() => {
    if (videoFile) {
      const url = URL.createObjectURL(videoFile);
      setVideoUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [videoFile]);

  useEffect(() => {
    if (isAnalyzing && videoRef.current) {
      try {
        videoRef.current.currentTime = 0;
        videoRef.current.play();
        onAnalysisStart();
      } catch (error) {
        onError(error);
      }
    }
  }, [isAnalyzing, onAnalysisStart, onError]);

  return (
    <VideoContainer>
      <Video
        ref={videoRef}
        src={videoUrl}
        controls={!isAnalyzing}
        playsInline
        muted
        loop={isAnalyzing}
      />
    </VideoContainer>
  );
};

export default VideoAnalyzer; 