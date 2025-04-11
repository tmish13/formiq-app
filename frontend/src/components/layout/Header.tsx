import React from 'react';
import styled from 'styled-components';
import { getThemeValue } from '../../utils/themeUtils';

const HeaderContainer = styled.header`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', '#FFFFFF')};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.sm', '0 2px 4px rgba(0, 0, 0, 0.1)')};
  display: flex;
  align-items: center;
  padding: 0 ${({ theme }) => getThemeValue(theme, 'spacing.md', '16px')};
  z-index: 1000;

  @media (max-width: 768px) {
    height: 56px;
  }
`;

export const HeaderContent = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
`;

const Title = styled.h1`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.large', '20px')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', 700)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', '#000000')};
  margin: 0;
`;

export interface HeaderProps {
  children?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({ children }) => {
  return (
    <HeaderContainer>
      {children}
    </HeaderContainer>
  );
}; 