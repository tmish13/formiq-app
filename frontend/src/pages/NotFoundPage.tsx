import React from 'react';
import { useNavigate } from 'react-router-dom';
import styled from 'styled-components';
import { Button } from '../components/common/Button';

const NotFoundContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: ${({ theme }) => theme.spacing.xl};
  text-align: center;
`;

const Title = styled.h1`
  font-size: ${({ theme }) => theme.typography.fontSize.xxl};
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const Message = styled.p`
  font-size: ${({ theme }) => theme.typography.fontSize.lg};
  color: ${({ theme }) => theme.colors.textSecondary};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <NotFoundContainer>
      <Title>404 - Page Not Found</Title>
      <Message>
        The page you're looking for doesn't exist or has been moved.
      </Message>
      <Button variant="primary" onClick={() => navigate('/')}>
        Go to Homepage
      </Button>
    </NotFoundContainer>
  );
}; 