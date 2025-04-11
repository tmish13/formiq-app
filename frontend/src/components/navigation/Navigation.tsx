import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { Theme } from '../../theme';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { useAuth } from '../../contexts/AuthContext';

const NavContainer = styled.nav<{ theme?: Partial<Theme> }>`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
`;

const Logo = styled(Link)<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.large', fallbacks.typography.fontSize.large)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', fallbacks.typography.fontWeight.bold)};
  text-decoration: none;
`;

const NavLinks = styled.div`
  display: flex;
  gap: 24px;
  align-items: center;
`;

const NavLink = styled(Link)<{ theme?: Partial<Theme>; active: boolean }>`
  color: ${({ theme, active }) => 
    active 
      ? getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)
      : getThemeValue(theme, 'colors.text', fallbacks.colors.text)
  };
  text-decoration: none;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.medium', fallbacks.typography.fontSize.medium)};
  font-weight: ${({ theme, active }) => 
    active 
      ? getThemeValue(theme, 'typography.fontWeight.bold', fallbacks.typography.fontWeight.bold)
      : getThemeValue(theme, 'typography.fontWeight.normal', fallbacks.typography.fontWeight.normal)
  };
  padding: 8px 12px;
  border-radius: 6px;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
  }
`;

const LogoutButton = styled.button<{ theme?: Partial<Theme> }>`
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.errorLight', fallbacks.colors.errorLight)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.medium', fallbacks.typography.fontSize.medium)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', fallbacks.typography.fontWeight.medium)};
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
    color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  }
`;

export const Navigation: React.FC = () => {
  const location = useLocation();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <NavContainer>
      <Logo to="/">FormIQ</Logo>
      
      <NavLinks>
        <NavLink 
          to="/dashboard" 
          active={location.pathname === '/dashboard' || location.pathname === '/'}
        >
          Dashboard
        </NavLink>
        
        <NavLink 
          to="/form-analysis" 
          active={location.pathname === '/form-analysis'}
        >
          Form Analysis
        </NavLink>
        
        <NavLink 
          to="/progress" 
          active={location.pathname === '/progress'}
        >
          Progress
        </NavLink>
        
        <NavLink 
          to="/profile" 
          active={location.pathname === '/profile'}
        >
          Profile
        </NavLink>
        
        <LogoutButton onClick={handleLogout}>
          Logout
        </LogoutButton>
      </NavLinks>
    </NavContainer>
  );
}; 