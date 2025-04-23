import React from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { Box } from '@mui/material';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';
import { ROUTES } from '../../routes/constants';
import { UserButton } from '../molecules/UserButton';
import { Typography } from '../atoms/Typography';

const Nav = styled(Box)`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background-color: ${({ theme }) => theme.colors.background.main};
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
`;

const NavLinks = styled(Box)`
  display: flex;
  gap: 2rem;
  align-items: center;
`;

const NavLink = styled(RouterLink)<{ $isActive: boolean }>`
  text-decoration: none;
  color: ${({ theme, $isActive }) => 
    $isActive ? theme.colors.primary.main : theme.colors.text.primary};
  font-weight: ${({ $isActive }) => $isActive ? '600' : '400'};
  
  &:hover {
    color: ${({ theme }) => theme.colors.primary.main};
  }
`;

export const Navigation: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return null;
  }

  return (
    <Nav>
      <NavLinks>
        <NavLink to={ROUTES.DASHBOARD} $isActive={location.pathname === ROUTES.DASHBOARD}>
          <Typography variant="body1">Dashboard</Typography>
        </NavLink>
        <NavLink to={ROUTES.WORKOUT} $isActive={location.pathname.startsWith(ROUTES.WORKOUT)}>
          <Typography variant="body1">Workout</Typography>
        </NavLink>
        <NavLink to={ROUTES.FORM_ANALYSIS} $isActive={location.pathname.startsWith(ROUTES.FORM_ANALYSIS)}>
          <Typography variant="body1">Form Analysis</Typography>
        </NavLink>
        <NavLink to={ROUTES.PROGRESS} $isActive={location.pathname.startsWith(ROUTES.PROGRESS)}>
          <Typography variant="body1">Progress</Typography>
        </NavLink>
      </NavLinks>
      <UserButton />
    </Nav>
  );
}; 