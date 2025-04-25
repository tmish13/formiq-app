import React from 'react';
import styled from 'styled-components';
import { ExerciseType, exerciseConfigs } from '../../services/poseAnalysis/exerciseTypes';

interface ExerciseSelectorProps {
  selectedExercise: ExerciseType;
  onExerciseChange: (exercise: ExerciseType) => void;
}

const Container = styled.div`
  padding: ${props => props.theme.spacing.md};
`;

const Select = styled.select`
  width: 100%;
  padding: ${props => props.theme.spacing.sm};
  margin-bottom: ${props => props.theme.spacing.md};
  border: 1px solid ${props => props.theme.colors.border.main};
  border-radius: ${props => props.theme.borderRadius.md};
  font-family: ${props => props.theme.typography.fontFamily.primary};
  font-size: ${props => props.theme.typography.fontSize.md};
`;

const GuidelinesContainer = styled.div`
  margin-top: ${props => props.theme.spacing.lg};
`;

const Title = styled.h3`
  font-family: ${props => props.theme.typography.fontFamily.primary};
  font-size: ${props => props.theme.typography.fontSize.lg};
  margin-bottom: ${props => props.theme.spacing.md};
`;

const GuidelinesList = styled.ul`
  list-style-type: none;
  padding: 0;
`;

const GuidelineItem = styled.li`
  margin-bottom: ${props => props.theme.spacing.sm};
  font-family: ${props => props.theme.typography.fontFamily.primary};
  font-size: ${props => props.theme.typography.fontSize.md};
`;

export const ExerciseSelector: React.FC<ExerciseSelectorProps> = ({
  selectedExercise,
  onExerciseChange,
}) => {
  const formatExerciseName = (name: string) => {
    // First, split by capital letters and join with spaces
    const withSpaces = name.replace(/([A-Z])/g, ' $1').trim();
    // Then capitalize the first letter and any letter after a space
    return withSpaces.replace(/(^|\s)\w/g, letter => letter.toUpperCase());
  };

  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    onExerciseChange(event.target.value as ExerciseType);
  };

  const selectedConfig = exerciseConfigs[selectedExercise];

  return (
    <Container>
      <Select
        value={selectedExercise}
        onChange={handleChange}
        role="combobox"
      >
        {Object.values(ExerciseType).map(exercise => (
          <option key={exercise} value={exercise}>
            {formatExerciseName(exercise)}
          </option>
        ))}
      </Select>

      <GuidelinesContainer>
        <Title>Exercise Form Guidelines</Title>
        <GuidelinesList>
          {selectedConfig.formChecks.map((check, index) => (
            <GuidelineItem key={index}>
              <strong>{check.name}:</strong> {check.description}
            </GuidelineItem>
          ))}
        </GuidelinesList>
      </GuidelinesContainer>
    </Container>
  );
}; 