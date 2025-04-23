import React from 'react';
import styled, { keyframes } from 'styled-components';
import { useNetworkStatus } from '../../services/networkService';
import { getThemeValue } from '../../utils/themeUtils';

const slideDown = keyframes`
  from {
    transform: translateY(-100%);
  }
  to {
    transform: translateY(0);
  }
`;

const StatusBarContainer = styled.div<{ isVisible: boolean }>`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background-color: ${({ theme }) => theme.colors.error};
  color: ${({ theme }) => theme.colors.white};
  padding: 8px 16px;
  text-align: center;
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  z-index: 1100;
  display: ${({ isVisible }) => (isVisible ? 'block' : 'none')};
  animation: ${slideDown} 0.3s ease-in-out;
  
  /* Handle iOS safe area */
  padding-top: max(8px, env(safe-area-inset-top));
`;

const StatusText = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
`;

const Dot = styled.span`
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: ${({ theme }) => theme.colors.white};
`;

const QueueInfo = styled.div`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', '0.875rem')};
  margin-top: 4px;
`;

interface OfflineStatusBarProps {
  queueCount?: number;
}

export const OfflineStatusBar: React.FC<OfflineStatusBarProps> = ({ queueCount = 0 }) => {
  const { status } = useNetworkStatus();

  return (
    <StatusBarContainer isVisible={!status.connected}>
      <StatusText>
        <Dot /> You are offline
      </StatusText>
      {queueCount > 0 && (
        <QueueInfo>
          {queueCount} {queueCount === 1 ? 'request' : 'requests'} queued for when you're back online
        </QueueInfo>
      )}
    </StatusBarContainer>
  );
}; 