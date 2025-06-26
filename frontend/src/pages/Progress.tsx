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
  AreaChart,
  Area,
} from 'recharts';
import { Theme } from '../types/theme';
import { getThemeValue, fallbacks } from '../utils/themeUtils';
import { ProgressDashboard } from '../components/progress/ProgressDashboard';
import { progressService, ProgressData } from '../services/progressService';
import { FormCheckService } from '../services/formCheckService';
import { FormCheck } from '../types/formCheck';
import { MLScoreCard } from '../components/molecules/MLScoreCard';
import { MLScores } from '../types/ml';

const PageContainer = styled.div<{ theme?: Partial<Theme> }>`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  min-height: 100vh;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.main', fallbacks.color.background)};
`;

const Title = styled.h1<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.color.text)};
  margin-bottom: 24px;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.xl', fallbacks.fontSize.xl)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', '700')};
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
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.secondary.light', fallbacks.color.secondary)};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.main', fallbacks.color.white)};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.color.text)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', fallbacks.fontSize.md)};
  flex: 1;
`;

const HistoryContainer = styled.div`
  width: 100%;
  max-width: 800px;
  margin-top: 32px;
`;

const HistoryTitle = styled.h2<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.color.text)};
  margin-bottom: 16px;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.lg', fallbacks.fontSize.lg)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', '700')};
`;

const HistoryList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

const HistoryItem = styled.div<{ theme?: Partial<Theme> }>`
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background.main', fallbacks.color.white)};
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
  color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', fallbacks.color.primary)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
`;

const Score = styled.span<{ theme?: Partial<Theme>; riskLevel: string }>`
  color: ${({ theme, riskLevel }) => 
    riskLevel === 'low' 
      ? getThemeValue(theme, 'colors.success.main', fallbacks.color.success)
      : riskLevel === 'high'
      ? getThemeValue(theme, 'colors.error.main', fallbacks.color.error)
      : getThemeValue(theme, 'colors.warning.main', fallbacks.color.warning)
  };
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', '700')};
`;

const DateText = styled.span<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.color.text)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.sm', fallbacks.fontSize.sm)};
`;

const FeedbackList = styled.ul`
  margin: 8px 0 0 0;
  padding-left: 20px;
`;

const FeedbackItem = styled.li<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.color.text)};
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.md', fallbacks.fontSize.md)};
  margin-bottom: 4px;
`;

const LoadingSpinner = styled.div<{ theme?: Partial<Theme> }>`
  display: flex;
  align-items: center;
  justify-content: center;
  color: ${({ theme }) => getThemeValue(theme, 'colors.primary.main', fallbacks.color.primary)};
  padding: 24px;
`;

const ErrorMessage = styled.div<{ theme?: Partial<Theme> }>`
  color: ${({ theme }) => getThemeValue(theme, 'colors.error.main', fallbacks.color.error)};
  background-color: ${({ theme }) => `${getThemeValue(theme, 'colors.error.light', fallbacks.color.error)}20`};
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
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.color.text)};
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: ${({ theme }) => theme.spacing.lg};
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const SessionCard = styled(motion.div)`
  background: ${({ theme }) => getThemeValue(theme, 'colors.background.main', fallbacks.color.white)};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  padding: ${({ theme }) => theme.spacing.lg};
  box-shadow: ${({ theme }) => theme.shadows.medium};
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
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.primary', fallbacks.color.text)};
  margin-bottom: ${({ theme }) => theme.spacing.sm};
`;

const SessionDate = styled.p`
  font-size: ${({ theme }) => theme.typography.fontSize.sm};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text.secondary', fallbacks.color.text)};
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
  background: ${({ theme }) => getThemeValue(theme, 'colors.background.main', fallbacks.color.white)};
  border-radius: ${({ theme }) => theme.borderRadius.lg};
  padding: ${({ theme }) => theme.spacing.lg};
  box-shadow: ${({ theme }) => theme.shadows.medium};
  height: 400px;
  margin-top: ${({ theme }) => theme.spacing.xl};
`;

const ChartTitle = styled.h2`
  color: #333;
  margin-bottom: 20px;
