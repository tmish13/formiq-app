import React from 'react';
import styled from 'styled-components';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { useProgress } from '../../contexts/ProgressContext';
import { getThemeValue } from '../../utils/themeUtils';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const Container = styled.div`
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.large', '24px')};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', '#FFFFFF')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.large', '12px')};
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const Header = styled.h2`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.large', '20px')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', 700)};
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.medium', '16px')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', '#000000')};
`;

const ChartContainer = styled.div`
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.large', '24px')};
  height: 300px;
`;

const HistoryList = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => getThemeValue(theme, 'spacing.medium', '16px')};
`;

const HistoryItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.medium', '16px')};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', '#F2F2F7')};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.medium', '8px')};
`;

const ExerciseInfo = styled.div`
  flex: 1;
`;

const ExerciseName = styled.h3`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.medium', '16px')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', 500)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', '#000000')};
  margin-bottom: 4px;
`;

const ExerciseDate = styled.p`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.small', '14px')};
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', '#666666')};
`;

const Score = styled.div<{ score: number }>`
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.medium', '16px')};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', 700)};
  color: ${({ theme, score }) =>
    score >= 80
      ? getThemeValue(theme, 'colors.success', '#34C759')
      : score >= 60
      ? getThemeValue(theme, 'colors.warning', '#FF9500')
      : getThemeValue(theme, 'colors.error', '#FF3B30')};
`;

const LoadingMessage = styled.p`
  text-align: center;
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', '#666666')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.large', '24px')};
`;

const ErrorMessage = styled.p`
  text-align: center;
  color: ${({ theme }) => getThemeValue(theme, 'colors.error', '#FF3B30')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.large', '24px')};
`;

export const ProgressVisualization: React.FC = () => {
  const { history, loading, error } = useProgress();

  if (loading) {
    return <LoadingMessage>Loading progress data...</LoadingMessage>;
  }

  if (error) {
    return <ErrorMessage>{error}</ErrorMessage>;
  }

  const chartData = {
    labels: history.map(item => new Date(item.date).toLocaleDateString()),
    datasets: [
      {
        label: 'Exercise Score',
        data: history.map(item => item.score),
        borderColor: getThemeValue(undefined, 'colors.primary', '#007AFF'),
        backgroundColor: getThemeValue(undefined, 'colors.primaryLight', '#E5F1FF'),
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Exercise Progress Over Time',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
      },
    },
  };

  return (
    <Container>
      <Header>Your Progress</Header>
      <ChartContainer>
        <Line data={chartData} options={chartOptions} />
      </ChartContainer>
      <HistoryList>
        {history.map(item => (
          <HistoryItem key={item.id}>
            <ExerciseInfo>
              <ExerciseName>{item.exercise}</ExerciseName>
              <ExerciseDate>{new Date(item.date).toLocaleDateString()}</ExerciseDate>
            </ExerciseInfo>
            <Score score={item.score}>{item.score}%</Score>
          </HistoryItem>
        ))}
      </HistoryList>
    </Container>
  );
}; 