import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { ExerciseFormAnalysis } from '../components/exercise/ExerciseFormAnalysis';
import { ResultsDisplay } from '../components/exercise/ResultsDisplay';
import { BackButton } from '../components/common/BackButton';

interface Analysis {
  score: number;
  feedback: string[];
  videoUrl: string;
}

const Container = styled.div`
  padding: ${({ theme }) => theme.spacing.md};
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const Title = styled.h1`
  color: ${({ theme }) => theme.colors.text.primary};
  margin-bottom: ${({ theme }) => theme.spacing.lg};
`;

const ExerciseSelector = styled.div`
  margin-bottom: ${({ theme }) => theme.spacing.lg};
`;

const Select = styled.select`
  padding: 10px;
  border-radius: 4px;
  border: 1px solid ${({ theme }) => theme.colors.border.main};
  background-color: ${({ theme }) => theme.colors.background.main};
  width: 100%;
  max-width: 300px;
`;

const ExerciseCard = styled.div`
  padding: ${({ theme }) => theme.spacing.md}px;
  margin-bottom: ${({ theme }) => theme.spacing.md}px;
  border-radius: 8px;
  background-color: #ffffff;
  color: ${({ theme }) => theme.colors.text.primary};
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
  }
`;

const exercises = [
  { id: 'squat', name: 'Squat' },
  { id: 'deadlift', name: 'Deadlift' },
  { id: 'bench_press', name: 'Bench Press' },
  { id: 'shoulder_press', name: 'Shoulder Press' },
];

export const FormAnalysis: React.FC = () => {
  const navigate = useNavigate();
  const [selectedExercise, setSelectedExercise] = useState(exercises[0].id);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [showResults, setShowResults] = useState(false);

  // Set active session on mount
  useEffect(() => {
    localStorage.setItem('activeSession', 'true');
    
    // Clean up on unmount
    return () => {
      localStorage.removeItem('activeSession');
    };
  }, []);

  const handleAnalysisComplete = (analysisResult: Analysis | null) => {
    if (analysisResult) {
      setAnalysis(analysisResult);
      setShowResults(true);
    }
  };
  
  const handleNewCheck = () => {
    setShowResults(false);
  };
  
  const handleBackClick = () => {
    navigate('/');
  };

  return (
    <Container>
      <Header>
        <BackButton onClick={handleBackClick} />
      </Header>
      
      <Title>Form Analysis</Title>
      
      {!showResults ? (
        <>
          <ExerciseSelector>
            <label htmlFor="exercise-selector">Select Exercise:</label>
            <Select 
              id="exercise-selector"
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
        </>
      ) : (
        <ResultsDisplay 
          results={analysis}
          onNewCheck={handleNewCheck}
        />
      )}
    </Container>
  );
}; 