`;

// Enhanced data interfaces for real backend data
interface ProgressChartData {
  date: string;
  overall_score: number;
  posture_score?: number;
  stability_score?: number;
  depth_score?: number;
}

interface SessionData {
  id: number;
  title: string;
  date: string;
  score: number;
  thumbnail: string;
  ml_scores?: MLScores;
  exercise_type: string;
}

export const Progress: React.FC = () => {
  const [exerciseType, setExerciseType] = useState<string>('all');
  const [history, setHistory] = useState<ProgressData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [progressData, setProgressData] = useState<ProgressChartData[]>([]);
  const [formChecks, setFormChecks] = useState<FormCheck[]>([]);
  const [averageMLScores, setAverageMLScores] = useState<MLScores | null>(null);
  
  const formCheckService = FormCheckService.getInstance();

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
      
      // Load form checks from backend
      const formCheckData = exerciseType !== 'all' 
        ? await formCheckService.getFormChecksByExerciseType(exerciseType as any)
        : await formCheckService.getFormChecks();
      
      setFormChecks(formCheckData);
      
      // Convert form checks to sessions data
      const sessionsData: SessionData[] = formCheckData.map((fc, index) => ({
        id: fc.id,
        title: `${fc.exercise_type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')} Session`,
        date: fc.created_at,
        score: fc.score || 0,
        thumbnail: fc.thumbnail_url || 'https://via.placeholder.com/300x200',
        ml_scores: fc.posture_score && fc.stability_score && fc.depth_score ? {
          posture_score: fc.posture_score,
          stability_score: fc.stability_score,
          depth_score: fc.depth_score,
          confidence: fc.confidence_score
        } : undefined,
        exercise_type: fc.exercise_type
      }));
      setSessions(sessionsData);

      // Convert to progress chart data
      const chartData: ProgressChartData[] = formCheckData
        .filter(fc => fc.score !== null && fc.score !== undefined)
        .map(fc => ({
          date: new Date(fc.created_at).toLocaleDateString(),
          overall_score: fc.score || 0,
          posture_score: fc.posture_score || undefined,
          stability_score: fc.stability_score || undefined,
          depth_score: fc.depth_score || undefined,
        }))
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
      setProgressData(chartData);

      // Calculate average ML scores
      const mlScoresData = formCheckData.filter(fc => 
        fc.posture_score && fc.stability_score && fc.depth_score
      );
      
      if (mlScoresData.length > 0) {
        const avgScores: MLScores = {
          posture_score: mlScoresData.reduce((sum, fc) => sum + (fc.posture_score || 0), 0) / mlScoresData.length,
          stability_score: mlScoresData.reduce((sum, fc) => sum + (fc.stability_score || 0), 0) / mlScoresData.length,
          depth_score: mlScoresData.reduce((sum, fc) => sum + (fc.depth_score || 0), 0) / mlScoresData.length,
          confidence: mlScoresData.reduce((sum, fc) => sum + (fc.confidence_score || 0), 0) / mlScoresData.length,
        };
        setAverageMLScores(avgScores);
      }
      
      // Load legacy progress history for backward compatibility
      const filter = exerciseType !== 'all' ? { exerciseType } : undefined;
      const historyData = await progressService.getProgressHistory(filter);
      setHistory(historyData);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load progress data');
      console.error('Progress loading error:', err);
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
        <Description>Track your form improvement over time with AI-powered analysis</Description>
      </Header>

      {/* ML Scores Overview */}
      {averageMLScores && (
        <div style={{ marginBottom: '32px', width: '100%', maxWidth: '800px' }}>
          <MLScoreCard 
            scores={averageMLScores}
            variant="summary"
            showTrend={false}
            showConfidence={true}
          />
        </div>
      )}

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
            
            {/* Display ML scores if available */}
            {session.ml_scores && (
              <div style={{ marginTop: '12px' }}>
                <MLScoreCard 
                  scores={session.ml_scores}
                  variant="compact"
                  showTrend={false}
                  showConfidence={false}
                />
              </div>
            )}
          </SessionCard>
        ))}
      </Grid>

      <ChartContainer>
        <ChartTitle>Form Score Progress</ChartTitle>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={progressData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis domain={[0, 100]} />
            <Tooltip 
              formatter={(value, name) => [
                `${value}%`,
                name === 'overall_score' ? 'Overall Score' :
                name === 'posture_score' ? 'Posture Score' :
                name === 'stability_score' ? 'Stability Score' :
                name === 'depth_score' ? 'Depth Score' : name
              ]}
            />
            <Area
              type="monotone"
              dataKey="overall_score"
              stroke="#4CAF50"
              fill="#4CAF5020"
              strokeWidth={3}
            />
            {progressData.some(d => d.posture_score) && (
              <Area
                type="monotone"
                dataKey="posture_score"
                stroke="#2196F3"
                fill="#2196F320"
                strokeWidth={2}
              />
            )}
            {progressData.some(d => d.stability_score) && (
              <Area
                type="monotone"
                dataKey="stability_score"
                stroke="#FF9500"
                fill="#FF950020"
                strokeWidth={2}
              />
            )}
            {progressData.some(d => d.depth_score) && (
              <Area
                type="monotone"
                dataKey="depth_score"
                stroke="#9C27B0"
                fill="#9C27B020"
                strokeWidth={2}
              />
            )}
          </AreaChart>
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
          <LoadingSpinner>Loading progress data...</LoadingSpinner>
        ) : error ? (
          <ErrorMessage>{error}</ErrorMessage>
        ) : sessions.length === 0 && history.length === 0 ? (
          <ErrorMessage>
            No exercise sessions yet. Start your first form check to see your progress!
          </ErrorMessage>
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