import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { DefaultTheme } from 'styled-components';

interface OnboardingTooltipProps {
  id: string;
  content: React.ReactNode;
  position?: 'top' | 'right' | 'bottom' | 'left';
  children: React.ReactNode;
  showOnlyOnce?: boolean;
}

const TooltipContainer = styled.div`
  position: relative;
  display: inline-flex;
`;

const TooltipContent = styled.div<{ position: string; isVisible: boolean }>`
  position: absolute;
  background-color: ${({ theme }) => theme.colors.primary.main};
  color: white;
  padding: ${({ theme }) => theme.spacing.sm}px ${({ theme }) => theme.spacing.md}px;
  border-radius: 4px;
  max-width: 250px;
  z-index: 1000;
  opacity: ${({ isVisible }) => (isVisible ? 1 : 0)};
  visibility: ${({ isVisible }) => (isVisible ? 'visible' : 'hidden')};
  transition: opacity 0.3s, visibility 0.3s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  
  ${({ position, theme }: { position: string; theme: DefaultTheme }) => {
    switch (position) {
      case 'top':
        return `
          bottom: 100%;
          left: 50%;
          transform: translateX(-50%) translateY(-10px);
          margin-bottom: 10px;
          
          &::after {
            content: '';
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -8px;
            border-width: 8px;
            border-style: solid;
            border-color: ${theme.colors.primary.main} transparent transparent transparent;
          }
        `;
      case 'right':
        return `
          left: 100%;
          top: 50%;
          transform: translateY(-50%) translateX(10px);
          margin-left: 10px;
          
          &::after {
            content: '';
            position: absolute;
            top: 50%;
            right: 100%;
            margin-top: -8px;
            border-width: 8px;
            border-style: solid;
            border-color: transparent ${theme.colors.primary.main} transparent transparent;
          }
        `;
      case 'bottom':
        return `
          top: 100%;
          left: 50%;
          transform: translateX(-50%) translateY(10px);
          margin-top: 10px;
          
          &::after {
            content: '';
            position: absolute;
            bottom: 100%;
            left: 50%;
            margin-left: -8px;
            border-width: 8px;
            border-style: solid;
            border-color: transparent transparent ${theme.colors.primary.main} transparent;
          }
        `;
      case 'left':
        return `
          right: 100%;
          top: 50%;
          transform: translateY(-50%) translateX(-10px);
          margin-right: 10px;
          
          &::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 100%;
            margin-top: -8px;
            border-width: 8px;
            border-style: solid;
            border-color: transparent transparent transparent ${theme.colors.primary.main};
          }
        `;
      default:
        return '';
    }
  }}
`;

const CloseButton = styled.button`
  position: absolute;
  top: 5px;
  right: 5px;
  background: transparent;
  border: none;
  color: white;
  font-size: 14px;
  cursor: pointer;
  padding: 2px 5px;
  line-height: 1;
  
  &:hover {
    opacity: 0.8;
  }
`;

export const OnboardingTooltip: React.FC<OnboardingTooltipProps> = ({
  id,
  content,
  position = 'top',
  children,
  showOnlyOnce = true,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  
  useEffect(() => {
    // Check if this tooltip has been shown before
    const hasBeenShown = localStorage.getItem(`onboarding-tooltip-${id}`);
    
    if (!hasBeenShown) {
      setIsVisible(true);
      if (showOnlyOnce) {
        localStorage.setItem(`onboarding-tooltip-${id}`, 'true');
      }
    }
  }, [id, showOnlyOnce]);
  
  const handleClose = () => {
    setIsVisible(false);
  };
  
  const resetTooltip = () => {
    localStorage.removeItem(`onboarding-tooltip-${id}`);
  };
  
  return (
    <TooltipContainer>
      {children}
      <TooltipContent position={position} isVisible={isVisible}>
        {content}
        <CloseButton onClick={handleClose}>✕</CloseButton>
      </TooltipContent>
    </TooltipContainer>
  );
};

export default OnboardingTooltip; 