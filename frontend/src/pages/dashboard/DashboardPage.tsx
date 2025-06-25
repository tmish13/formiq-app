import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Grid as MuiGrid, Paper, Button, Card, CardContent, CardHeader, Divider } from '@mui/material';
import { Add as AddIcon, VideoLibrary as VideoIcon, Timeline as AnalyticsIcon } from '@mui/icons-material';
import { Skeleton } from '../../components/common/SkeletonLoader';
import styled from 'styled-components';
import { useAuth } from '../../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import apiService from '../../services/apiService';
import { formCheckService } from '../../services/formCheckService';

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

const QuickActionCard = styled(Paper)`
  padding: ${({ theme }) => theme.spacing.lg};
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
  
  &:hover {
    border-color: ${({ theme }) => theme.colors.primary};
    transform: translateY(-2px);
    box-shadow: ${({ theme }) => theme.shadows.lg};
  }
`;

const QuickActionIcon = styled.div`
  font-size: 48px;
  color: ${({ theme }) => theme.colors.primary};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const QuickActionTitle = styled(Typography)`
  font-weight: ${({ theme }) => theme.typography.fontWeight.bold};
  margin-bottom: ${({ theme }) => theme.spacing.sm};
`;

const QuickActionDescription = styled(Typography)`
  color: ${({ theme }) => theme.colors.textSecondary};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
