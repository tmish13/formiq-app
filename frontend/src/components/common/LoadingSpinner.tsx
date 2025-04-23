import React from 'react';
import styled, { keyframes } from 'styled-components';
import { getThemeValue } from '../../utils/themeUtils';

const spin = keyframes`
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
`;

const SpinnerWrapper = styled.div<{ size?: 'small' | 'medium' | 'large' }>`
  display: inline-block;
  position: relative;
  width: ${({ size, theme }) => {
    switch (size) {
      case 'small':
        return getThemeValue(theme, 'spacing.xs', '16px');
      case 'large':
        return getThemeValue(theme, 'spacing.xl', '48px');
      default:
        return getThemeValue(theme, 'spacing.md', '24px');
    }
  }};
  height: ${({ size, theme }) => {
    switch (size) {
      case 'small':
        return getThemeValue(theme, 'spacing.xs', '16px');
      case 'large':
        return getThemeValue(theme, 'spacing.xl', '48px');
      default:
        return getThemeValue(theme, 'spacing.md', '24px');
    }
  }};
`;

const SpinnerCircle = styled.div<{ size?: 'small' | 'medium' | 'large' }>`
  box-sizing: border-box;
  display: block;
  position: absolute;
  width: 100%;
  height: 100%;
  border: ${({ size, theme }) => {
    const borderWidth = size === 'small' ? '2px' : '3px';
    return `${borderWidth} solid`;
  }};
  border-radius: 50%;
  animation: ${spin} ${({ theme }) => getThemeValue(theme, 'transitions.duration.long', '1.2s')} ${({ theme }) => getThemeValue(theme, 'transitions.easing.easeInOut', 'cubic-bezier(0.5, 0, 0.5, 1)')} infinite;
  border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', '#3f51b5')} transparent transparent transparent;
`;

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  ariaLabel?: string;
  testId?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'medium',
  color,
  ariaLabel = 'Loading',
  testId = 'loading-spinner'
}) => {
  return (
    <SpinnerWrapper 
      size={size}
      role="status"
      aria-label={ariaLabel}
      data-testid={testId}
    >
      <SpinnerCircle 
        size={size} 
        style={color ? { borderColor: `${color} transparent transparent transparent` } : undefined}
      />
    </SpinnerWrapper>
  );
}; 