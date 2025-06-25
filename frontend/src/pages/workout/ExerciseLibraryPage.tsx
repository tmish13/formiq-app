import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
  Container, 
  Grid, 
  Typography, 
  TextField, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel,
  Chip,
  Card,
  CardContent,
  CardMedia,
  CardActionArea,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  Slider,
  Divider
} from '@mui/material';
import { 
  Search as SearchIcon,
  FilterList as FilterListIcon,
  FitnessCenter as FitnessCenterIcon,
  Timer as TimerIcon,
  TrendingUp as TrendingUpIcon,
  Add as AddIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { 
  exerciseLibraryService, 
  type Exercise, 
  type ExerciseLibraryFilters,
  ExerciseType,
  ExerciseDifficulty
} from '../../services/exerciseLibraryService';
import { lightTheme } from '../../theme';

const ExerciseLibraryPage: React.FC = () => {
  const navigate = useNavigate();
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [filters, setFilters] = useState<ExerciseLibraryFilters>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [muscleGroups, setMuscleGroups] = useState<string[]>([]);
  const [equipment, setEquipment] = useState<string[]>([]);
  const [selectedMuscleGroups, setSelectedMuscleGroups] = useState<string[]>([]);
  const [selectedEquipment, setSelectedEquipment] = useState<string[]>([]);
  const [durationRange, setDurationRange] = useState<[number, number]>([0, 60]);

  useEffect(() => {
    fetchExercises();
    fetchMuscleGroups();
    fetchEquipment();
  }, []);

  useEffect(() => {
    fetchExercises();
  }, [filters]);

  const fetchExercises = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await exerciseLibraryService.getExercises(filters);
      setExercises(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch exercises');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchMuscleGroups = async () => {
    try {
      const data = await exerciseLibraryService.getMuscleGroups();
      setMuscleGroups(data);
    } catch (err) {
      console.error('Failed to fetch muscle groups:', err);
    }
  };

  const fetchEquipment = async () => {
    try {
      const data = await exerciseLibraryService.getEquipment();
      setEquipment(data);
    } catch (err) {
      console.error('Failed to fetch equipment:', err);
    }
  };

  const handleSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    const query = event.target.value;
    setSearchQuery(query);
    setFilters(prev => ({ ...prev, searchQuery: query }));
  };

  const handleFilterChange = (field: keyof ExerciseLibraryFilters, value: any) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleMuscleGroupChange = (muscleGroup: string) => {
    setSelectedMuscleGroups(prev => {
      const newSelection = prev.includes(muscleGroup)
        ? prev.filter(m => m !== muscleGroup)
        : [...prev, muscleGroup];
      
      setFilters(prevFilters => ({ 
        ...prevFilters, 
        muscleGroups: newSelection.length > 0 ? newSelection : undefined 
      }));
      
      return newSelection;
    });
  };

  const handleEquipmentChange = (equipmentItem: string) => {
    setSelectedEquipment(prev => {
      const newSelection = prev.includes(equipmentItem)
        ? prev.filter(e => e !== equipmentItem)
        : [...prev, equipmentItem];
      
      setFilters(prevFilters => ({ 
        ...prevFilters, 
        equipment: newSelection.length > 0 ? newSelection : undefined 
      }));
      
      return newSelection;
    });
  };

  const handleDurationChange = (_event: Event, newValue: number | number[]) => {
    const [min, max] = newValue as number[];
    setDurationRange([min, max]);
    setFilters(prev => ({ 
      ...prev, 
      duration: { min, max } 
    }));
  };

  const handleClearFilters = () => {
    setFilters({});
    setSearchQuery('');
    setSelectedMuscleGroups([]);
    setSelectedEquipment([]);
    setDurationRange([0, 60]);
  };

  const handleExerciseClick = (exerciseId: string) => {
    navigate(`/workout/exercise/${exerciseId}`);
  };

  const handleStartFormCheck = (exerciseId: string, exerciseName: string) => {
    // Navigate to upload page with exercise pre-selected
    navigate('/workout/form-check/upload', { 
      state: { 
        exerciseId, 
        exerciseName,
        fromLibrary: true 
      } 
    });
  };

  const renderExerciseCard = (exercise: Exercise) => (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        transition: 'transform 0.2s',
        '&:hover': {
          transform: 'scale(1.02)',
          boxShadow: lightTheme.shadows.lg
        }
      }}
    >
      <CardActionArea onClick={() => handleExerciseClick(exercise.id)}>
        <CardMedia
          component="img"
          height="140"
          image={exercise.thumbnailUrl || '/placeholder-exercise.jpg'}
          alt={exercise.name}
        />
        <CardContent>
          <Typography gutterBottom variant="h6" component="h2">
            {exercise.name}
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {exercise.description}
          </Typography>
          <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Chip 
              size="small" 
              label={exercise.difficulty} 
              color={
                exercise.difficulty === ExerciseDifficulty.BEGINNER ? 'success' :
                exercise.difficulty === ExerciseDifficulty.INTERMEDIATE ? 'warning' : 'error'
              }
            />
            <Chip 
              size="small" 
              icon={<FitnessCenterIcon />} 
              label={exercise.type} 
            />
            {exercise.metrics && (
              <Chip 
                size="small" 
                icon={<TimerIcon />} 
                label={`${exercise.metrics.recommendedSets}x${exercise.metrics.recommendedReps}`} 
              />
            )}
          </Box>
        </CardContent>
      </CardActionArea>
      
      {/* Action buttons outside of CardActionArea */}
      <Box sx={{ p: 2, pt: 0, mt: 'auto' }}>
        <Button
          variant="contained"
          color="primary"
          fullWidth
          startIcon={<AddIcon />}
          onClick={(e) => {
            e.stopPropagation();
            handleStartFormCheck(exercise.id, exercise.name);
          }}
          sx={{ mb: 1 }}
        >
          Start Form Check
        </Button>
        <Button
          variant="outlined"
          color="secondary"
          fullWidth
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            handleExerciseClick(exercise.id);
          }}
        >
          View Details
        </Button>
      </Box>
    </Card>
  );

  const renderFilterDialog = () => (
    <Dialog 
      open={showFilters} 
      onClose={() => setShowFilters(false)}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Filter Exercises</Typography>
          <IconButton onClick={() => setShowFilters(false)}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Type</InputLabel>
              <Select
                value={filters.type || ''}
                label="Type"
                onChange={(e) => handleFilterChange('type', e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                {Object.values(ExerciseType).map(type => (
                  <MenuItem key={type} value={type}>{type}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Difficulty</InputLabel>
              <Select
                value={filters.difficulty || ''}
                label="Difficulty"
                onChange={(e) => handleFilterChange('difficulty', e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                {Object.values(ExerciseDifficulty).map(difficulty => (
                  <MenuItem key={difficulty} value={difficulty}>{difficulty}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" gutterBottom>Muscle Groups</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {muscleGroups.map(muscleGroup => (
                <Chip
                  key={muscleGroup}
                  label={muscleGroup}
                  onClick={() => handleMuscleGroupChange(muscleGroup)}
                  color={selectedMuscleGroups.includes(muscleGroup) ? 'primary' : 'default'}
                  variant={selectedMuscleGroups.includes(muscleGroup) ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          </Grid>
          
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" gutterBottom>Equipment</Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {equipment.map(item => (
                <Chip
                  key={item}
                  label={item}
                  onClick={() => handleEquipmentChange(item)}
                  color={selectedEquipment.includes(item) ? 'primary' : 'default'}
                  variant={selectedEquipment.includes(item) ? 'filled' : 'outlined'}
                />
              ))}
            </Box>
          </Grid>
          
          <Grid item xs={12}>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" gutterBottom>Duration (minutes)</Typography>
            <Box sx={{ px: 2 }}>
              <Slider
                value={durationRange}
                onChange={handleDurationChange}
                valueLabelDisplay="auto"
                min={0}
                max={60}
                step={1}
              />
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">{durationRange[0]} min</Typography>
                <Typography variant="body2">{durationRange[1]} min</Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClearFilters}>Clear Filters</Button>
        <Button variant="contained" onClick={() => setShowFilters(false)}>Apply</Button>
      </DialogActions>
    </Dialog>
  );

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Exercise Library
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Browse and search through our comprehensive exercise library
          </Typography>
        </Box>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={() => navigate('/workout/exercise/new')}
        >
          Add Exercise
        </Button>
      </Box>

      <Box sx={{ mb: 4 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Search exercises..."
              value={searchQuery}
              onChange={handleSearch}
              InputProps={{
                startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
              }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                startIcon={<FilterListIcon />}
                onClick={() => setShowFilters(true)}
              >
                Filters
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : exercises.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="h6" color="text.secondary">
            No exercises found. Try adjusting your filters.
          </Typography>
        </Box>
      ) : (
        <Grid container spacing={3}>
          {exercises.map((exercise) => (
            <Grid item key={exercise.id} xs={12} sm={6} md={4}>
              {renderExerciseCard(exercise)}
            </Grid>
          ))}
        </Grid>
      )}

      {renderFilterDialog()}
    </Container>
  );
};

export default ExerciseLibraryPage; 