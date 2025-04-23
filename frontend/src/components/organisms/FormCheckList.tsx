import React from 'react';
import { Grid, Typography, Box, Skeleton } from '@mui/material';
import { FormCheckCard } from '../molecules/FormCheckCard';
import { FormCheck } from '../../types/formCheck';

interface FormCheckListProps {
  formChecks: FormCheck[];
  onSelectFormCheck: (formCheck: FormCheck) => void;
  isLoading?: boolean;
}

// Memoize the loading skeleton to prevent unnecessary re-renders
const LoadingSkeleton = React.memo(() => (
  <Grid container spacing={3}>
    {[1, 2, 3].map((key) => (
      <Grid item xs={12} sm={6} md={4} key={key}>
        <Skeleton variant="rectangular" height={200} />
      </Grid>
    ))}
  </Grid>
));

// Memoize the empty state to prevent unnecessary re-renders
const EmptyState = React.memo(() => (
  <Box sx={{ p: 3, textAlign: 'center' }}>
    <Typography>No form checks found</Typography>
  </Box>
));

export const FormCheckList = React.memo<FormCheckListProps>(({
  formChecks,
  onSelectFormCheck,
  isLoading,
}) => {
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (formChecks.length === 0) {
    return <EmptyState />;
  }

  return (
    <Grid container spacing={3}>
      {formChecks.map((formCheck) => (
        <Grid item xs={12} sm={6} md={4} key={formCheck.id}>
          <FormCheckCard
            formCheck={formCheck}
            onSelect={onSelectFormCheck}
          />
        </Grid>
      ))}
    </Grid>
  );
}); 