import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Container,
  Alert,
  Button,
  Card,
  CardContent,
  Grid,
  Chip
} from '@mui/material';
import {
  Assessment,
  Psychology,
  Timeline,
  Settings,
  Refresh
} from '@mui/icons-material';
import { AnalyticsDashboard } from '../components/analytics/AnalyticsDashboard';
import { AdvancedFeedbackPreview } from '../components/analytics/AdvancedFeedbackPreview';
import { useFormCheck } from '../hooks/useFormCheck';
import { LoadingSpinner } from '../components/atoms/LoadingSpinner';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const a11yProps = (index: number) => {
  return {
    id: `analytics-tab-${index}`,
    'aria-controls': `analytics-tabpanel-${index}`,
  };
};

export const Analytics: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const { formChecks, isLoading, error, fetchFormChecks } = useFormCheck();

  useEffect(() => {
    fetchFormChecks();
  }, [fetchFormChecks]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleTimeRangeChange = (range: string) => {
    setTimeRange(range as '7d' | '30d' | '90d' | '1y');
  };

  const handleRefreshData = () => {
    fetchFormChecks();
  };

  // Get latest form check for feedback preview
  const latestFormCheck = formChecks && formChecks.length > 0 
    ? formChecks.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
    : null;

  const getMLScores = (formCheck: any) => {
    if (formCheck?.posture_score && formCheck?.stability_score && formCheck?.depth_score) {
      return {
        posture_score: formCheck.posture_score,
        stability_score: formCheck.stability_score,
        depth_score: formCheck.depth_score,
        confidence: formCheck.confidence_score || 0.8
      };
    }
    return undefined;
  };

  if (isLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
          <LoadingSpinner ariaLabel="Loading analytics data" />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert 
          severity="error" 
          action={
            <Button color="inherit" size="small" onClick={handleRefreshData}>
              Try Again
            </Button>
          }
        >
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Assessment fontSize="large" />
          Analytics & Insights
        </Typography>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Deep insights into your exercise form and progress powered by AI
        </Typography>
        
        {/* Quick Stats */}
        <Grid container spacing={2} sx={{ mt: 2 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">
                  Total Sessions
                </Typography>
                <Typography variant="h4" color="primary">
                  {formChecks?.length || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">
                  Completed Analyses
                </Typography>
                <Typography variant="h4" color="success.main">
                  {formChecks?.filter(fc => fc.status === 'completed').length || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">
                  AI Feedback Items
                </Typography>
                <Typography variant="h4" color="info.main">
                  {formChecks?.reduce((sum, fc) => sum + (fc.feedback_items?.length || 0), 0) || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography color="text.secondary" variant="body2">
                  Time Range
                </Typography>
                <Chip 
                  label={timeRange === '7d' ? 'Last 7 days' : 
                        timeRange === '30d' ? 'Last 30 days' :
                        timeRange === '90d' ? 'Last 90 days' : 'Last year'}
                  color="primary"
                  variant="outlined"
                />
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Navigation Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={currentTab} onChange={handleTabChange} aria-label="analytics navigation">
          <Tab 
            icon={<Assessment />} 
            label="Dashboard" 
            {...a11yProps(0)}
            sx={{ minHeight: 72 }}
          />
          <Tab 
            icon={<Psychology />} 
            label="AI Feedback" 
            {...a11yProps(1)}
            sx={{ minHeight: 72 }}
          />
          <Tab 
            icon={<Timeline />} 
            label="Progress Trends" 
            {...a11yProps(2)}
            sx={{ minHeight: 72 }}
            disabled
          />
          <Tab 
            icon={<Settings />} 
            label="Settings" 
            {...a11yProps(3)}
            sx={{ minHeight: 72 }}
            disabled
          />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <TabPanel value={currentTab} index={0}>
        <AnalyticsDashboard 
          timeRange={timeRange}
          onTimeRangeChange={handleTimeRangeChange}
        />
      </TabPanel>

      <TabPanel value={currentTab} index={1}>
        {latestFormCheck ? (
          <Box>
            <Alert severity="info" sx={{ mb: 3 }}>
              Preview of advanced AI-powered feedback features. Showing analysis for your most recent session.
            </Alert>
            <AdvancedFeedbackPreview 
              formCheck={latestFormCheck}
              mlScores={getMLScores(latestFormCheck)}
              poseIssues={[]}
              onFeedbackRating={(feedbackId, rating) => {
                console.log('Feedback rated:', feedbackId, rating);
              }}
              onApplyRecommendation={(recommendationId) => {
                console.log('Recommendation applied:', recommendationId);
              }}
            />
          </Box>
        ) : (
          <Alert severity="info">
            Complete your first form check to see AI-powered feedback insights here.
          </Alert>
        )}
      </TabPanel>

      <TabPanel value={currentTab} index={2}>
        <Alert severity="info" sx={{ mb: 3 }}>
          Advanced progress trend analysis coming soon! This will include:
        </Alert>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Movement Pattern Analysis
                </Typography>
                <Typography color="text.secondary">
                  Detailed breakdown of your movement patterns over time, 
                  identifying improvements and areas for focus.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Biomechanical Efficiency
                </Typography>
                <Typography color="text.secondary">
                  Track how efficiently you perform exercises and identify 
                  optimization opportunities for better results.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Injury Risk Assessment
                </Typography>
                <Typography color="text.secondary">
                  AI-powered analysis to identify potential injury risks 
                  based on your movement patterns and form.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Predictions
                </Typography>
                <Typography color="text.secondary">
                  Machine learning models to predict your performance 
                  improvements and optimal training adjustments.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={currentTab} index={3}>
        <Alert severity="info" sx={{ mb: 3 }}>
          Analytics settings and preferences will be available here, including:
        </Alert>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Notification Preferences
                </Typography>
                <Typography color="text.secondary">
                  Customize when and how you receive feedback and progress updates.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Data Export
                </Typography>
                <Typography color="text.secondary">
                  Export your analytics data for external analysis or backup.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>
    </Container>
  );
};

export default Analytics;