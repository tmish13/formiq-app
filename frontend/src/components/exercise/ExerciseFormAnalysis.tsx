import React, { useRef, useState } from 'react';
import styled from 'styled-components';
import { CameraCapture } from '../camera/CameraCapture';
import { PoseAnalysis } from '../camera/PoseAnalysis';
import { AnalysisResults as AnalysisResultsComponent } from './AnalysisResults';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
`;

const VideoContainer = styled.div`
  position: relative;
  width: 100%;
  max-width: 600px;
  margin-bottom: 20px;
`;

const AnalysisResults = styled.div`
  width: 100%;
  padding: 20px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const ScoreContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
`;

const Score = styled.div<{ score: number }>`
  font-size: 24px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  color: ${({ score }) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 70) return '#FFC107';
    return '#F44336';
  }};
`;

const FeedbackList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const FeedbackItem = styled.li<{ type: 'success' | 'warning' | 'error' }>`
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  background-color: ${({ theme, type }) => {
    switch (type) {
      case 'success':
        return getThemeValue(theme, 'colors.successLight', fallbacks.colors.successLight);
      case 'warning':
        return getThemeValue(theme, 'colors.warningLight', fallbacks.colors.warningLight);
      case 'error':
        return getThemeValue(theme, 'colors.errorLight', fallbacks.colors.errorLight);
      default:
        return getThemeValue(theme, 'colors.background', fallbacks.colors.background);
    }
  }};
  color: ${({ theme, type }) => {
    switch (type) {
      case 'success':
        return getThemeValue(theme, 'colors.success', fallbacks.colors.success);
      case 'warning':
        return getThemeValue(theme, 'colors.warning', fallbacks.colors.warning);
      case 'error':
        return getThemeValue(theme, 'colors.error', fallbacks.colors.error);
      default:
        return getThemeValue(theme, 'colors.text', fallbacks.colors.text);
    }
  }};
`;

interface ExerciseFormAnalysisProps {
  exerciseType: string;
  onAnalysisComplete?: (analysis: {
    score: number;
    feedback: string[];
    videoUrl: string;
  }) => void;
}

export const ExerciseFormAnalysis: React.FC<ExerciseFormAnalysisProps> = ({
  exerciseType,
  onAnalysisComplete,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [analysisResults, setAnalysisResults] = useState<{
    score: number;
    feedback: string[];
  } | null>(null);

  const handleVideoCapture = (videoFile: File) => {
    const url = URL.createObjectURL(videoFile);
    setVideoUrl(url);
    if (videoRef.current) {
      videoRef.current.src = url;
    }
  };

  const handleAnalysisComplete = (analysis: {
    score: number;
    feedback: string[];
    keypoints: any[];
  }) => {
    setAnalysisResults({
      score: analysis.score,
      feedback: analysis.feedback,
    });

    if (onAnalysisComplete && videoUrl) {
      onAnalysisComplete({
        score: analysis.score,
        feedback: analysis.feedback,
        videoUrl,
      });
    }
  };

  return (
    <Container>
      <VideoContainer>
        {!videoUrl ? (
          <CameraCapture 
            onVideoCapture={handleVideoCapture} 
            maxDuration={60}
            exerciseType={exerciseType}
          />
        ) : (
          <>
            <video
              ref={videoRef}
              style={{ width: '100%', display: 'none' }}
              playsInline
              muted
            />
            {videoRef.current && (
              <PoseAnalysis
                videoRef={videoRef}
                exerciseType={exerciseType}
                onAnalysisComplete={handleAnalysisComplete}
              />
            )}
          </>
        )}
      </VideoContainer>

      {analysisResults && videoUrl && (
        <AnalysisResultsComponent
          score={analysisResults.score}
          feedback={analysisResults.feedback}
          videoUrl={videoUrl}
        />
      )}
    </Container>
  );
}; 