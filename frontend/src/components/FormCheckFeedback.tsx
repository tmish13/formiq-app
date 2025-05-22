import React from 'react';
import styled from 'styled-components';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';

export type FeedbackSeverity = 'good' | 'warning' | 'error';

interface FormCheckFeedbackProps {
  feedback: string;
  score: number;
  severity?: FeedbackSeverity;
}

const Container = styled.div`
  padding: ${props => props.theme.spacing.md};
  background: ${props => props.theme.colors.background.paper};
  border-radius: ${props => props.theme.borderRadius.md};
  box-shadow: ${props => props.theme.shadows.small};
  margin-bottom: ${props => props.theme.spacing.md};
`;

const Score = styled.div`
  font-size: ${props => props.theme.typography.fontSize.lg};
  font-weight: ${props => props.theme.typography.fontWeight.semibold};
  margin-bottom: ${props => props.theme.spacing.sm};
  color: ${props => props.theme.colors.text.primary};
`;

interface FeedbackTextProps {
  severity: FeedbackSeverity;
}

const FeedbackText = styled.div<FeedbackTextProps>`
  color: ${props => {
    switch (props.severity) {
      case 'good':
        return props.theme.colors.success.main;
      case 'warning':
        return props.theme.colors.warning.main;
      case 'error':
        return props.theme.colors.error.main;
      default:
        return props.theme.colors.text.secondary;
    }
  }};
  line-height: ${props => props.theme.typography.lineHeight.normal};
  display: flex;
  align-items: center;
  gap: ${props => props.theme.spacing.sm};
`;

const FormCheckFeedback: React.FC<FormCheckFeedbackProps> = ({ 
  feedback, 
  score, 
  severity = 'good'  // Default to good if not specified
}) => {
  const renderIcon = () => {
    switch (severity) {
      case 'good':
        return <CheckCircleIcon data-testid="good-icon" aria-label="Success" color="success" />;
      case 'warning':
        return <WarningIcon data-testid="warning-icon" aria-label="Warning" color="warning" />;
      case 'error':
        return <ErrorIcon data-testid="error-icon" aria-label="Error" color="error" />;
      default:
        return null;
    }
  };

  return (
    <Container data-testid="form-check-feedback">
      <Score data-testid="score">Form Check Score: {score}%</Score>
      <FeedbackText severity={severity} data-testid={`feedback-${severity}`}>
        {renderIcon()}
        <span>{feedback}</span>
      </FeedbackText>
    </Container>
  );
};

export default FormCheckFeedback; 