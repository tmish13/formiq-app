import React from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';

interface Analysis {
  score: number;
  feedback: string[];
  videoUrl: string;
}

interface ResultsDisplayProps {
  results: Analysis | null;
  onNewCheck: () => void;
}

const Container = styled(motion.div)`
  padding: ${({ theme }) => theme.spacing.lg};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  background-color: ${({ theme }) => theme.colors.background.paper};
  box-shadow: ${({ theme }) => theme.shadows.md};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const ScoreContainer = styled.div`
  text-align: center;
  margin-bottom: ${({ theme }) => theme.spacing.lg};
`;

const Score = styled.div<{ score: number }>`
  font-size: 3rem;
  font-weight: bold;
  color: ${({ score, theme }) => {
    if (score >= 80) return theme.colors.success;
    if (score >= 60) return theme.colors.warning;
    return theme.colors.error;
  }};
  margin-bottom: ${({ theme }) => theme.spacing.sm};
`;

const ScoreLabel = styled.div`
  font-size: 1.2rem;
  color: ${({ theme }) => theme.colors.text.secondary};
`;

const FeedbackTitle = styled.h3`
  margin-bottom: ${({ theme }) => theme.spacing.md};
  color: ${({ theme }) => theme.colors.text.primary};
`;

const FeedbackList = styled.ul`
  margin-bottom: ${({ theme }) => theme.spacing.lg};
  padding-left: ${({ theme }) => theme.spacing.lg};
`;

const FeedbackItem = styled.li`
  margin-bottom: ${({ theme }) => theme.spacing.sm};
  color: ${({ theme }) => theme.colors.text.primary};
`;

const VideoContainer = styled.div`
  margin-bottom: ${({ theme }) => theme.spacing.lg};
  width: 100%;
  border-radius: ${({ theme }) => theme.borderRadius.md};
  overflow: hidden;
`;

const Video = styled.video`
  width: 100%;
  height: auto;
`;

const Button = styled(motion.button)`
  background-color: ${({ theme }) => theme.colors.primary};
  color: white;
  border: none;
  border-radius: ${({ theme }) => theme.borderRadius.md};
  padding: ${({ theme }) => theme.spacing.md};
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  width: 100%;
  max-width: 300px;
  margin: 0 auto;
  display: block;
`;

const containerVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      staggerChildren: 0.1
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 }
};

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ results, onNewCheck }) => {
  if (!results) return null;

  return (
    <Container
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <ScoreContainer>
        <Score score={results.score}>{results.score}</Score>
        <ScoreLabel>Your Form Score</ScoreLabel>
      </ScoreContainer>

      {results.feedback.length > 0 && (
        <motion.div variants={itemVariants}>
          <FeedbackTitle>Feedback</FeedbackTitle>
          <FeedbackList>
            {results.feedback.map((item, index) => (
              <FeedbackItem key={index} data-testid="feedback-item">
                {item}
              </FeedbackItem>
            ))}
          </FeedbackList>
        </motion.div>
      )}

      {results.videoUrl && (
        <motion.div variants={itemVariants}>
          <VideoContainer>
            <Video src={results.videoUrl} controls />
          </VideoContainer>
        </motion.div>
      )}

      <Button
        onClick={onNewCheck}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        data-testid="new-check-btn"
      >
        New Check
      </Button>
    </Container>
  );
}; 