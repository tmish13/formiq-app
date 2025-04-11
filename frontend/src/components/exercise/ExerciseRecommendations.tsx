import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  FitnessCenter as FitnessCenterIcon,
  Timer as TimerIcon,
  Info as InfoIcon,
  SwapHoriz as SwapHorizIcon,
} from '@mui/icons-material';
import {
  exerciseRecommendationService,
  ExerciseRecommendation,
  RecommendationRequest,
  RecommendationResponse,
} from '../../services/exerciseRecommendationService';
import { Exercise } from '../../services/exerciseLibraryService';

interface ExerciseRecommendationsProps {
  userId: string;
  fitnessLevel: 'beginner' | 'intermediate' | 'advanced';
  goals: string[];
  preferences: RecommendationRequest['preferences'];
}

export const ExerciseRecommendations: React.FC<ExerciseRecommendationsProps> = ({
  userId,
  fitnessLevel,
  goals,
  preferences,
}) => {
  const [recommendations, setRecommendations] = useState<ExerciseRecommendation[]>([]);
  const [workoutPlan, setWorkoutPlan] = useState<RecommendationResponse['workoutPlan'] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedExercise, setSelectedExercise] = useState<Exercise | null>(null);
  const [alternatives, setAlternatives] = useState<Exercise[]>([]);
  const [isAlternativesDialogOpen, setIsAlternativesDialogOpen] = useState(false);

  useEffect(() => {
    loadRecommendations();
  }, [userId, fitnessLevel, goals, preferences]);

  const loadRecommendations = async () => {
    try {
      setIsLoading(true);
      const request: RecommendationRequest = {
        userId,
        fitnessLevel,
        goals,
        preferences,
      };
      const response = await exerciseRecommendationService.getRecommendations(request);
      setRecommendations(response.recommendations);
      setWorkoutPlan(response.workoutPlan);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recommendations');
    } finally {
      setIsLoading(false);
    }
  };

  const handleShowAlternatives = async (exercise: Exercise) => {
    try {
      setIsLoading(true);
      setSelectedExercise(exercise);
      const alternatives = await exerciseRecommendationService.getExerciseAlternatives(exercise.id);
      setAlternatives(alternatives);
      setIsAlternativesDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alternatives');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Typography color="error" sx={{ p: 3 }}>
        {error}
      </Typography>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Recommended Exercises
      </Typography>

      <Grid container spacing={3}>
        {recommendations.map((recommendation) => (
          <Grid item xs={12} md={6} key={recommendation.id}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Typography variant="h6">{recommendation.exercise.name}</Typography>
                  <Chip
                    label={`${Math.round(recommendation.confidence * 100)}% match`}
                    color="primary"
                    size="small"
                  />
                </Box>
                <Typography color="textSecondary" sx={{ mt: 1 }}>
                  {recommendation.reason}
                </Typography>
                <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                  <Chip
                    icon={<FitnessCenterIcon />}
                    label={recommendation.exercise.type}
                    size="small"
                  />
                  <Chip
                    icon={<TimerIcon />}
                    label={`${recommendation.exercise.duration} min`}
                    size="small"
                  />
                </Box>
                <Box sx={{ mt: 2 }}>
                  <Button
                    startIcon={<SwapHorizIcon />}
                    onClick={() => handleShowAlternatives(recommendation.exercise)}
                  >
                    Show Alternatives
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {workoutPlan && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" gutterBottom>
            Personalized Workout Plan
          </Typography>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Duration: {workoutPlan.duration} minutes
              </Typography>
              <List>
                {workoutPlan.exercises.map((exercise, index) => (
                  <ListItem key={index}>
                    <ListItemText
                      primary={exercise.exercise.name}
                      secondary={`${exercise.sets} sets × ${exercise.reps} reps (${exercise.restTime}s rest)`}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => handleShowAlternatives(exercise.exercise)}
                      >
                        <SwapHorizIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Alternatives Dialog */}
      <Dialog
        open={isAlternativesDialogOpen}
        onClose={() => setIsAlternativesDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Alternatives for {selectedExercise?.name}
        </DialogTitle>
        <DialogContent>
          <List>
            {alternatives.map((exercise) => (
              <ListItem key={exercise.id}>
                <ListItemText
                  primary={exercise.name}
                  secondary={exercise.description}
                />
                <ListItemSecondaryAction>
                  <IconButton edge="end">
                    <InfoIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsAlternativesDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}; 