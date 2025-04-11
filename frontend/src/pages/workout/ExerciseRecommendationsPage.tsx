import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Chip,
  Grid,
  SelectChangeEvent,
} from '@mui/material';
import { ExerciseRecommendations } from '../../components/exercise/ExerciseRecommendations';
import { RecommendationRequest } from '../../services/exerciseRecommendationService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`recommendations-tabpanel-${index}`}
      aria-labelledby={`recommendations-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export const ExerciseRecommendationsPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [fitnessLevel, setFitnessLevel] = useState<RecommendationRequest['fitnessLevel']>('beginner');
  const [goals, setGoals] = useState<string[]>([]);
  const [preferences, setPreferences] = useState<RecommendationRequest['preferences']>({
    equipment: [],
    timeAvailable: 30,
    targetMuscleGroups: [],
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleFitnessLevelChange = (event: SelectChangeEvent<RecommendationRequest['fitnessLevel']>) => {
    setFitnessLevel(event.target.value as RecommendationRequest['fitnessLevel']);
  };

  const handleGoalsChange = (event: SelectChangeEvent<string[]>) => {
    setGoals(event.target.value as string[]);
  };

  const handlePreferencesChange = (field: keyof RecommendationRequest['preferences'], value: any) => {
    setPreferences(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Exercise Recommendations
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="recommendations tabs"
        >
          <Tab label="Quick Start" />
          <Tab label="Customize" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Fitness Level</InputLabel>
                <Select
                  value={fitnessLevel}
                  onChange={handleFitnessLevelChange}
                  label="Fitness Level"
                >
                  <MenuItem value="beginner">Beginner</MenuItem>
                  <MenuItem value="intermediate">Intermediate</MenuItem>
                  <MenuItem value="advanced">Advanced</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Goals</InputLabel>
                <Select
                  multiple
                  value={goals}
                  onChange={handleGoalsChange}
                  label="Goals"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} />
                      ))}
                    </Box>
                  )}
                >
                  <MenuItem value="strength">Build Strength</MenuItem>
                  <MenuItem value="endurance">Improve Endurance</MenuItem>
                  <MenuItem value="flexibility">Increase Flexibility</MenuItem>
                  <MenuItem value="weight-loss">Weight Loss</MenuItem>
                  <MenuItem value="muscle-gain">Muscle Gain</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Available Equipment</InputLabel>
                <Select
                  multiple
                  value={preferences.equipment}
                  onChange={(e) => handlePreferencesChange('equipment', e.target.value)}
                  label="Available Equipment"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} />
                      ))}
                    </Box>
                  )}
                >
                  <MenuItem value="dumbbells">Dumbbells</MenuItem>
                  <MenuItem value="barbell">Barbell</MenuItem>
                  <MenuItem value="kettlebell">Kettlebell</MenuItem>
                  <MenuItem value="resistance-bands">Resistance Bands</MenuItem>
                  <MenuItem value="bodyweight">Bodyweight Only</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                type="number"
                label="Time Available (minutes)"
                value={preferences.timeAvailable}
                onChange={(e) => handlePreferencesChange('timeAvailable', Number(e.target.value))}
              />
            </Grid>
            <Grid item xs={12}>
              <FormControl fullWidth>
                <InputLabel>Target Muscle Groups</InputLabel>
                <Select
                  multiple
                  value={preferences.targetMuscleGroups}
                  onChange={(e) => handlePreferencesChange('targetMuscleGroups', e.target.value)}
                  label="Target Muscle Groups"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => (
                        <Chip key={value} label={value} />
                      ))}
                    </Box>
                  )}
                >
                  <MenuItem value="chest">Chest</MenuItem>
                  <MenuItem value="back">Back</MenuItem>
                  <MenuItem value="legs">Legs</MenuItem>
                  <MenuItem value="shoulders">Shoulders</MenuItem>
                  <MenuItem value="arms">Arms</MenuItem>
                  <MenuItem value="core">Core</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>

      <ExerciseRecommendations
        userId="current-user-id" // This should be replaced with actual user ID from auth context
        fitnessLevel={fitnessLevel}
        goals={goals}
        preferences={preferences}
      />
    </Box>
  );
}; 