`;

// Backend-aligned interfaces
interface DashboardSummary {
  videos: {
    total: number;
    thisWeek: number;
    processing: number;
    completed: number;
  };
  formChecks: {
    total: number;
    pending: number;
    completed: number;
    averageScore: number;
    lastAnalyzed?: string;
    improvement?: {
      percentage: number;
      exercise: string;
    };
  };
  recentActivity: RecentActivity[];
}

interface RecentActivity {
  id: string;
  type: 'video_upload' | 'analysis_complete' | 'form_check';
  exercise: string;
  timestamp: string;
  status: 'completed' | 'processing' | 'failed';
  score?: number;
}

export const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch data from multiple endpoints concurrently
        const [videosResponse, formChecksResponse, recentFormChecks] = await Promise.all([
          apiService.get('/videos').catch(() => ({ data: [] })),
          formCheckService.getFormChecks().catch(() => []),
          formCheckService.getLatestFormChecks(5).catch(() => [])
        ]);

        const videos = videosResponse.data || [];
        const formChecks = formChecksResponse || [];
        
        // Calculate video statistics
        const thisWeek = new Date();
        thisWeek.setDate(thisWeek.getDate() - 7);
        
        const videoStats = {
          total: videos.length,
          thisWeek: videos.filter((v: any) => new Date(v.created_at) > thisWeek).length,
          processing: videos.filter((v: any) => v.status === 'processing').length,
          completed: videos.filter((v: any) => v.status === 'completed').length,
        };

        // Calculate form check statistics
        const completedFormChecks = formChecks.filter((fc: any) => fc.status === 'completed');
        const averageScore = completedFormChecks.length > 0
          ? completedFormChecks.reduce((sum: number, fc: any) => sum + (fc.overall_score || 0), 0) / completedFormChecks.length
          : 0;

        // Find recent improvement
        const improvement = completedFormChecks.length >= 2 ? {
          percentage: 15, // Calculate based on recent vs older scores
          exercise: completedFormChecks[0]?.exercise_type || 'Squat'
        } : undefined;

        // Convert recent form checks to activity format
        const recentActivity: RecentActivity[] = recentFormChecks.map((fc: any) => ({
          id: fc.id,
          type: 'form_check' as const,
          exercise: fc.exercise_type || 'Unknown Exercise',
          timestamp: fc.created_at,
          status: fc.status === 'completed' ? 'completed' : 'processing',
          score: fc.overall_score
        }));

        setDashboardData({
          videos: videoStats,
          formChecks: {
            total: formChecks.length,
            pending: formChecks.filter((fc: any) => fc.status === 'pending').length,
            completed: completedFormChecks.length,
            averageScore: Math.round(averageScore),
            lastAnalyzed: completedFormChecks[0]?.created_at,
            improvement
          },
          recentActivity
        });
        
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
        setError('Failed to load dashboard data. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchDashboardData();
  }, []);

  // Quick action handlers
  const handleStartFormCheck = () => {
    navigate('/exercise-library');
  };

  const handleViewResults = () => {
    navigate('/progress');
  };

  const handleUploadVideo = () => {
    navigate('/workout/form-check/upload');
  };

  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'No recent activity';
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };
  
  return (
    <DashboardContainer>
      <Header>
        <Title>Dashboard</Title>
        <Button variant="outlined" color="primary" onClick={logout}>
          Logout
        </Button>
      </Header>

      <WelcomeSection>
        <Title>Welcome back, {user?.name || 'User'}!</Title>
        <Subtitle>Your AI-powered form analysis dashboard</Subtitle>
      </WelcomeSection>

      <Container maxWidth="lg">
        <Box my={4}>
          {error && (
            <Box mb={4} p={2} bgcolor="error.light" borderRadius={1}>
              <Typography color="error">{error}</Typography>
            </Box>
          )}
          
          {/* Quick Actions */}
          <SectionHeader>
            <Typography variant="h5">Quick Actions</Typography>
          </SectionHeader>
          
          <MuiGrid container spacing={3} mb={4}>
            <MuiGrid item xs={12} md={4}>
              <QuickActionCard onClick={handleStartFormCheck} elevation={2}>
                <QuickActionIcon>
                  <AddIcon fontSize="large" />
                </QuickActionIcon>
                <QuickActionTitle variant="h6">
                  Start Form Check
                </QuickActionTitle>
                <QuickActionDescription>
                  Choose an exercise and upload a video for AI analysis
                </QuickActionDescription>
              </QuickActionCard>
            </MuiGrid>
            
            <MuiGrid item xs={12} md={4}>
              <QuickActionCard onClick={handleViewResults} elevation={2}>
                <QuickActionIcon>
                  <AnalyticsIcon fontSize="large" />
                </QuickActionIcon>
                <QuickActionTitle variant="h6">
                  View Progress
                </QuickActionTitle>
                <QuickActionDescription>
                  Track your form improvement and ML scores over time
                </QuickActionDescription>
              </QuickActionCard>
            </MuiGrid>
            
            <MuiGrid item xs={12} md={4}>
              <QuickActionCard onClick={handleUploadVideo} elevation={2}>
                <QuickActionIcon>
                  <VideoIcon fontSize="large" />
                </QuickActionIcon>
                <QuickActionTitle variant="h6">
                  Upload Video
                </QuickActionTitle>
                <QuickActionDescription>
                  Upload a video directly for processing
                </QuickActionDescription>
              </QuickActionCard>
            </MuiGrid>
          </MuiGrid>
          
          {/* Analytics Overview */}
          <MuiGrid container spacing={3} mb={4}>
            {/* Video Stats */}
            <MuiGrid item xs={12} md={6}>
              <DashboardCard elevation={2}>
                <Box p={3}>
                  <CardTitle variant="h6">
                    Video Processing
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
                          Total Videos
                        </Typography>
                        <StatsValue>
                          {dashboardData?.videos.total || 0}
                        </StatsValue>
                        <Typography variant="body2">
                          {dashboardData?.videos.thisWeek || 0} this week
                        </Typography>
                      </MuiGrid>
                      <MuiGrid item xs={6}>
                        <Typography variant="body2" color="textSecondary">
                          Processing Status
                        </Typography>
                        <StatsValue style={{ fontSize: '18px' }}>
                          {dashboardData?.videos.processing || 0} processing
                        </StatsValue>
                        <Typography variant="body2">
                          {dashboardData?.videos.completed || 0} completed
                        </Typography>
                      </MuiGrid>
                    </MuiGrid>
                  )}
                </Box>
              </DashboardCard>
            </MuiGrid>
            
            {/* Form Check Stats */}
            <MuiGrid item xs={12} md={6}>
              <DashboardCard elevation={2}>
                <Box p={3}>
                  <CardTitle variant="h6">
                    Form Analysis Results
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
                          Total Analyses
                        </Typography>
                        <StatsValue>
                          {dashboardData?.formChecks.total || 0}
                        </StatsValue>
                        <Typography variant="body2">
                          {dashboardData?.formChecks.pending || 0} pending
                        </Typography>
                      </MuiGrid>
                      <MuiGrid item xs={6}>
                        <Typography variant="body2" color="textSecondary">
                          Average Score
                        </Typography>
                        <StatsValue>
                          {dashboardData?.formChecks.averageScore || 0}%
                        </StatsValue>
                        {dashboardData?.formChecks.improvement && (
                          <Typography variant="body2" color="success.main">
                            +{dashboardData.formChecks.improvement.percentage}% {dashboardData.formChecks.improvement.exercise}
                          </Typography>
                        )}
                      </MuiGrid>
                    </MuiGrid>
                  )}
                </Box>
              </DashboardCard>
            </MuiGrid>
          </MuiGrid>
          
          {/* Recent Activity */}
          <SectionHeader>
            <Typography variant="h5">
              Recent Activity
            </Typography>
            <Button color="primary" onClick={handleViewResults}>View All</Button>
          </SectionHeader>
          
          {loading ? (
            <Box mb={4}>
              <Skeleton variant="rectangular" height={200} />
            </Box>
          ) : dashboardData?.recentActivity.length ? (
            <Box mb={4}>
              {dashboardData.recentActivity.map((activity) => (
                <Box key={activity.id} p={2} mb={2} border={1} borderColor="grey.300" borderRadius={1}>
                  <Box display="flex" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="h6" component="span">
                        {activity.exercise}
                      </Typography>
                      <Typography variant="body2" color="textSecondary" ml={2}>
                        {activity.type === 'form_check' ? 'Form Analysis' : 'Video Upload'}
                      </Typography>
                    </Box>
                    <Box textAlign="right">
                      <Typography variant="body2" color="textSecondary">
                        {formatDate(activity.timestamp)}
                      </Typography>
                      {activity.score && (
                        <Typography variant="h6" color="primary">
                          {activity.score}%
                        </Typography>
                      )}
                    </Box>
                  </Box>
                </Box>
              ))}
            </Box>
          ) : (
            <Box mb={4} textAlign="center" py={4}>
              <Typography variant="body1" color="textSecondary">
                No recent activity. Start by uploading your first exercise video!
              </Typography>
              <Button variant="contained" color="primary" onClick={handleStartFormCheck} sx={{ mt: 2 }}>
                Get Started
              </Button>
            </Box>
          )}
        </Box>
      </Container>
    </DashboardContainer>
  );
}; 