import React from 'react';
import styled, { keyframes } from 'styled-components';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
}

const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

const SpinnerContainer = styled.div<{ size: LoadingSpinnerProps['size'] }>`
  display: inline-block;
  width: ${({ size, theme }) => {
    switch (size) {
      case 'small':
        return '20px';
      case 'large':
        return '40px';
      default:
        return '30px';
    }
  }};
  height: ${({ size, theme }) => {
    switch (size) {
      case 'small':
        return '20px';
      case 'large':
        return '40px';
      default:
        return '30px';
    }
  }};
  border: 3px solid ${({ theme }) => theme.colors.primaryLight};
  border-radius: 50%;
  border-top-color: ${({ theme, color }) => color || theme.colors.primary};
  animation: ${spin} 1s linear infinite;
`;

const LoadingText = styled.p`
  color: ${({ theme }) => theme.colors.textSecondary};
  margin-top: ${({ theme }) => theme.spacing.sm};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: ${({ theme }) => theme.spacing.xl};
`;

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  color,
  children,
}) => {
  return (
    <LoadingContainer>
      <SpinnerContainer size={size} color={color} />
      {children && <LoadingText>{children}</LoadingText>}
    </LoadingContainer>
  );
}; 