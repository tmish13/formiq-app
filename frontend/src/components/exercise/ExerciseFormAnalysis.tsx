import React, { useState, useRef, useEffect, lazy, Suspense } from 'react';
import styled from 'styled-components';
import { CameraCapture } from '../camera/CameraCapture';
import { PoseAnalysis } from '../camera/PoseAnalysis';
import { AnalysisResults as AnalysisResultsComponent } from './AnalysisResults';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorMessage } from '../common/ErrorMessage';
import { Button } from '../common/Button';
import { CircularProgress } from '@mui/material';
import { handleApiError, type ApiError } from '../../utils/errorHandling';
import { errorHandlingService } from '../../services/errorHandlingService';
import type { VideoAnalyzerProps } from './VideoAnalyzer/index';

// Lazy-loaded components for better performance
const ResultsDisplay = lazy(() => import('./ResultsDisplay'));
const VideoAnalyzer = lazy(() => import('./VideoAnalyzer'));

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.lg', '1.5rem')};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.paper', '#ffffff')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.lg', '0.5rem')};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.medium', '0 2px 4px rgba(0,0,0,0.1)')};
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
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.color.background)};
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
        return getThemeValue(theme, 'colors.success.light', '#81c784');
      case 'warning':
        return getThemeValue(theme, 'colors.warning.light', '#ffb74d');
      case 'error':
        return getThemeValue(theme, 'colors.error.light', '#e57373');
      default:
        return getThemeValue(theme, 'colors.background.main', '#ffffff');
    }
  }};
  color: ${({ theme, type }) => {
    switch (type) {
      case 'success':
        return getThemeValue(theme, 'colors.success.main', '#4caf50');
      case 'warning':
        return getThemeValue(theme, 'colors.warning.main', '#ff9800');
      case 'error':
        return getThemeValue(theme, 'colors.error.main', '#f44336');
      default:
        return getThemeValue(theme, 'colors.text.primary', '#000000');
    }
  }};
`;

const LoadingPlaceholder = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: ${({ theme }) => theme.colors.background.main};
  border-radius: 8px;
  padding: ${({ theme }) => theme.spacing.md}px;
  min-height: 300px;
  
  &::after {
    content: "Loading...";
    color: ${({ theme }) => theme.colors.text.secondary};
  }
`;

const ProgressBar = styled.div`
  width: 100%;
  height: 4px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', '#f0f0f0')};
  border-radius: 2px;
  overflow: hidden;
  margin: 16px 0;
`;

const ProgressFill = styled.div<{ progress: number }>`
  height: 100%;
  width: ${({ progress }) => `${progress}%`};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', '#4a90e2')};
  transition: width 0.3s ease-in-out;
`;

const LoadingOverlay = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
`;

const LoadingText = styled.p`
  margin-top: 16px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', '#333')};
  font-size: 16px;
`;

const LoadingContainer = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
`;

interface ExerciseFormAnalysisProps {
  exerciseType: string;
  onAnalysisComplete: (analysis: {
    score: number;
    feedback: string[];
    videoUrl: string;
  }) => void;
}

export const ExerciseFormAnalysis: React.FC<ExerciseFormAnalysisProps> = ({
  exerciseType,
  onAnalysisComplete,
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<ApiError | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [analysisResults, setAnalysisResults] = useState<{
    score: number;
    feedback: string[];
    videoUrl: string;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Reset state when exercise type changes
    setVideoFile(null);
    setIsAnalyzing(false);
    setAnalysisResults(null);
  }, [exerciseType]);

  useEffect(() => {
    let progressInterval: ReturnType<typeof setInterval>;
    if (isAnalyzing) {
      progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 500);
    } else {
      setProgress(0);
    }
    return () => clearInterval(progressInterval);
  }, [isAnalyzing]);

  const handleError = (error: unknown) => {
    const appError = handleApiError(error);
    setError(appError);
    errorHandlingService.handleError(error instanceof Error ? error : new Error(String(error)), {
      severity: 'error',
      source: 'client',
      context: { 
        component: 'ExerciseFormAnalysis',
        exerciseType 
      }
    });
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setVideoFile(event.target.files[0]);
      setAnalysisResults(null);
      setError(null);
    }
  };

  const handleAnalyzeClick = async () => {
    if (!videoFile) return;

    try {
      setIsAnalyzing(true);
      setError(null);
      setAnalysisResults(null);

      // Simulate analysis process
      await new Promise(resolve => setTimeout(resolve, 5000));
      setProgress(100);

      const mockResults = {
        score: Math.floor(Math.random() * 100),
        feedback: ["Great form! Keep your back straight throughout the exercise."],
        videoUrl: URL.createObjectURL(videoFile)
      };

      setAnalysisResults(mockResults);
      onAnalysisComplete(mockResults);
    } catch (err) {
      handleError(err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRetry = () => {
    setError(null);
    setIsAnalyzing(false);
    handleAnalyzeClick();
  };

  // Memoize the loading state component
  const LoadingState = React.memo(() => (
    <LoadingContainer>
      <CircularProgress size={40} />
      <LoadingText>Analyzing exercise form...</LoadingText>
      <ProgressBar>
        <ProgressFill progress={progress} />
      </ProgressBar>
    </LoadingContainer>
  ));

  // Memoize the file selection UI
  const FileSelectionUI = React.memo(() => (
    <>
      <input
        type="file"
        ref={fileInputRef}
        accept="video/*"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
      <Button onClick={() => fileInputRef.current?.click()} disabled={isAnalyzing}>
        Select Video
      </Button>
    </>
  ));

  return (
    <Container>
      {isAnalyzing ? (
        <LoadingState />
      ) : error ? (
        <ErrorMessage error={error} onRetry={handleRetry} />
      ) : (
        <>
          <FileSelectionUI />

          {videoFile && (
            <Button onClick={handleAnalyzeClick} disabled={isAnalyzing}>
              Analyze Form
            </Button>
          )}

          {videoFile && (
            <Suspense fallback={<LoadingSpinner />}>
              <VideoAnalyzer 
                videoFile={videoFile} 
                exerciseType={exerciseType}
                isAnalyzing={isAnalyzing}
                onError={handleError}
                onAnalysisStart={() => setIsAnalyzing(true)}
              />
            </Suspense>
          )}
          
          {analysisResults && (
            <Suspense fallback={<LoadingSpinner />}>
              <ResultsDisplay 
                score={analysisResults.score}
                feedback={analysisResults.feedback}
                videoUrl={analysisResults.videoUrl}
              />
            </Suspense>
          )}
        </>
      )}
    </Container>
  );
}; 