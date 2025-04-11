import React from 'react';
import styled from 'styled-components';
import { Theme } from '../../theme';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
}

const SpinnerContainer = styled.div<LoadingSpinnerProps & { theme?: Partial<Theme> }>`
  width: ${({ size }) => {
    switch (size) {
      case 'small': return '24px';
      case 'large': return '48px';
      default: return '32px';
    }
  }};
  height: ${({ size }) => {
    switch (size) {
      case 'small': return '24px';
      case 'large': return '48px';
      default: return '32px';
    }
  }};
  border: 3px solid ${({ theme }) => getThemeValue(theme, 'colors.primaryLight', fallbacks.colors.primaryLight)};
  border-top: 3px solid ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
  border-radius: 50%;
  animation: spin 1s linear infinite;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ size = 'medium' }) => {
  return <SpinnerContainer size={size} role="status" aria-label="Loading" />;
};

export default LoadingSpinner; 