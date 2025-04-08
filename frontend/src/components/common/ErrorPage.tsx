import React from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { Button } from './Button';

interface ErrorPageProps {
  title?: string;
  message?: string;
  code?: number | string;
  showHomeButton?: boolean;
  showRetryButton?: boolean;
  onRetry?: () => void;
}

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  text-align: center;
  background-color: ${({ theme }) => theme.colors.background};
`;

const ErrorCode = styled.h1`
  font-size: 6rem;
  font-weight: bold;
  color: ${({ theme }) => theme.colors.primary};
  margin: 0;
  line-height: 1;
  
  @media (max-width: 768px) {
    font-size: 4rem;
  }
`;

const Title = styled.h2`
  font-size: 2rem;
  font-weight: 500;
  color: ${({ theme }) => theme.colors.text};
  margin: 1rem 0;
  
  @media (max-width: 768px) {
    font-size: 1.5rem;
  }
`;

const Message = styled.p`
  font-size: 1.125rem;
  color: ${({ theme }) => theme.colors.textSecondary};
  margin-bottom: 2rem;
  max-width: 600px;
  
  @media (max-width: 768px) {
    font-size: 1rem;
  }
`;

const ButtonContainer = styled.div`
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  
  @media (max-width: 768px) {
    flex-direction: column;
  }
`;

const ErrorPage: React.FC<ErrorPageProps> = ({
  title = 'Oops! Something went wrong',
  message = 'We encountered an error while processing your request. Please try again later.',
  code = 500,
  showHomeButton = true,
  showRetryButton = true,
  onRetry
}) => {
  const navigate = useNavigate();

  const handleHomeClick = () => {
    navigate('/');
  };

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else {
      window.location.reload();
    }
  };

  return (
    <Container>
      <ErrorCode>{code}</ErrorCode>
      <Title>{title}</Title>
      <Message>{message}</Message>
      <ButtonContainer>
        {showRetryButton && (
          <Button
            variant="primary"
            onClick={handleRetry}
            icon="refresh"
          >
            Try Again
          </Button>
        )}
        {showHomeButton && (
          <Button
            variant="secondary"
            onClick={handleHomeClick}
            icon="home"
          >
            Go Home
          </Button>
        )}
      </ButtonContainer>
    </Container>
  );
};

export default ErrorPage; 