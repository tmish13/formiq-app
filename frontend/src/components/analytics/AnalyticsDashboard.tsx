import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  LinearProgress,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Button,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Assessment,
  FitnessCenter,
  Timeline,
  ShowChart,
  Refresh,
  DateRange,
  FilterList
} from '@mui/icons-material';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from 'recharts';
import { FormCheck, ExerciseType } from '../../types/formCheck';
import { MLScores } from '../../types/ml';
import { FormCheckService } from '../../services/formCheckService';

// Analytics data interfaces
interface ExerciseStats {
  exercise_type: ExerciseType;
  count: number;
  avg_score: number;
  best_score: number;
  improvement: number;
  trend: 'up' | 'down' | 'stable';
}

interface TimeSeriesData {
  date: string;
  overall_score: number;
  posture_score: number;
  stability_score: number;
  depth_score: number;
  session_count: number;
}

interface PerformanceMetrics {
  totalSessions: number;
  averageScore: number;
  bestExercise: ExerciseType | null;
  weakestArea: 'posture' | 'stability' | 'depth' | null;
  improvementRate: number;
  consistency: number;
}

interface AnalyticsDashboardProps {
  timeRange?: '7d' | '30d' | '90d' | '1y';
  onTimeRangeChange?: (range: string) => void;
}

const EXERCISE_COLORS = {
  squat: '#4CAF50',
  deadlift: '#FF9500',
  bench_press: '#2196F3',
  overhead_press: '#9C27B0',
  barbell_row: '#FF5722',
  pullup: '#795548',
  pushup: '#607D8B'
} as const;

