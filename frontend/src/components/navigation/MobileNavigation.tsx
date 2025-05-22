import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';
import { ROUTES } from '../../routes/constants';

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
  font-size: 0.65rem;
  font-weight: 500;
  padding: 8px 0;
  width: 16.66%; /* Adjusted for 6 items */
  
  &.active {
    color: ${({ theme }) => theme.colors.primary.main};
  }
`;

interface MobileNavigationProps {
  className?: string;
}

export const MobileNavigation: React.FC<MobileNavigationProps> = ({ className }) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  
  // Don't show bottom navigation on login/register pages
  if (!isAuthenticated || location.pathname.includes('/login') || location.pathname.includes('/register')) {
    return null;
  }
  
  return (
    <BottomNavContainer className={className}>
      <NavItem to={ROUTES.DASHBOARD} end>
        <span>Home</span>
      </NavItem>
      
      <NavItem to={ROUTES.WORKOUT}>
        <span>Workout</span>
      </NavItem>
      
      <NavItem to={ROUTES.FORM_ANALYSIS}>
        <span>Form</span>
      </NavItem>
      
      <NavItem to={ROUTES.VIDEOS}>
        <span>Videos</span>
      </NavItem>
      
      <NavItem to={ROUTES.PROGRESS}>
        <span>Progress</span>
      </NavItem>
      
      <NavItem to={ROUTES.PROFILE}>
        <span>Profile</span>
      </NavItem>
    </BottomNavContainer>
  );
}; 