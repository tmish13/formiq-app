import React from 'react';
import styled from 'styled-components';
import { FormValidationResult } from '../services/poseAnalysis/types';

interface FormFeedbackProps {
  feedback: FormValidationResult[];
  confidence: number;
  repetitionCount: number;
  phase: 'start' | 'middle' | 'end';
}

const Container = styled.div`
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.8);
  padding: 15px 25px;
  border-radius: 8px;
  max-width: 80%;
  z-index: 10;
`;

const FeedbackList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const BaseFeedbackItem = styled.li`
  font-size: 16px;
  margin: 5px 0;
  display: flex;
  align-items: center;
  
  &:before {
    margin-right: 8px;
    font-weight: bold;
  }
`;

const ValidFeedbackItem = styled(BaseFeedbackItem)`
  color: ${({ theme }) => theme.colors.success};
  
  &:before {
    content: "✓";
  }
`;

const InvalidFeedbackItem = styled(BaseFeedbackItem)`
  color: ${({ theme }) => theme.colors.error};
  
  &:before {
    content: "×";
  }
`;

const Stats = styled.div`
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
`;

const StatItem = styled.div`
  color: white;
  text-align: center;
  
  span {
    display: block;
    font-size: 12px;
    opacity: 0.7;
  }
  
  strong {
    font-size: 18px;
  }
`;

export const FormFeedback: React.FC<FormFeedbackProps> = ({
  feedback,
  confidence,
  repetitionCount,
  phase,
}) => {
  return (
    <Container data-testid="form-feedback">
      <FeedbackList>
        {feedback.map((item, index) => (
          item.isValid ? (
            <ValidFeedbackItem key={index}>
              {item.message}
            </ValidFeedbackItem>
          ) : (
            <InvalidFeedbackItem key={index}>
              {item.message}
            </InvalidFeedbackItem>
          )
        ))}
      </FeedbackList>
      
      <Stats>
        <StatItem>
          <span>Confidence</span>
          <strong>{Math.round(confidence * 100)}%</strong>
        </StatItem>
        <StatItem>
          <span>Reps</span>
          <strong>{repetitionCount}</strong>
        </StatItem>
        <StatItem>
          <span>Phase</span>
          <strong>{phase.charAt(0).toUpperCase() + phase.slice(1)}</strong>
        </StatItem>
      </Stats>
    </Container>
  );
}; 