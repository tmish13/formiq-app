import React from 'react';
import styled from 'styled-components';
import { LoadingSpinner } from './LoadingSpinner';
import { getThemeValue } from '../../utils/themeUtils';

interface LoadingStateProps {
  isLoading: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

const LoadingContainer = styled.div`
  position: relative;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const ContentContainer = styled.div<{ isLoading: boolean }>`
  opacity: ${({ isLoading }) => (isLoading ? 0.5 : 1)};
  pointer-events: ${({ isLoading }) => (isLoading ? 'none' : 'auto')};
  transition: opacity ${({ theme }) => getThemeValue(theme, 'transitions.medium', '0.3s')} ease;
`;

export const LoadingState: React.FC<LoadingStateProps> = ({
  isLoading,
  children,
  fallback,
}) => {
  if (isLoading && fallback) {
    return <>{fallback}</>;
  }

  return (
    <LoadingContainer>
      <ContentContainer isLoading={isLoading}>{children}</ContentContainer>
      {isLoading && <LoadingSpinner />}
    </LoadingContainer>
  );
}; 