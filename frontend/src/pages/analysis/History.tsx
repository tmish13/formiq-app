import React, { useState, useEffect, useMemo } from 'react';
import { 
  Box, 
  Typography, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper,
  Chip,
  IconButton,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Grid,
  Card,
  CardContent,
  Button,
  Tooltip,
  Avatar
} from '@mui/material';
import { 
  Visibility as ViewIcon, 
  Delete as DeleteIcon, 
  FilterList as FilterIcon,
  Assessment as AssessmentIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { useFormCheck } from '../../hooks/useFormCheck';
import { LoadingSpinner } from '../../components/atoms/LoadingSpinner';
import { MLScoreCard } from '../../components/molecules/MLScoreCard';
import { FormCheck, ExerciseType, FormCheckStatus } from '../../types/formCheck';
import { MLScores } from '../../types/ml';

const History: React.FC = () => {
  const { formChecks, isLoading, error, fetchFormChecks, deleteFormCheckById } = useFormCheck();
  const [filterExercise, setFilterExercise] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'table' | 'cards'>('cards');

  useEffect(() => {
    fetchFormChecks();
  }, [fetchFormChecks]);

  // Filter and search logic
  const filteredFormChecks = useMemo(() => {
    if (!formChecks) return [];
    
    return formChecks.filter(check => {
      const matchesExercise = filterExercise === 'all' || check.exercise_type === filterExercise;
      const matchesStatus = filterStatus === 'all' || check.status === filterStatus;
      const matchesSearch = searchTerm === '' || 
        check.exercise_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (check.overall_feedback && check.overall_feedback.toLowerCase().includes(searchTerm.toLowerCase()));
      
      return matchesExercise && matchesStatus && matchesSearch;
    });
  }, [formChecks, filterExercise, filterStatus, searchTerm]);

  // Get exercise type color
  const getExerciseColor = (exerciseType: ExerciseType): string => {
    const colors: Record<ExerciseType, string> = {
      squat: '#4CAF50',
      deadlift: '#FF9500',
      bench_press: '#2196F3',
      overhead_press: '#9C27B0',
      barbell_row: '#FF5722',
      pullup: '#795548',
      pushup: '#607D8B'
    };
    return colors[exerciseType] || '#757575';
  };

  // Get status color
  const getStatusColor = (status: FormCheckStatus): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status) {
      case 'completed': return 'success';
      case 'analyzing': return 'info';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  // Format exercise name
  const formatExerciseName = (exerciseType: ExerciseType): string => {
    return exerciseType.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this form check?')) {
      await deleteFormCheckById(id);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ p: 3, display: 'flex', justifyContent: 'center' }}>
        <LoadingSpinner ariaLabel="Loading form checks" />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error" role="alert">{error}</Typography>
      </Box>
    );
  }

  if (!formChecks || formChecks.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <AssessmentIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" gutterBottom>No form checks found</Typography>
        <Typography color="text.secondary" mb={3}>
          Start by recording your first form check to see your progress here
        </Typography>
        <Button variant="contained" href="/analysis">
          Start Form Check
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ScheduleIcon />
          Exercise History
        </Typography>
        <Typography color="text.secondary">
          Track your form improvement across all exercises with detailed ML analysis
        </Typography>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                size="small"
                placeholder="Search exercises..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Exercise Type</InputLabel>
                <Select
                  value={filterExercise}
                  label="Exercise Type"
                  onChange={(e) => setFilterExercise(e.target.value)}
                >
                  <MenuItem value="all">All Exercises</MenuItem>
                  <MenuItem value="squat">Squat</MenuItem>
                  <MenuItem value="deadlift">Deadlift</MenuItem>
                  <MenuItem value="bench_press">Bench Press</MenuItem>
                  <MenuItem value="overhead_press">Overhead Press</MenuItem>
                  <MenuItem value="barbell_row">Barbell Row</MenuItem>
                  <MenuItem value="pullup">Pull Up</MenuItem>
                  <MenuItem value="pushup">Push Up</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  value={filterStatus}
                  label="Status"
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <MenuItem value="all">All Status</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                  <MenuItem value="analyzing">Analyzing</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                  <MenuItem value="failed">Failed</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Button
                variant="outlined"
                fullWidth
                onClick={() => setViewMode(viewMode === 'cards' ? 'table' : 'cards')}
              >
                {viewMode === 'cards' ? 'Table View' : 'Card View'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Results */}
      {filteredFormChecks.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 6 }}>
          <FilterIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" gutterBottom>No matching form checks</Typography>
          <Typography color="text.secondary">
            Try adjusting your filters or search term
          </Typography>
        </Box>
      ) : viewMode === 'cards' ? (
        <Grid container spacing={3}>
          {filteredFormChecks.map((check) => (
            <Grid item xs={12} md={6} lg={4} key={check.id}>
              <Card sx={{ height: '100%' }}>
                <CardContent>
                  {/* Header */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Avatar 
                        sx={{ 
                          bgcolor: getExerciseColor(check.exercise_type), 
                          width: 32, 
                          height: 32,
                          fontSize: '0.875rem'
                        }}
                      >
                        {check.exercise_type.charAt(0).toUpperCase()}
                      </Avatar>
                      <Typography variant="h6">
                        {formatExerciseName(check.exercise_type)}
                      </Typography>
                    </Box>
                    <Chip 
                      label={check.status} 
                      color={getStatusColor(check.status)}
                      size="small"
                    />
                  </Box>

                  {/* Date and Score */}
                  <Box sx={{ mb: 2 }}>
                    <Typography color="text.secondary" variant="body2">
                      {new Date(check.created_at).toLocaleDateString()} at {new Date(check.created_at).toLocaleTimeString()}
                    </Typography>
                    {check.score && (
                      <Typography variant="h5" color="primary" sx={{ mt: 1 }}>
                        {Math.round(check.score)}%
                      </Typography>
                    )}
                  </Box>

                  {/* ML Scores */}
                  {check.posture_score && check.stability_score && check.depth_score && (
                    <Box sx={{ mb: 2 }}>
                      <MLScoreCard
                        scores={{
                          posture_score: check.posture_score,
                          stability_score: check.stability_score,
                          depth_score: check.depth_score,
                          confidence: check.confidence_score
                        }}
                        variant="compact"
                        showTrend={false}
                        showConfidence={false}
                      />
                    </Box>
                  )}

                  {/* Feedback */}
                  {check.overall_feedback && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {check.overall_feedback.substring(0, 120)}
                      {check.overall_feedback.length > 120 && '...'}
                    </Typography>
                  )}

                  {/* Actions */}
                  <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                    <Tooltip title="View Details">
                      <IconButton size="small" href={`/analysis/results/${check.id}`}>
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" color="error" onClick={() => handleDelete(check.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Date</TableCell>
                <TableCell>Exercise</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Score</TableCell>
                <TableCell>ML Scores</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredFormChecks.map((check) => (
                <TableRow key={check.id}>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(check.created_at).toLocaleDateString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(check.created_at).toLocaleTimeString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Avatar 
                        sx={{ 
                          bgcolor: getExerciseColor(check.exercise_type), 
                          width: 24, 
                          height: 24,
                          fontSize: '0.75rem'
                        }}
                      >
                        {check.exercise_type.charAt(0).toUpperCase()}
                      </Avatar>
                      {formatExerciseName(check.exercise_type)}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={check.status} 
                      color={getStatusColor(check.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {check.score ? `${Math.round(check.score)}%` : '-'}
                  </TableCell>
                  <TableCell>
                    {check.posture_score && check.stability_score && check.depth_score ? (
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Chip label={`P: ${Math.round(check.posture_score)}`} size="small" />
                        <Chip label={`S: ${Math.round(check.stability_score)}`} size="small" />
                        <Chip label={`D: ${Math.round(check.depth_score)}`} size="small" />
                      </Box>
                    ) : '-'}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton size="small" href={`/analysis/results/${check.id}`}>
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <IconButton size="small" color="error" onClick={() => handleDelete(check.id)}>
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default History; 