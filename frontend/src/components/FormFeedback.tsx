import React from 'react';
import styled from 'styled-components';
import { FormValidationResult } from '../services/poseAnalysis/types';

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

const FeedbackItem = styled.li<{ isValid: boolean }>`
  color: ${({ isValid }) => (isValid ? '#4caf50' : '#ff5252')};
  font-size: 16px;
  margin: 5px 0;
  display: flex;
  align-items: center;
  
  &:before {
    content: ${({ isValid }) => (isValid ? '"✓"' : '"×"')};
    margin-right: 8px;
    font-weight: bold;
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

interface FormFeedbackProps {
  feedback: FormValidationResult[];
  confidence: number;
  repetitionCount: number;
  phase: 'start' | 'middle' | 'end';
}

export const FormFeedback: React.FC<FormFeedbackProps> = ({
  feedback,
  confidence,
  repetitionCount,
  phase,
}) => {
  return (
    <Container>
      <FeedbackList>
        {feedback.map((item, index) => (
          <FeedbackItem key={index} isValid={item.isValid}>
            {item.message}
          </FeedbackItem>
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