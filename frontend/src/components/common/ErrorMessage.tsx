import React from 'react';
import styled, { DefaultTheme } from 'styled-components';
import { ApiError } from '../../utils/errorHandling';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface ErrorMessageProps {
  error: ApiError | null;
  onRetry?: () => void;
}

const ErrorContainer = styled.div<{ theme: DefaultTheme }>`
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', fallbacks.spacing.md)};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', fallbacks.borderRadius.md)};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.errorLight', fallbacks.colors.errorLight)};
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
  margin: ${({ theme }) => getThemeValue(theme, 'spacing.md', fallbacks.spacing.md)} 0;
`;

const ErrorTitle = styled.h3<{ theme: DefaultTheme }>`
  margin: 0 0 ${({ theme }) => getThemeValue(theme, 'spacing.sm', fallbacks.spacing.sm)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.lg', fallbacks.typography.fontSize.lg)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', String(fallbacks.typography.fontWeight.bold))};
`;

const ErrorText = styled.p<{ theme: DefaultTheme }>`
  margin: 0;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', fallbacks.typography.fontSize.md)};
`;

const RetryButton = styled.button<{ theme: DefaultTheme }>`
  margin-top: ${({ theme }) => getThemeValue(theme, 'spacing.sm', fallbacks.spacing.sm)};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', fallbacks.spacing.sm)} ${({ theme }) => getThemeValue(theme, 'spacing.md', fallbacks.spacing.md)};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  border: none;
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', fallbacks.borderRadius.md)};
  cursor: pointer;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', fallbacks.typography.fontSize.sm)};
  transition: background-color ${({ theme }) => getThemeValue(theme, 'transitions.medium', fallbacks.transitions.medium)};

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
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