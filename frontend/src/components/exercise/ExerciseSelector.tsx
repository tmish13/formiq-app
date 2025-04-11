import React from 'react';
import styled from 'styled-components';
import { ExerciseType, exerciseConfigs } from '../../services/poseAnalysis/exerciseTypes';

const Container = styled.div`
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 20px;
`;

const SelectWrapper = styled.div`
  margin-bottom: 20px;
`;

const Select = styled.select`
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  background: white;
`;

const ExerciseInfo = styled.div`
  background: white;
  padding: 15px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h3`
  margin: 0 0 15px 0;
  color: #333;
`;

const List = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const ListItem = styled.li`
  padding: 8px 0;
  border-bottom: 1px solid #eee;
  &:last-child {
    border-bottom: none;
  }
`;

interface ExerciseSelectorProps {
  selectedExercise: ExerciseType;
  onExerciseChange: (exercise: ExerciseType) => void;
}

export const ExerciseSelector: React.FC<ExerciseSelectorProps> = ({
  selectedExercise,
  onExerciseChange,
}) => {
  const exerciseConfig = exerciseConfigs[selectedExercise];

  return (
    <Container>
      <SelectWrapper>
        <Select
          value={selectedExercise}
          onChange={(e) => onExerciseChange(e.target.value as ExerciseType)}
        >
          {Object.values(ExerciseType).map((type) => (
            <option key={type} value={type}>
              {type.replace(/([A-Z])/g, ' $1').trim()} {/* Add spaces before capital letters */}
            </option>
          ))}
        </Select>
      </SelectWrapper>

      <ExerciseInfo>
        <Title>Exercise Form Guidelines</Title>
        <List>
          {exerciseConfig.formChecks.map((check, index) => (
            <ListItem key={index}>
              <strong>{check.name}:</strong> {check.description}
            </ListItem>
          ))}
        </List>
      </ExerciseInfo>
    </Container>
  );
}; 