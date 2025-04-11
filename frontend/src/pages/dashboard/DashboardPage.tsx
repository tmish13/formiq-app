import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Grid as MuiGrid, Paper, Button, Card, CardContent, CardHeader, Divider } from '@mui/material';
import { Skeleton } from '../../components/common/SkeletonLoader';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';

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

const DashboardGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: ${({ theme }) => theme.spacing.xl};
`;

const DashboardCard = styled(Paper)`
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
`;

const CardTitle = styled(Typography)`
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  margin-bottom: ${({ theme }) => theme.spacing.sm};
`;

const StatsValue = styled(Typography)`
  font-size: 28px;
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
  color: ${({ theme }) => theme.colors.primary};
  margin-bottom: ${({ theme }) => theme.spacing.sm};
`;

const SectionHeader = styled(Box)`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

// Mock data interfaces
interface WorkoutSummary {
  totalWorkouts: number;
  completedThisWeek: number;
  averageDuration: string;
  upcomingWorkout: {
    name: string;
    date: string;
    type: string;
  } | null;
}

interface FormCheckSummary {
  total: number;
  pending: number;
  lastAnalyzed: string;
  improvement: string;
}

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(true);
  const [workoutSummary, setWorkoutSummary] = useState<WorkoutSummary | null>(null);
  const [formCheckSummary, setFormCheckSummary] = useState<FormCheckSummary | null>(null);
  
  // Recent activity loading state
  const [activitiesLoading, setActivitiesLoading] = useState(true);
  
  useEffect(() => {
    // Simulate API call to get dashboard data
    const fetchDashboardData = async () => {
      try {
        // In a real app, we'd make API calls here
        // const workoutResponse = await api.get('/workouts/summary');
        // const formCheckResponse = await api.get('/form-checks/summary');
        
        // Simulate network delay for main content
        setTimeout(() => {
          setWorkoutSummary({
            totalWorkouts: 24,
            completedThisWeek: 3,
            averageDuration: '45 mins',
            upcomingWorkout: {
              name: 'Upper Body Strength',
              date: 'Tomorrow, 6:00 PM',
              type: 'Strength'
            }
          });
          
          setFormCheckSummary({
            total: 12,
            pending: 2,
            lastAnalyzed: '2 days ago',
            improvement: '15% on Squat Form'
          });
          
          setLoading(false);
        }, 1500);
        
        // Simulate delayed loading for recent activity
        setTimeout(() => {
          setActivitiesLoading(false);
        }, 2500);
        
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        setLoading(false);
        setActivitiesLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);
  
  return (
    <DashboardContainer>
      <Header>
        <Title>Dashboard</Title>
        <Button variant="outlined" color="primary" onClick={logout}>
          Logout
        </Button>
      </Header>

      <WelcomeSection>
        <Title>Welcome back, {user?.name}!</Title>
        <Subtitle>Here's what's happening with your workouts today.</Subtitle>
      </WelcomeSection>

      <Container maxWidth="lg">
        <Box my={4}>
          <Typography variant="h4" component="h1" gutterBottom>
            Dashboard
          </Typography>
          
          <Typography variant="body1" color="textSecondary" paragraph>
            Welcome back! Here's an overview of your fitness progress and recent activities.
          </Typography>
          
          {/* Quick stats */}
          <MuiGrid container spacing={3} mb={4}>
            {/* Workout stats */}
            <MuiGrid item xs={12} md={6}>
              <DashboardCard elevation={2}>
                <Box p={3}>
                  <CardTitle variant="h6">
                    Workout Summary
                  </CardTitle>
                  <Divider sx={{ mb: 2 }} />
                  {loading ? (
                    <MuiGrid container spacing={2}>
                      <MuiGrid item xs={6}>
                        <Skeleton variant="text" width="50%" />
                        <Skeleton variant="text" width="70%" height="40px" />
                        <Skeleton variant="text" width="60%" />
                      </MuiGrid>
                      <MuiGrid item xs={6}>
                        <Skeleton variant="text" width="50%" />
                        <Skeleton variant="text" width="70%" height="40px" />
                        <Skeleton variant="text" width="60%" />
                      </MuiGrid>
                    </MuiGrid>
                  ) : (
                    <MuiGrid container spacing={2}>
                      <MuiGrid item xs={6}>
                        <Typography variant="body2" color="textSecondary">
                          Total Workouts
                        </Typography>
                        <StatsValue>
                          {workoutSummary?.totalWorkouts}
                        </StatsValue>
                        <Typography variant="body2">
                          {workoutSummary?.completedThisWeek} this week
                        </Typography>
                      </MuiGrid>
                      <MuiGrid item xs={6}>
                        <Typography variant="body2" color="textSecondary">
                          Average Duration
                        </Typography>
                        <StatsValue>
                          {workoutSummary?.averageDuration}
                        </StatsValue>
                        <Button size="small" color="primary">
                          View Details
                        </Button>
                      </MuiGrid>
                    </MuiGrid>
                  )}
                </Box>
              </DashboardCard>
            </MuiGrid>
            
            {/* Form check stats */}
            <MuiGrid item xs={12} md={6}>
              <DashboardCard elevation={2}>
                <Box p={3}>
                  <CardTitle variant="h6">
                    Form Check Analysis
                  </CardTitle>
                  <Divider sx={{ mb: 2 }} />
                  {loading ? (
                    <MuiGrid container spacing={2}>
                      <MuiGrid item xs={6}>
                        <Skeleton variant="text" width="50%" />
                        <Skeleton variant="text" width="70%" height="40px" />
                        <Skeleton variant="text" width="60%" />
                      </MuiGrid>
                      <MuiGrid item xs={6}>
                        <Skeleton variant="text" width="50%" />
                        <Skeleton variant="text" width="70%" height="40px" />
                        <Skeleton variant="text" width="60%" />
                      </MuiGrid>
                    </MuiGrid>
                  ) : (
                    <MuiGrid container spacing={2}>
                      <MuiGrid item xs={6}>
                        <Typography variant="body2" color="textSecondary">
                          Total Form Checks
                        </Typography>
                        <StatsValue>
                          {formCheckSummary?.total}
                        </StatsValue>
                        <Typography variant="body2">
                          {formCheckSummary?.pending} pending analysis
                        </Typography>
                      </MuiGrid>
                      <MuiGrid item xs={6}>
                        <Typography variant="body2" color="textSecondary">
                          Latest Improvement
                        </Typography>
                        <StatsValue style={{ fontSize: '22px' }}>
                          {formCheckSummary?.improvement}
                        </StatsValue>
                        <Button size="small" color="primary">
                          Upload New Video
                        </Button>
                      </MuiGrid>
                    </MuiGrid>
                  )}
                </Box>
              </DashboardCard>
            </MuiGrid>
          </MuiGrid>
          
          {/* Upcoming workout */}
          <DashboardGrid>
            <DashboardCard elevation={2}>
              <Box p={3}>
                <Typography variant="h6" gutterBottom>
                  Upcoming Workout
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {loading ? (
                  <MuiGrid container spacing={2}>
                    <MuiGrid item xs={12}>
                      <Skeleton variant="text" width="60%" />
                      <Skeleton variant="text" width="40%" />
                      <Skeleton variant="text" width="30%" />
                    </MuiGrid>
                  </MuiGrid>
                ) : workoutSummary?.upcomingWorkout ? (
                  <>
                    <Typography variant="h6" gutterBottom>
                      {workoutSummary.upcomingWorkout.name}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {workoutSummary.upcomingWorkout.date}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Type: {workoutSummary.upcomingWorkout.type}
                    </Typography>
                  </>
                ) : (
                  <Typography variant="body2" color="textSecondary">
                    No upcoming workouts scheduled
                  </Typography>
                )}
              </Box>
            </DashboardCard>
          </DashboardGrid>
          
          {/* Recent activity */}
          <SectionHeader>
            <Typography variant="h5">
              Recent Activity
            </Typography>
            <Button color="primary">View All</Button>
          </SectionHeader>
          
          {activitiesLoading ? (
            // Skeleton for activity list
            <Box mb={4}>
              <Skeleton variant="list" count={4} />
            </Box>
          ) : (
            <Box mb={4}>
              <Typography variant="body1">
                Activity items will be displayed here...
              </Typography>
            </Box>
          )}
        </Box>
      </Container>
    </DashboardContainer>
  );
}; 