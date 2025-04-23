import React from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import { useFormCheck } from '../../hooks/useFormCheck';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

const History: React.FC = () => {
  const { formChecks, isLoading, error } = useFormCheck();

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
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>No form checks found</Typography>
        <Typography>Start by recording your first form check</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Form Check History
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Exercise Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Feedback</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {formChecks.map((check) => (
              <TableRow key={check.id}>
                <TableCell role="cell">{new Date(check.created_at).toLocaleDateString()}</TableCell>
                <TableCell role="cell">{check.exercise_type}</TableCell>
                <TableCell role="cell">{check.status}</TableCell>
                <TableCell role="cell">{check.overall_feedback || '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default History; 