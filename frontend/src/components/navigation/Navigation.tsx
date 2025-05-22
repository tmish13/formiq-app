import React from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';
import { ROUTES } from '../../routes/constants';
import { UserButton } from './UserButton';

const Nav = styled.nav`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background-color: ${({ theme }) => theme.colors.background.main};
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const NavLinks = styled.div`
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
          Dashboard
        </NavLink>
        <NavLink to={ROUTES.WORKOUT} $isActive={location.pathname.startsWith(ROUTES.WORKOUT)}>
          Workout
        </NavLink>
        <NavLink to={ROUTES.FORM_ANALYSIS} $isActive={location.pathname.startsWith(ROUTES.FORM_ANALYSIS)}>
          Form Analysis
        </NavLink>
        <NavLink to={ROUTES.VIDEOS} $isActive={location.pathname.startsWith(ROUTES.VIDEOS)}>
          Videos
        </NavLink>
        <NavLink to={ROUTES.PROGRESS} $isActive={location.pathname.startsWith(ROUTES.PROGRESS)}>
          Progress
        </NavLink>
      </NavLinks>
      <UserButton />
    </Nav>
  );
}; 