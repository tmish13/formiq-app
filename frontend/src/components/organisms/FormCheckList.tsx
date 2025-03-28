import React from 'react';
import { Grid, Typography, Box } from '@mui/material';
import { FormCheckCard } from '../molecules/FormCheckCard';
import { FormCheck } from '../../types/formCheck';

interface FormCheckListProps {
  formChecks: FormCheck[];
  onSelectFormCheck: (formCheck: FormCheck) => void;
  isLoading?: boolean;
}

export const FormCheckList: React.FC<FormCheckListProps> = ({
  formChecks,
  onSelectFormCheck,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography>Loading form checks...</Typography>
      </Box>
    );
  }

  if (formChecks.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography>No form checks found</Typography>
      </Box>
    );
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
}; 