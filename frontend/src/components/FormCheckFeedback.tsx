import React from 'react';
import styled from 'styled-components';

interface FormCheckFeedbackProps {
  feedback: string;
  score: number;
}

const Container = styled.div`
  padding: ${props => props.theme.spacing.md};
  background: ${props => props.theme.colors.background.paper};
  border-radius: ${props => props.theme.borderRadius.md};
  box-shadow: ${props => props.theme.shadows.small};
`;

const Score = styled.div`
  font-size: ${props => props.theme.typography.fontSize.lg};
  font-weight: ${props => props.theme.typography.fontWeight.semibold};
  margin-bottom: ${props => props.theme.spacing.sm};
  color: ${props => props.theme.colors.text.primary};
`;

const FeedbackText = styled.div`
  color: ${props => props.theme.colors.text.secondary};
  line-height: ${props => props.theme.typography.lineHeight.normal};
`;

const FormCheckFeedback: React.FC<FormCheckFeedbackProps> = ({ feedback, score }) => {
  return (
    <Container data-testid="form-check-feedback">
      <Score>Form Check Score: {score}%</Score>
      <FeedbackText>{feedback}</FeedbackText>
    </Container>
  );
};

export default FormCheckFeedback; 