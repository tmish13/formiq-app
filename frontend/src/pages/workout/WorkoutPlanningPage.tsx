import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  Typography,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { Add as AddIcon, Edit as EditIcon } from '@mui/icons-material';
import { workoutPlanningService, WorkoutTemplate, WorkoutSchedule } from '../../services/workoutPlanningService';
import { exerciseLibraryService, Exercise } from '../../services/exerciseLibraryService';
import { TemplateForm } from '../../components/workout/TemplateForm';
import { ScheduleForm } from '../../components/workout/ScheduleForm';

interface WorkoutPlanningPageProps {
  // Add any props if needed
}

export const WorkoutPlanningPage: React.FC<WorkoutPlanningPageProps> = () => {
  const [templates, setTemplates] = useState<WorkoutTemplate[]>([]);
  const [schedules, setSchedules] = useState<WorkoutSchedule[]>([]);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTemplateDialogOpen, setIsTemplateDialogOpen] = useState(false);
  const [isScheduleDialogOpen, setIsScheduleDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkoutTemplate | null>(null);
  const [selectedSchedule, setSelectedSchedule] = useState<WorkoutSchedule | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [templatesData, schedulesData, exercisesData] = await Promise.all([
        workoutPlanningService.getTemplates(),
        workoutPlanningService.getSchedules(
          new Date().toISOString(),
          new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
        ),
        exerciseLibraryService.getExercises()
      ]);
      setTemplates(templatesData);
      setSchedules(schedulesData);
      setExercises(exercisesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTemplate = async (template: Omit<WorkoutTemplate, 'id' | 'createdAt' | 'updatedAt'>) => {
    try {
      setIsLoading(true);
      const newTemplate = await workoutPlanningService.createTemplate(template);
      setTemplates([...templates, newTemplate]);
      setIsTemplateDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create template');
    } finally {
      setIsLoading(false);
    }
  };

  const handleScheduleWorkout = async (schedule: Omit<WorkoutSchedule, 'id' | 'createdAt' | 'updatedAt'>) => {
    try {
      setIsLoading(true);
      const newSchedule = await workoutPlanningService.scheduleWorkout(schedule);
      setSchedules([...schedules, newSchedule]);
      setIsScheduleDialogOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to schedule workout');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Workout Planning
      </Typography>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      <Grid container spacing={3}>
        {/* Templates Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Workout Templates</Typography>
                <Button
                  startIcon={<AddIcon />}
                  variant="contained"
                  onClick={() => setIsTemplateDialogOpen(true)}
                >
                  Create Template
                </Button>
              </Box>
              {templates.map((template) => (
                <Card key={template.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="h6">{template.name}</Typography>
                    <Typography color="textSecondary">{template.description}</Typography>
                    <Typography variant="body2">
                      Difficulty: {template.difficulty}
                    </Typography>
                    <Typography variant="body2">
                      Duration: {template.estimatedDuration} minutes
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      <IconButton size="small" onClick={() => setSelectedTemplate(template)}>
                        <EditIcon />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* Schedule Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Scheduled Workouts</Typography>
                <Button
                  startIcon={<AddIcon />}
                  variant="contained"
                  onClick={() => setIsScheduleDialogOpen(true)}
                >
                  Schedule Workout
                </Button>
              </Box>
              {schedules.map((schedule) => (
                <Card key={schedule.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Typography variant="h6">
                      {templates.find(t => t.id === schedule.templateId)?.name}
                    </Typography>
                    <Typography color="textSecondary">
                      Scheduled for: {new Date(schedule.scheduledDate).toLocaleDateString()}
                    </Typography>
                    <Typography variant="body2">
                      Status: {schedule.completed ? 'Completed' : 'Pending'}
                    </Typography>
                    <Box sx={{ mt: 1 }}>
                      <IconButton size="small" onClick={() => setSelectedSchedule(schedule)}>
                        <EditIcon />
                      </IconButton>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Template Dialog */}
      <Dialog 
        open={isTemplateDialogOpen} 
        onClose={() => setIsTemplateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedTemplate ? 'Edit Workout Template' : 'Create Workout Template'}
        </DialogTitle>
        <DialogContent>
          <TemplateForm
            template={selectedTemplate || undefined}
            exercises={exercises}
            onSubmit={handleCreateTemplate}
            onCancel={() => setIsTemplateDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Schedule Dialog */}
      <Dialog 
        open={isScheduleDialogOpen} 
        onClose={() => setIsScheduleDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {selectedSchedule ? 'Edit Workout Schedule' : 'Schedule Workout'}
        </DialogTitle>
        <DialogContent>
          <ScheduleForm
            templates={templates}
            onSubmit={handleScheduleWorkout}
            onCancel={() => setIsScheduleDialogOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
}; 