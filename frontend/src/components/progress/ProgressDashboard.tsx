import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { motion } from 'framer-motion';
import { Theme } from '../../theme';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';
import { progressService, ProgressStats, ProgressData } from '../../services/progressService';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const Container = styled.div`
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
`;

const Header = styled.div`
  margin-bottom: 32px;
`;

const Title = styled.h1`
  font-size: 28px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.colors.text)};
  margin-bottom: 8px;
`;

const Subtitle = styled.p`
  font-size: 16px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
`;

const StatCard = styled(motion.div)`
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  padding: 24px;
  border-radius: 12px;
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
`;

const StatTitle = styled.h3`
  font-size: 14px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
  margin-bottom: 8px;
`;

const StatValue = styled.div<{ trend?: 'up' | 'down' | 'neutral' }>`
  font-size: 24px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  color: ${({ theme, trend }) => {
    switch (trend) {
      case 'up':
        return getThemeValue(theme, 'colors.success', fallbacks.colors.success);
      case 'down':
        return getThemeValue(theme, 'colors.error', fallbacks.colors.error);
      default:
        return getThemeValue(theme, 'colors.text', fallbacks.colors.text);
    }
  }};
`;

const ChartContainer = styled.div`
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  padding: 24px;
  border-radius: 12px;
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
  margin-bottom: 32px;
  height: 400px;
`;

const SessionsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
`;

const SessionCard = styled(motion.div)`
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
  border-radius: 12px;
  overflow: hidden;
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
`;

const SessionThumbnail = styled.div<{ src: string }>`
  height: 200px;
  background-image: url(${props => props.src});
  background-size: cover;
  background-position: center;
`;

const SessionInfo = styled.div`
  padding: 16px;
`;

const SessionTitle = styled.h3`
  font-size: 16px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
  margin-bottom: 8px;
`;

const SessionMeta = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.textSecondary', fallbacks.colors.textSecondary)};
`;

const SessionScore = styled.div<{ score: number }>`
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  color: ${({ score }) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 70) return '#FFC107';
    return '#F44336';
  }};
`;

// Mock data - replace with real data from your backend
const mockSessions = [
  {
    id: 1,
    date: '2024-03-15',
    exerciseType: 'Squat',
    score: 85,
    thumbnail: 'https://example.com/thumbnail1.jpg',
  },
  {
    id: 2,
    date: '2024-03-14',
    exerciseType: 'Deadlift',
    score: 92,
    thumbnail: 'https://example.com/thumbnail2.jpg',
  },
  // Add more mock sessions...
];

const mockChartData = [
  { date: '2024-03-10', score: 75 },
  { date: '2024-03-11', score: 82 },
  { date: '2024-03-12', score: 78 },
  { date: '2024-03-13', score: 85 },
  { date: '2024-03-14', score: 88 },
  { date: '2024-03-15', score: 92 },
];

export const ProgressDashboard: React.FC = () => {
  const [sessions, setSessions] = useState(mockSessions);
  const [chartData, setChartData] = useState(mockChartData);

  // Calculate stats
  const averageScore = Math.round(
    sessions.reduce((acc, session) => acc + session.score, 0) / sessions.length
  );
  const totalSessions = sessions.length;
  const improvement = chartData.length > 1
    ? chartData[chartData.length - 1].score - chartData[0].score
    : 0;

  return (
    <Container>
      <Header>
        <Title>Your Progress</Title>
        <Subtitle>Track your improvement and form consistency</Subtitle>
      </Header>

      <StatsGrid>
        <StatCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <StatTitle>Average Form Score</StatTitle>
          <StatValue>{averageScore}</StatValue>
        </StatCard>

        <StatCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <StatTitle>Total Sessions</StatTitle>
          <StatValue>{totalSessions}</StatValue>
        </StatCard>

        <StatCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <StatTitle>Overall Improvement</StatTitle>
          <StatValue trend={improvement > 0 ? 'up' : improvement < 0 ? 'down' : 'neutral'}>
            {improvement > 0 ? '+' : ''}{improvement}%
          </StatValue>
        </StatCard>
      </StatsGrid>

      <ChartContainer>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="score"
              stroke={getThemeValue({ colors: { primary: '#4D7CFE' } }, 'colors.primary', fallbacks.colors.primary)}
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartContainer>

      <SessionsGrid>
        {sessions.map((session, index) => (
          <SessionCard
            key={session.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
          >
            <SessionThumbnail src={session.thumbnail} />
            <SessionInfo>
              <SessionTitle>{session.exerciseType}</SessionTitle>
              <SessionMeta>
                <span>{new Date(session.date).toLocaleDateString()}</span>
                <SessionScore score={session.score}>{session.score}%</SessionScore>
              </SessionMeta>
            </SessionInfo>
          </SessionCard>
        ))}
      </SessionsGrid>
    </Container>
  );
}; 