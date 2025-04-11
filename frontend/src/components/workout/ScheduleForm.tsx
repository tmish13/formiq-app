import React, { useState } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Grid,
} from '@mui/material';
import { WorkoutSchedule, WorkoutTemplate } from '../../services/workoutPlanningService';

interface ScheduleFormProps {
  templates: WorkoutTemplate[];
  onSubmit: (schedule: Omit<WorkoutSchedule, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onCancel: () => void;
}

export const ScheduleForm: React.FC<ScheduleFormProps> = ({
  templates,
  onSubmit,
  onCancel,
}) => {
  const [templateId, setTemplateId] = useState('');
  const [scheduledDate, setScheduledDate] = useState('');
  const [notes, setNotes] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      templateId,
      userId: 'current-user-id', // This should be replaced with actual user ID from auth context
      scheduledDate,
      completed: false,
      notes,
    });
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ p: 2 }}>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <FormControl fullWidth>
            <InputLabel>Workout Template</InputLabel>
            <Select
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              label="Workout Template"
              required
            >
              {templates.map((template) => (
                <MenuItem key={template.id} value={template.id}>
                  {template.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            type="datetime-local"
            label="Schedule Date & Time"
            value={scheduledDate}
            onChange={(e) => setScheduledDate(e.target.value)}
            required
            InputLabelProps={{
              shrink: true,
            }}
          />
        </Grid>
        <Grid item xs={12}>
          <TextField
            fullWidth
            label="Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            rows={3}
          />
        </Grid>
        <Grid item xs={12}>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button onClick={onCancel} variant="outlined">
              Cancel
            </Button>
            <Button type="submit" variant="contained">
              Schedule Workout
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}; 