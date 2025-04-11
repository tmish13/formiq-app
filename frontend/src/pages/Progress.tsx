import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Theme } from '../theme';
import { getThemeValue, fallbacks } from '../utils/themeUtils';
import { ProgressDashboard } from '../components/progress/ProgressDashboard';
import { progressService, ProgressData } from '../services/progressService';

const PageContainer = styled.div<{ theme?: Partial<Theme> }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  min-height: 100vh;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
`;

const Title = styled.h1<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  margin-bottom: 24px;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.xlarge', fallbacks.typography.fontSize.xlarge)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', fallbacks.typography.fontWeight.bold)};
`;

const FilterContainer = styled.div`
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  width: 100%;
  max-width: 600px;
`;

const Select = styled.select<{ theme?: Partial<Theme> }>`
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.secondaryLight', fallbacks.colors.secondaryLight)};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.medium', fallbacks.typography.fontSize.medium)};
  flex: 1;
`;

const HistoryContainer = styled.div`
  width: 100%;
  max-width: 800px;
  margin-top: 32px;
`;

const HistoryTitle = styled.h2<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  margin-bottom: 16px;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.large', fallbacks.typography.fontSize.large)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', fallbacks.typography.fontWeight.bold)};
`;

const HistoryList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const HistoryItem = styled.div<{ theme?: Partial<Theme> }>`
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1);
`;

const HistoryItemHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
`;

const ExerciseType = styled.span<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', fallbacks.typography.fontWeight.medium)};
`;

const Score = styled.span<{ theme?: Partial<Theme>; riskLevel: string }>`
  color: ${({ theme, riskLevel }) => 
    riskLevel === 'low' 
      ? getThemeValue(theme, 'colors.success', fallbacks.colors.success)
      : riskLevel === 'high'
      ? getThemeValue(theme, 'colors.error', fallbacks.colors.error)
      : getThemeValue(theme, 'colors.warning', fallbacks.colors.warning)
  };
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', fallbacks.typography.fontWeight.bold)};
`;

const DateText = styled.span<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.textLight', fallbacks.colors.textLight)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.small', fallbacks.typography.fontSize.small)};
`;

const FeedbackList = styled.ul`
  margin: 8px 0 0 0;
  padding-left: 20px;
`;

const FeedbackItem = styled.li<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.medium', fallbacks.typography.fontSize.medium)};
  margin-bottom: 4px;
`;

const LoadingSpinner = styled.div<{ theme?: Partial<Theme> }>`
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${({ theme }) => getThemeValue(theme, 'colors.primary', fallbacks.colors.primary)};
  padding: 24px;
`;

const ErrorMessage = styled.div<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.error', fallbacks.colors.error)};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.errorLight', fallbacks.colors.errorLight)};
  padding: 16px;
  border-radius: 8px;
  margin: 16px 0;
  width: 100%;
  max-width: 600px;
  text-align: center;
`;

const Container = styled.div`
  padding: ${({ theme }) => theme.spacing.xl};
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const Description = styled.p`
  font-size: ${({ theme }) => theme.typography.fontSize.md};
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: ${({ theme }) => theme.spacing.lg};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const SessionCard = styled(motion.div)`
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  padding: ${({ theme }) => theme.spacing.lg};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
`;

const SessionImage = styled.img`
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: ${({ theme }) => theme.borderRadius.md};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const SessionTitle = styled.h3`
  font-size: ${({ theme }) => theme.typography.fontSize.lg};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  margin-bottom: ${({ theme }) => theme.spacing.sm};
`;

const SessionDate = styled.p`
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const ScoreBadge = styled.div<{ score: number }>`
  display: inline-block;
  padding: ${({ theme }) => `${theme.spacing.xs} ${theme.spacing.md}`};
  border-radius: ${({ theme }) => theme.borderRadius.sm};
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
  background: ${({ score }) => {
    if (score >= 90) return '#E5FFE9';
    if (score >= 70) return '#FFF4E5';
    return '#FFE5E5';
  }};
  color: ${({ score }) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 70) return '#FF9500';
    return '#FF3B30';
  }};
`;

const ChartContainer = styled.div`
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  padding: ${({ theme }) => theme.spacing.lg};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
  height: 400px;
  margin-top: ${({ theme }) => theme.spacing.xl};
`;

