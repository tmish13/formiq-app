import React from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import { useFormCheck } from '../../hooks/useFormCheck';
import LoadingSpinner from '../../components/atoms/LoadingSpinner';

const History: React.FC = () => {
  const { formChecks, isLoading, error } = useFormCheck();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">{error}</Typography>
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
                <TableCell>{new Date(check.created_at).toLocaleDateString()}</TableCell>
                <TableCell>{check.exercise_type}</TableCell>
                <TableCell>{check.status}</TableCell>
                <TableCell>{check.overall_feedback || '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default History; 