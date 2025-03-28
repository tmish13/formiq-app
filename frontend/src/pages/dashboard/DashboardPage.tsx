import React from 'react';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../../components/common/Button';

const DashboardContainer = styled.div`
  min-height: 100vh;
  padding: ${({ theme }) => theme.spacing.xl};
  background-color: ${({ theme }) => theme.colors.background};
`;

const Header = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const WelcomeSection = styled.div`
  background-color: ${({ theme }) => theme.colors.white};
  padding: ${({ theme }) => theme.spacing.xl};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  box-shadow: ${({ theme }) => theme.shadows.md};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const Title = styled.h1`
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const Subtitle = styled.p`
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => theme.typography.fontSize.lg};
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: ${({ theme }) => theme.spacing.xl};
`;

const Card = styled.div`
  background-color: ${({ theme }) => theme.colors.white};
  padding: ${({ theme }) => theme.spacing.xl};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  box-shadow: ${({ theme }) => theme.shadows.md};
`;

const CardTitle = styled.h2`
  color: ${({ theme }) => theme.colors.text};
  margin-bottom: ${({ theme }) => theme.spacing.md};
  font-size: ${({ theme }) => theme.typography.fontSize.xl};
`;

const CardContent = styled.p`
  color: ${({ theme }) => theme.colors.textSecondary};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <DashboardContainer>
      <Header>
        <Title>Dashboard</Title>
        <Button variant="outline" onClick={logout}>
          Logout
        </Button>
      </Header>

      <WelcomeSection>
        <Title>Welcome back, {user?.name}!</Title>
        <Subtitle>Here's what's happening with your workouts today.</Subtitle>
      </WelcomeSection>

      <Grid>
        <Card>
          <CardTitle>Recent Workouts</CardTitle>
          <CardContent>
            You haven't completed any workouts today. Start a new workout to track your progress!
          </CardContent>
          <Button variant="primary">Start Workout</Button>
        </Card>

        <Card>
          <CardTitle>Form Analysis</CardTitle>
          <CardContent>
            Your last form analysis was 2 days ago. Keep practicing to improve your technique!
          </CardContent>
          <Button variant="primary">Analyze Form</Button>
        </Card>

        <Card>
          <CardTitle>Progress Overview</CardTitle>
          <CardContent>
            Track your progress over time and see how your form has improved.
          </CardContent>
          <Button variant="primary">View Progress</Button>
        </Card>
      </Grid>
    </DashboardContainer>
  );
}; 