const ChartTitle = styled.h2`
  color: #333;
  margin-bottom: 20px;
`;

// Mock data for sessions
const mockSessions = [
  {
    id: 1,
    title: 'Morning Squat Session',
    date: '2024-03-15',
    score: 85,
    thumbnail: 'https://via.placeholder.com/300x200',
  },
  {
    id: 2,
    title: 'Evening Push-up Routine',
    date: '2024-03-14',
    score: 75,
    thumbnail: 'https://via.placeholder.com/300x200',
  },
  {
    id: 3,
    title: 'Deadlift Practice',
    date: '2024-03-13',
    score: 92,
    thumbnail: 'https://via.placeholder.com/300x200',
  },
  {
    id: 4,
    title: 'Lunge Training',
    date: '2024-03-12',
    score: 68,
    thumbnail: 'https://via.placeholder.com/300x200',
  },
];

// Mock data for progress chart
const mockProgressData = [
  { date: '2024-03-01', score: 65 },
  { date: '2024-03-05', score: 70 },
  { date: '2024-03-08', score: 75 },
  { date: '2024-03-12', score: 68 },
  { date: '2024-03-13', score: 92 },
  { date: '2024-03-14', score: 75 },
  { date: '2024-03-15', score: 85 },
];

export const Progress: React.FC = () => {
  const [exerciseType, setExerciseType] = useState<string>('all');
  const [history, setHistory] = useState<ProgressData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessions] = useState(mockSessions);
  const [progressData] = useState(mockProgressData);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
      },
    },
  };

  const loadHistory = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const filter = exerciseType !== 'all' ? { exerciseType } : undefined;
      const data = await progressService.getProgressHistory(filter);
      setHistory(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [exerciseType]);

  const formatDate = (dateString: string): string => {
    const timestamp = Date.parse(dateString);
    if (isNaN(timestamp)) {
      return 'Invalid date';
    }
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <PageContainer>
      <Header>
        <Title>Your Progress</Title>
        <Description>Track your form improvement over time</Description>
      </Header>

      <Grid
        as={motion.div}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {sessions.map((session, index) => (
          <SessionCard
            key={session.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <SessionImage src={session.thumbnail} alt={session.title} />
            <SessionTitle>{session.title}</SessionTitle>
            <SessionDate>{new Date(session.date).toLocaleDateString()}</SessionDate>
            <ScoreBadge score={session.score}>{session.score}%</ScoreBadge>
          </SessionCard>
        ))}
      </Grid>

      <ChartContainer>
        <ChartTitle>Form Score Progress</ChartTitle>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={progressData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#4CAF50"
              strokeWidth={2}
              dot={{ fill: '#4CAF50' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>

      <HistoryContainer>
        <HistoryTitle>Analysis History</HistoryTitle>
        
        <FilterContainer>
          <Select
            value={exerciseType}
            onChange={(e) => setExerciseType(e.target.value)}
          >
            <option value="all">All Exercises</option>
            <option value="squat">Squat</option>
            <option value="deadlift">Deadlift</option>
            <option value="bench_press">Bench Press</option>
            <option value="shoulder_press">Shoulder Press</option>
            <option value="pull_up">Pull Up</option>
          </Select>
        </FilterContainer>

        {isLoading ? (
          <LoadingSpinner>Loading history...</LoadingSpinner>
        ) : error ? (
          <ErrorMessage>{error}</ErrorMessage>
        ) : history.length === 0 ? (
          <ErrorMessage>No history available</ErrorMessage>
        ) : (
          <HistoryList>
            {history.map((item) => (
              <HistoryItem key={item.id}>
                <HistoryItemHeader>
                  <ExerciseType>
                    {item.exerciseType.split('_').map(word => 
                      word.charAt(0).toUpperCase() + word.slice(1)
                    ).join(' ')}
                  </ExerciseType>
                  <Score riskLevel={item.riskLevel}>
                    {item.score.toFixed(1)}%
                  </Score>
                </HistoryItemHeader>
                <DateText>{formatDate(item.createdAt)}</DateText>
                <FeedbackList>
                  {item.feedback.map((feedback, index) => (
                    <FeedbackItem key={index}>{feedback}</FeedbackItem>
                  ))}
                </FeedbackList>
              </HistoryItem>
            ))}
          </HistoryList>
        )}
      </HistoryContainer>
    </PageContainer>
  );
}; 