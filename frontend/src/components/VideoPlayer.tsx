import React, { useState } from 'react';
import styled from 'styled-components';
import { LoadingSpinner } from './atoms/LoadingSpinner';

interface VideoPlayerProps {
  src: string;
  poster?: string;
  className?: string;
}

const VideoContainer = styled.div`
  width: 100%;
  aspect-video;
  position: relative;
  background: ${props => props.theme.colors.background.main};
`;

const StyledVideo = styled.video`
  width: 100%;
  height: 100%;
  object-fit: contain;
`;

const ErrorMessage = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: ${props => props.theme.colors.error.main};
  text-align: center;
`;

const VideoPlayer: React.FC<VideoPlayerProps> = ({ src, poster, className }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const handleLoadStart = () => {
    setIsLoading(true);
    setHasError(false);
  };

  const handleCanPlay = () => {
    setIsLoading(false);
  };

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  return (
    <VideoContainer className={className} data-testid="video-player">
      {isLoading && <LoadingSpinner size="50px" dataTestId="video-loading" />}
      {hasError ? (
        <ErrorMessage data-testid="video-error">
          Failed to load video. Please try again.
        </ErrorMessage>
      ) : (
        <StyledVideo
          src={src}
          poster={poster}
          controls
          onLoadStart={handleLoadStart}
          onCanPlay={handleCanPlay}
          onError={handleError}
        />
      )}
    </VideoContainer>
  );
};

export default VideoPlayer; 