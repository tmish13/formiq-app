import React from 'react';
import styled from 'styled-components';

interface ResultsDisplayProps {
  score: number;
  feedback: string[];
  videoUrl: string;
}

const Container = styled.div`
  margin-top: 30px;
  padding: 20px;
  border-radius: 8px;
  background-color: ${({ theme }) => theme.colors.background.light};
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h2`
  margin-top: 0;
  color: ${({ theme }) => theme.colors.text.primary};
  margin-bottom: 20px;
`;

const ResultCard = styled.div`
  display: flex;
  margin-bottom: 30px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const ScoreSection = styled.div<{ score: number }>`
  flex: 0 0 150px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background-color: ${({ score, theme }) => {
    if (score >= 80) return theme.colors.success.main;
    if (score >= 60) return theme.colors.warning.main;
    return theme.colors.error.main;
  }};
  color: white;
`;

const ScoreValue = styled.div`
  font-size: 3rem;
  font-weight: bold;
`;

const ScoreLabel = styled.div`
  font-size: 1rem;
  margin-top: 5px;
`;

const FeedbackSection = styled.div`
  flex: 1;
  padding: 20px;
  background-color: white;
`;

const FeedbackTitle = styled.h3`
  margin-top: 0;
  margin-bottom: 15px;
  color: ${({ theme }) => theme.colors.text.primary};
`;

const FeedbackList = styled.ul`
  margin: 0;
  padding-left: 20px;
`;

const FeedbackItem = styled.li`
  margin-bottom: 10px;
  color: ${({ theme }) => theme.colors.text.primary};
  
  &:last-child {
    margin-bottom: 0;
  }
`;

const VideoTitle = styled.h3`
  margin-top: 0;
  color: ${({ theme }) => theme.colors.text.primary};
  margin-bottom: 15px;
`;

const VideoPlayer = styled.video`
  width: 100%;
  border-radius: 8px;
`;

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ score, feedback, videoUrl }) => {
  const getScoreLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Needs Improvement';
  };

  return (
    <Container>
      <Title>Form Analysis Results</Title>
      
      <ResultCard>
        <ScoreSection score={score}>
          <ScoreValue>{score}</ScoreValue>
          <ScoreLabel>{getScoreLabel(score)}</ScoreLabel>
        </ScoreSection>
        
        <FeedbackSection>
          <FeedbackTitle>Feedback</FeedbackTitle>
          <FeedbackList>
            {feedback.map((item, index) => (
              <FeedbackItem key={index}>{item}</FeedbackItem>
            ))}
          </FeedbackList>
        </FeedbackSection>
      </ResultCard>
      
      <VideoTitle>Your Form Video</VideoTitle>
      <VideoPlayer src={videoUrl} controls />
    </Container>
  );
};

export default ResultsDisplay; 