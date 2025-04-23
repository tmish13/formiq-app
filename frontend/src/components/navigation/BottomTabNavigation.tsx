import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { Home, User, FileText, BarChart2, Activity } from 'react-feather';
import { useAuth } from '../../hooks/useAuth';

const BottomNavContainer = styled.nav`
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background-color: ${({ theme }) => theme.colors.background.main};
  display: flex;
  justify-content: space-around;
  align-items: center;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
  
  /* Hide on larger screens */
  @media (min-width: 768px) {
    display: none;
  }
`;

const NavItem = styled(NavLink)`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  color: ${({ theme }) => theme.colors.secondary.main};
  font-size: 0.7rem;
  padding: 8px 0;
  width: 20%;
  
  &.active {
    color: ${({ theme }) => theme.colors.primary.main};
  }
  
  svg {
    margin-bottom: 4px;
  }
`;

interface BottomTabNavigationProps {
  className?: string;
}

export const BottomTabNavigation: React.FC<BottomTabNavigationProps> = ({ className }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  
  // Don't show bottom navigation on login/register pages
  if (!isAuthenticated || location.pathname.includes('/login') || location.pathname.includes('/register')) {
    return null;
  }
  
  return (
    <BottomNavContainer className={className}>
      <NavItem to="/dashboard" end>
        <Home size={20} strokeWidth={2} />
        <span>Home</span>
      </NavItem>
      
      <NavItem to="/workout">
        <Activity size={20} strokeWidth={2} />
        <span>Workout</span>
      </NavItem>
      
      <NavItem to="/form-analysis">
        <FileText size={20} strokeWidth={2} />
        <span>Form</span>
      </NavItem>
      
      <NavItem to="/progress">
        <BarChart2 size={20} strokeWidth={2} />
        <span>Progress</span>
      </NavItem>
      
      <NavItem to="/profile">
        <User size={20} strokeWidth={2} />
        <span>Profile</span>
      </NavItem>
    </BottomNavContainer>
  );
}; 