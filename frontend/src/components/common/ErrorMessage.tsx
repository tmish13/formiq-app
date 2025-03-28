import React from 'react';
import styled from 'styled-components';
import { ApiError } from '../../utils/errorHandling';

interface ErrorMessageProps {
  error: ApiError | null;
  onRetry?: () => void;
}

const ErrorContainer = styled.div`
  padding: ${({ theme }) => theme.spacing.md};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  background-color: ${({ theme }) => theme.colors.errorLight};
  border: 1px solid ${({ theme }) => theme.colors.error};
  color: ${({ theme }) => theme.colors.errorDark};
  margin: ${({ theme }) => theme.spacing.md} 0;
`;

const ErrorTitle = styled.h3`
  margin: 0 0 ${({ theme }) => theme.spacing.sm};
  font-size: ${({ theme }) => theme.typography.fontSize.lg};
  font-weight: ${({ theme }) => theme.typography.fontWeight.semibold};
`;

const ErrorText = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.typography.fontSize.base};
`;

const RetryButton = styled.button`
  margin-top: ${({ theme }) => theme.spacing.sm};
  padding: ${({ theme }) => theme.spacing.sm} ${({ theme }) => theme.spacing.md};
  background-color: ${({ theme }) => theme.colors.error};
  color: ${({ theme }) => theme.colors.white};
  border: none;
  border-radius: ${({ theme }) => theme.borderRadius.md};
  cursor: pointer;
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  transition: background-color ${({ theme }) => theme.transitions.fast};

  &:hover {
    background-color: ${({ theme }) => theme.colors.errorDark};
  }
`;

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ error, onRetry }) => {
  if (!error) return null;

  return (
    <ErrorContainer>
      <ErrorTitle>Error {error.status}</ErrorTitle>
      <ErrorText>{error.message}</ErrorText>
      {error.details && (
        <ErrorText>
          <strong>Details:</strong> {JSON.stringify(error.details)}
        </ErrorText>
      )}
      {onRetry && (
        <RetryButton onClick={onRetry}>
          Try Again
        </RetryButton>
      )}
    </ErrorContainer>
  );
}; 