import React, { useState } from 'react';
import styled from 'styled-components';
import { Button } from '../../components/common/Button';

const AnalysisContainer = styled.div`
  min-height: 100vh;
  padding: ${({ theme }) => theme.spacing.xl};
  background-color: ${({ theme }) => theme.colors.background};
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const Title = styled.h1`
  color: ${({ theme }) => theme.colors.text};
`;

const AnalysisCard = styled.div`
  background-color: ${({ theme }) => theme.colors.white};
  padding: ${({ theme }) => theme.spacing.xl};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  box-shadow: ${({ theme }) => theme.shadows.md};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const VideoContainer = styled.div`
  width: 100%;
  max-width: 800px;
  margin: 0 auto ${({ theme }) => theme.spacing.xl};
  aspect-ratio: 16/9;
  background-color: ${({ theme }) => theme.colors.background};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
`;

const VideoPlaceholder = styled.div`
  color: ${({ theme }) => theme.colors.textSecondary};
  text-align: center;
`;

const AnalysisSection = styled.section`
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const SectionTitle = styled.h2`
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.md};
  font-size: ${({ theme }) => theme.typography.fontSize.xl};
`;

const FeedbackList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const FeedbackItem = styled.li`
  display: flex;
  align-items: flex-start;
  gap: ${({ theme }) => theme.spacing.md};
  padding: ${({ theme }) => theme.spacing.md};
  background-color: ${({ theme }) => theme.colors.background};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const FeedbackIcon = styled.div<{ type: 'success' | 'warning' | 'error' }>`
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: ${({ theme, type }) => {
    switch (type) {
      case 'success':
        return theme.colors.success;
      case 'warning':
        return theme.colors.warning;
      case 'error':
        return theme.colors.error;
      default:
        return theme.colors.textSecondary;
    }
  }};
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${({ theme }) => theme.colors.white};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

const FeedbackContent = styled.div`
  flex: 1;
`;

const FeedbackTitle = styled.h3`
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.xs};
  font-size: ${({ theme }) => theme.typography.fontSize.md};
`;

const FeedbackDescription = styled.p`
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.spacing.md};
  margin-top: ${({ theme }) => theme.spacing.xl};
`;

export const AnalysisPage: React.FC = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleStartRecording = () => {
    setIsRecording(true);
    // TODO: Implement video recording logic
  };

  const handleStopRecording = () => {
    setIsRecording(false);
    setIsAnalyzing(true);
    // TODO: Implement video analysis logic
  };

  const handleNewAnalysis = () => {
    setIsAnalyzing(false);
    // TODO: Reset analysis state
  };

  return (
    <AnalysisContainer>
      <Header>
        <Title>Form Analysis</Title>
      </Header>

      <AnalysisCard>
        <VideoContainer>
          {!isRecording && !isAnalyzing ? (
            <VideoPlaceholder>
              <p>Click "Start Recording" to begin form analysis</p>
            </VideoPlaceholder>
          ) : isRecording ? (
            <VideoPlaceholder>
              <p>Recording in progress...</p>
            </VideoPlaceholder>
          ) : (
            <VideoPlaceholder>
              <p>Analysis complete</p>
            </VideoPlaceholder>
          )}
        </VideoContainer>

        {!isAnalyzing ? (
          <ButtonGroup>
            {!isRecording ? (
              <Button variant="primary" onClick={handleStartRecording}>
                Start Recording
              </Button>
            ) : (
              <Button variant="secondary" onClick={handleStopRecording}>
                Stop Recording
              </Button>
            )}
          </ButtonGroup>
        ) : (
          <AnalysisSection>
            <SectionTitle>Analysis Results</SectionTitle>
            <FeedbackList>
              <FeedbackItem>
                <FeedbackIcon type="success">✓</FeedbackIcon>
                <FeedbackContent>
                  <FeedbackTitle>Good Form</FeedbackTitle>
                  <FeedbackDescription>
                    Your back is straight and your knees are properly aligned.
                  </FeedbackDescription>
                </FeedbackContent>
              </FeedbackItem>
              <FeedbackItem>
                <FeedbackIcon type="warning">!</FeedbackIcon>
                <FeedbackContent>
                  <FeedbackTitle>Minor Adjustment Needed</FeedbackTitle>
                  <FeedbackDescription>
                    Try to keep your elbows closer to your body during the movement.
                  </FeedbackDescription>
                </FeedbackContent>
              </FeedbackItem>
              <FeedbackItem>
                <FeedbackIcon type="error">×</FeedbackIcon>
                <FeedbackContent>
                  <FeedbackTitle>Form Correction Required</FeedbackTitle>
                  <FeedbackDescription>
                    Your lower back is arching. Focus on maintaining a neutral spine.
                  </FeedbackDescription>
                </FeedbackContent>
              </FeedbackItem>
            </FeedbackList>
            <ButtonGroup>
              <Button variant="primary" onClick={handleNewAnalysis}>
                New Analysis
              </Button>
            </ButtonGroup>
          </AnalysisSection>
        )}
      </AnalysisCard>
    </AnalysisContainer>
  );
}; 