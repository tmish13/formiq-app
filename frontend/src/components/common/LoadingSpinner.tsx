import React from 'react';
import styled, { keyframes, DefaultTheme } from 'styled-components';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  isFullPage?: boolean;
  text?: string;
  ariaLabel?: string;
}

const pulse = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
`;

const LoadingText = styled.div<{ theme: DefaultTheme }>`
  margin-top: 1rem;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.lg', fallbacks.typography.fontSize.lg)};
  text-align: center;
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', String(fallbacks.typography.fontWeight.medium))};
  letter-spacing: 0.5px;
`;

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
`;

const FullPageLoader = styled.div<{ theme: DefaultTheme }>`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
  z-index: 9999;
`;

const SpinnerWrapper = styled.div<{ size: LoadingSpinnerProps['size'] }>`
  width: ${({ size }) => {
    switch (size) {
      case 'small': return '32px';
      case 'large': return '64px';
      default: return '48px';
    }
  }};
  height: ${({ size }) => {
    switch (size) {
      case 'small': return '32px';
      case 'large': return '64px';
      default: return '48px';
    }
  }};
  position: relative;
`;

const DumbbellIcon = styled.svg<{ $color?: string; theme: DefaultTheme }>`
  width: 100%;
  height: 100%;
  animation: ${pulse} 1.5s ease-in-out infinite;
  color: ${({ $color, theme }) => $color || getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
`;

const LoadingSpinner: React.FC<LoadingSpinnerProps> = React.memo(({
  size = 'medium',
  color,
  isFullPage = false,
  text = 'Loading your fitness journey...',
  ariaLabel = 'Loading content, please wait'
}) => {
  const spinner = (
    <Container>
      <SpinnerWrapper size={size} role="progressbar" aria-label={ariaLabel}>
        <DumbbellIcon 
          $color={color}
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2" 
          strokeLinecap="round" 
          strokeLinejoin="round"
        >
          <path d="M6 4v16M18 4v16M4 8h4M16 8h4M4 16h4M16 16h4" />
        </DumbbellIcon>
      </SpinnerWrapper>
      {text && <LoadingText>{text}</LoadingText>}
    </Container>
  );

  if (isFullPage) {
    return <FullPageLoader>{spinner}</FullPageLoader>;
  }

  return spinner;
});

LoadingSpinner.displayName = 'LoadingSpinner';

export { LoadingSpinner }; 