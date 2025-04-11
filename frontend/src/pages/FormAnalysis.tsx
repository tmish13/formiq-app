import React, { useState } from 'react';
import styled from 'styled-components';
import { ExerciseFormAnalysis } from '../components/exercise/ExerciseFormAnalysis';
import { getThemeValue, fallbacks } from '../utils/themeUtils';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
`;

const Header = styled.div`
  width: 100%;
  margin-bottom: 32px;
  text-align: center;
`;

const Title = styled.h1`
  font-size: 32px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  margin-bottom: 16px;
`;

const Description = styled.p`
  font-size: 16px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
  max-width: 600px;
  margin: 0 auto;
`;

const ExerciseSelector = styled.div`
  width: 100%;
  max-width: 400px;
  margin-bottom: 32px;
`;

const Select = styled.select`
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.colors.border)};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  font-size: 16px;
  cursor: pointer;
  
  &:focus {
    outline: none;
    border-color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
  }
`;

const exercises = [
  { id: 'squat', name: 'Squat' },
  { id: 'pushup', name: 'Push-up' },
  { id: 'plank', name: 'Plank' },
  { id: 'lunges', name: 'Lunges' },
  { id: 'deadlift', name: 'Deadlift' },
  { id: 'burpees', name: 'Burpees' },
  { id: 'mountain_climbers', name: 'Mountain Climbers' }
];

export const FormAnalysis: React.FC = () => {
  const [selectedExercise, setSelectedExercise] = useState(exercises[0].id);

  const handleAnalysisComplete = (analysis: {
    score: number;
    feedback: string[];
    videoUrl: string;
  }) => {
    // Here you can handle the analysis results, e.g., save to backend, show in UI, etc.
    console.log('Analysis completed:', analysis);
  };

  return (
    <Container>
      <Header>
        <Title>Exercise Form Analysis</Title>
        <Description>
          Record your exercise form and get real-time feedback on your technique.
          Our AI will analyze your form and provide personalized recommendations.
        </Description>
      </Header>

      <ExerciseSelector>
        <Select
          value={selectedExercise}
          onChange={(e) => setSelectedExercise(e.target.value)}
        >
          {exercises.map((exercise) => (
            <option key={exercise.id} value={exercise.id}>
              {exercise.name}
            </option>
          ))}
        </Select>
      </ExerciseSelector>

      <ExerciseFormAnalysis
        exerciseType={selectedExercise}
        onAnalysisComplete={handleAnalysisComplete}
      />
    </Container>
  );
}; 