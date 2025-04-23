import React from 'react';
import styled, { DefaultTheme } from 'styled-components';
import { ApiError } from '../../utils/errorHandling';
import { getThemeValue } from '../../utils/themeUtils';

interface ErrorMessageProps {
  error: ApiError | null;
  onRetry?: () => void;
}

const ErrorContainer = styled.div<{ theme: DefaultTheme }>`
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '8px')};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.error.light', '#ffebee')};
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
  margin: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')} 0;
`;

const ErrorTitle = styled.h3<{ theme: DefaultTheme }>`
  margin: 0 0 ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.5rem')};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.lg', '1.25rem')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', '700')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
`;

const ErrorText = styled.p<{ theme: DefaultTheme }>`
  margin: 0;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', '1rem')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', '#000000')};
`;

const RetryButton = styled.button<{ theme: DefaultTheme }>`
  margin-top: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.5rem')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.5rem')} ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', '#f44336')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.inverse', '#ffffff')};
  border: none;
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '8px')};
  cursor: pointer;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', '0.875rem')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
  transition: background-color ${({ theme }) => getThemeValue(theme, 'transitions.duration.medium', '0.3s')} ${({ theme }) => getThemeValue(theme, 'transitions.easing.easeInOut', 'cubic-bezier(0.4, 0, 0.2, 1)')};

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.error.dark', '#d32f2f')};
  }

  &:focus {
    outline: none;
    box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.small', '0 1px 3px rgba(0,0,0,0.12)')};
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