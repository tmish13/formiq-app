import React from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import styled from 'styled-components';
import { Home, Activity, FileText, BarChart2, User } from 'react-feather';
import { useAuth } from '../../hooks/useAuth';
import { ROUTES } from '../../routes/constants';
import { Typography } from '../atoms/Typography';

const BottomNav = styled(Box)`
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
  z-index: 1000;
  
  @media (min-width: 768px) {
    display: none;
  }
`;

const NavItem = styled(RouterLink)<{ $isActive: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  color: ${({ theme, $isActive }) => 
    $isActive ? theme.colors.primary.main : theme.colors.text.secondary};
  padding: 8px 0;
  width: 20%;
  
  svg {
    margin-bottom: 4px;
  }
`;

export const MobileNavigation: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  
  if (!isAuthenticated || 
      location.pathname === ROUTES.LOGIN || 
      location.pathname === ROUTES.REGISTER) {
    return null;
  }
  
  return (
    <BottomNav>
      <NavItem to={ROUTES.DASHBOARD} $isActive={location.pathname === ROUTES.DASHBOARD}>
        <Home size={20} strokeWidth={2} />
        <Typography variant="caption">Home</Typography>
      </NavItem>
      
      <NavItem to={ROUTES.WORKOUT} $isActive={location.pathname.startsWith(ROUTES.WORKOUT)}>
        <Activity size={20} strokeWidth={2} />
        <Typography variant="caption">Workout</Typography>
      </NavItem>
      
      <NavItem to={ROUTES.FORM_ANALYSIS} $isActive={location.pathname.startsWith(ROUTES.FORM_ANALYSIS)}>
        <FileText size={20} strokeWidth={2} />
        <Typography variant="caption">Form</Typography>
      </NavItem>
      
      <NavItem to={ROUTES.PROGRESS} $isActive={location.pathname.startsWith(ROUTES.PROGRESS)}>
        <BarChart2 size={20} strokeWidth={2} />
        <Typography variant="caption">Progress</Typography>
      </NavItem>
      
      <NavItem to={ROUTES.PROFILE} $isActive={location.pathname === ROUTES.PROFILE}>
        <User size={20} strokeWidth={2} />
        <Typography variant="caption">Profile</Typography>
      </NavItem>
    </BottomNav>
  );
}; 