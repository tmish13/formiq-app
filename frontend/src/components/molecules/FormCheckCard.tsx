import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';
import { FormCheck } from '../../types/formCheck';

interface FormCheckCardProps {
  formCheck: FormCheck;
  onSelect: (formCheck: FormCheck) => void;
}

export const FormCheckCard: React.FC<FormCheckCardProps> = ({
  formCheck,
  onSelect,
}) => {
  return (
    <Card
      sx={{ cursor: 'pointer' }}
      onClick={() => onSelect(formCheck)}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Form Check #{formCheck.id}
        </Typography>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Status: {formCheck.status}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Created: {new Date(formCheck.created_at).toLocaleDateString()}
          </Typography>
        </Box>
        {formCheck.results && (
          <Typography variant="body2">
            Results: {JSON.stringify(formCheck.results)}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}; 