const PIE_COLORS = ['#4CAF50', '#FF9500', '#2196F3', '#9C27B0', '#FF5722', '#795548', '#607D8B'];

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  timeRange = '30d',
  onTimeRangeChange
}) => {
  const [loading, setLoading] = useState(true);
  const [formChecks, setFormChecks] = useState<FormCheck[]>([]);
  const [selectedExercise, setSelectedExercise] = useState<string>('all');
  const formCheckService = FormCheckService.getInstance();

  useEffect(() => {
    loadAnalyticsData();
  }, [timeRange]);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      const data = await formCheckService.getFormChecks();
      setFormChecks(data || []);
    } catch (error) {
      console.error('Error loading analytics data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Calculate performance metrics
  const performanceMetrics = useMemo((): PerformanceMetrics => {
    if (!formChecks.length) {
      return {
        totalSessions: 0,
        averageScore: 0,
        bestExercise: null,
        weakestArea: null,
        improvementRate: 0,
        consistency: 0
      };
    }

    const completedChecks = formChecks.filter(fc => fc.status === 'completed' && fc.score);
    const scores = completedChecks.map(fc => fc.score || 0);
    const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;

    // Calculate best exercise
    const exerciseAvgs = formChecks.reduce((acc, fc) => {
      if (fc.status === 'completed' && fc.score) {
        if (!acc[fc.exercise_type]) {
          acc[fc.exercise_type] = { total: 0, count: 0 };
        }
        acc[fc.exercise_type].total += fc.score;
        acc[fc.exercise_type].count += 1;
      }
      return acc;
    }, {} as Record<string, { total: number; count: number }>);

    let bestExercise: ExerciseType | null = null;
    let bestAvg = 0;
    Object.entries(exerciseAvgs).forEach(([exercise, { total, count }]) => {
      const avg = total / count;
      if (avg > bestAvg) {
        bestAvg = avg;
        bestExercise = exercise as ExerciseType;
      }
    });

    // Calculate weakest area from ML scores
    const mlScores = formChecks.filter(fc => fc.posture_score && fc.stability_score && fc.depth_score);
    let weakestArea: 'posture' | 'stability' | 'depth' | null = null;
    if (mlScores.length > 0) {
      const avgPosture = mlScores.reduce((sum, fc) => sum + (fc.posture_score || 0), 0) / mlScores.length;
      const avgStability = mlScores.reduce((sum, fc) => sum + (fc.stability_score || 0), 0) / mlScores.length;
      const avgDepth = mlScores.reduce((sum, fc) => sum + (fc.depth_score || 0), 0) / mlScores.length;
      
      const areas = { posture: avgPosture, stability: avgStability, depth: avgDepth };
      weakestArea = Object.entries(areas).reduce((min, [area, score]) => 
        score < areas[min] ? area as 'posture' | 'stability' | 'depth' : min, 'posture' as 'posture' | 'stability' | 'depth'
      );
    }

    return {
      totalSessions: completedChecks.length,
      averageScore: avgScore,
      bestExercise,
      weakestArea,
      improvementRate: 0, // TODO: Calculate based on time series
      consistency: 0 // TODO: Calculate consistency metric
    };
  }, [formChecks]);

  // Calculate exercise statistics
  const exerciseStats = useMemo((): ExerciseStats[] => {
    const stats = formChecks.reduce((acc, fc) => {
      if (fc.status === 'completed' && fc.score) {
        if (!acc[fc.exercise_type]) {
          acc[fc.exercise_type] = {
            exercise_type: fc.exercise_type,
            count: 0,
            total_score: 0,
            best_score: 0,
            scores: []
          };
        }
        
        const stat = acc[fc.exercise_type];
        stat.count += 1;
        stat.total_score += fc.score;
        stat.best_score = Math.max(stat.best_score, fc.score);
        stat.scores.push(fc.score);
      }
      return acc;
    }, {} as Record<string, any>);

    return Object.values(stats).map((stat: any) => ({
      exercise_type: stat.exercise_type,
      count: stat.count,
      avg_score: stat.total_score / stat.count,
      best_score: stat.best_score,
      improvement: 0, // TODO: Calculate improvement
      trend: 'stable' as const // TODO: Calculate trend
    }));
  }, [formChecks]);

  // Time series data for charts
  const timeSeriesData = useMemo((): TimeSeriesData[] => {
    // Group form checks by date
    const dailyData = formChecks.reduce((acc, fc) => {
      const date = new Date(fc.created_at).toLocaleDateString();
      if (!acc[date]) {
        acc[date] = {
          date,
          overall_scores: [],
          posture_scores: [],
          stability_scores: [],
          depth_scores: [],
          session_count: 0
        };
      }
      
      const dayData = acc[date];
      dayData.session_count += 1;
      
      if (fc.score) dayData.overall_scores.push(fc.score);
      if (fc.posture_score) dayData.posture_scores.push(fc.posture_score);
      if (fc.stability_score) dayData.stability_scores.push(fc.stability_score);
      if (fc.depth_score) dayData.depth_scores.push(fc.depth_score);
      
      return acc;
    }, {} as Record<string, any>);

    return Object.values(dailyData).map((day: any) => ({
      date: day.date,
      overall_score: day.overall_scores.length ? 
        day.overall_scores.reduce((sum: number, score: number) => sum + score, 0) / day.overall_scores.length : 0,
      posture_score: day.posture_scores.length ?
        day.posture_scores.reduce((sum: number, score: number) => sum + score, 0) / day.posture_scores.length : 0,
      stability_score: day.stability_scores.length ?
        day.stability_scores.reduce((sum: number, score: number) => sum + score, 0) / day.stability_scores.length : 0,
      depth_score: day.depth_scores.length ?
        day.depth_scores.reduce((sum: number, score: number) => sum + score, 0) / day.depth_scores.length : 0,
      session_count: day.session_count
    })).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [formChecks]);

  // Exercise distribution for pie chart
  const exerciseDistribution = useMemo(() => {
    const distribution = formChecks.reduce((acc, fc) => {
      acc[fc.exercise_type] = (acc[fc.exercise_type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(distribution).map(([exercise, count], index) => ({
      name: exercise.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
      value: count,
      color: PIE_COLORS[index % PIE_COLORS.length],
      exercise_type: exercise
    }));
  }, [formChecks]);

  const formatExerciseName = (exerciseType: string): string => {
    return exerciseType.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp color="success" />;
      case 'down': return <TrendingDown color="error" />;
      default: return <TrendingFlat color="action" />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography sx={{ mt: 2, textAlign: 'center' }}>Loading analytics...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Assessment />
            Analytics Dashboard
          </Typography>
          <Typography color="text.secondary">
            Comprehensive insights into your exercise form progress
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={(e) => onTimeRangeChange?.(e.target.value)}
            >
              <MenuItem value="7d">Last 7 days</MenuItem>
              <MenuItem value="30d">Last 30 days</MenuItem>
              <MenuItem value="90d">Last 90 days</MenuItem>
              <MenuItem value="1y">Last year</MenuItem>
            </Select>
          </FormControl>
          
          <Tooltip title="Refresh Data">
            <IconButton onClick={loadAnalyticsData}>
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Total Sessions
                  </Typography>
                  <Typography variant="h4">
                    {performanceMetrics.totalSessions}
                  </Typography>
                </Box>
                <FitnessCenter color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Average Score
                  </Typography>
                  <Typography variant="h4">
                    {Math.round(performanceMetrics.averageScore)}%
                  </Typography>
                </Box>
                <ShowChart color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Best Exercise
                  </Typography>
                  <Typography variant="h6">
                    {performanceMetrics.bestExercise ? 
                      formatExerciseName(performanceMetrics.bestExercise) : 'N/A'}
                  </Typography>
                </Box>
                <Assessment color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                  <Typography color="text.secondary" variant="body2">
                    Focus Area
                  </Typography>
                  <Typography variant="h6">
                    {performanceMetrics.weakestArea ? 
                      performanceMetrics.weakestArea.charAt(0).toUpperCase() + 
                      performanceMetrics.weakestArea.slice(1) : 'N/A'}
                  </Typography>
                </Box>
                <Timeline color="primary" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Grid */}
      <Grid container spacing={3}>
        {/* Progress Trend Chart */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Progress Over Time</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={timeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis domain={[0, 100]} />
                  <ChartTooltip formatter={(value, name) => [`${value}%`, name]} />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="overall_score" 
                    stroke="#4CAF50" 
                    fill="#4CAF5020"
                    name="Overall Score"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="posture_score" 
                    stroke="#2196F3" 
                    fill="#2196F320"
                    name="Posture Score"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="stability_score" 
                    stroke="#FF9500" 
                    fill="#FF950020"
                    name="Stability Score"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="depth_score" 
                    stroke="#9C27B0" 
                    fill="#9C27B020"
                    name="Depth Score"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Exercise Distribution */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Exercise Distribution</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={exerciseDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {exerciseDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <ChartTooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Exercise Performance Comparison */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Exercise Performance Comparison</Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={exerciseStats}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="exercise_type" 
                    tickFormatter={(value) => formatExerciseName(value)}
                  />
                  <YAxis domain={[0, 100]} />
                  <ChartTooltip 
                    formatter={(value, name) => [
                      name === 'avg_score' ? `${value.toFixed(1)}%` : value,
                      name === 'avg_score' ? 'Average Score' : 
                      name === 'best_score' ? 'Best Score' : 'Session Count'
                    ]}
                  />
                  <Legend />
                  <Bar dataKey="avg_score" fill="#4CAF50" name="Average Score" />
                  <Bar dataKey="best_score" fill="#2196F3" name="Best Score" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnalyticsDashboard;