import React, { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  TablePagination,
  Alert,
  Chip,
} from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useApi } from '../hooks/useApi';
import { FormCheck, ExerciseType } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBoundaryWrapper from '../components/ErrorBoundary';

const exerciseTypeLabels: Record<ExerciseType, string> = {
  squat: 'Squat',
  deadlift: 'Deadlift',
  bench_press: 'Bench Press',
  overhead_press: 'Overhead Press',
};

const getScoreColor = (score: number) => {
  if (score >= 90) return 'success';
  if (score >= 70) return 'warning';
  return 'error';
};

const HistoryContent = () => {
  const navigate = useNavigate();
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(10);
  const { data: history, loading, error, execute: fetchHistory } = useApi<FormCheck[]>('form-checks', 'get');

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const chartData = useMemo(() => {
    if (!history) return [];
    return history
      .slice()
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .map(check => ({
        date: new Date(check.created_at).toLocaleDateString(),
        score: check.score,
        exercise: exerciseTypeLabels[check.exercise_type],
      }));
  }, [history]);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <LoadingSpinner size="large" />
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md">
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="contained" onClick={() => fetchHistory()}>
          Retry
        </Button>
      </Container>
    );
  }

  if (!history?.length) {
    return (
      <Container maxWidth="md">
        <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No form checks yet
          </Typography>
          <Typography color="text.secondary" paragraph>
            Start by uploading a video for analysis
          </Typography>
          <Button variant="contained" onClick={() => navigate('/')}>
            Upload Video
          </Button>
        </Paper>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Form Check History
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={() => navigate('/')}
          sx={{ mr: 2 }}
        >
          New Analysis
        </Button>
      </Box>

      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Progress Over Time
        </Typography>
        <Box sx={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="score"
                stroke="#2196f3"
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Paper>

      <TableContainer component={Paper} elevation={3}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Exercise</TableCell>
              <TableCell>Score</TableCell>
              <TableCell>Issues</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {history
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((check) => (
                <TableRow key={check.id} hover>
                  <TableCell>
                    {new Date(check.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    {exerciseTypeLabels[check.exercise_type]}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={`${check.score}%`}
                      color={getScoreColor(check.score)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {check.issues.length > 0
                      ? check.issues.join(', ')
                      : 'No issues found'}
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => navigate(`/results/${check.id}`)}
                    >
                      View Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={history.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>
    </Container>
  );
};

const History = () => {
  const handleError = (error: Error) => {
    console.error('History Error:', error);
  };

  return (
    <ErrorBoundaryWrapper onError={handleError}>
      <HistoryContent />
    </ErrorBoundaryWrapper>
  );
};

export default History; 