import React from 'react';
import styled from 'styled-components';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

interface FeedbackItem {
  message: string;
  severity: 'low' | 'medium' | 'high';
  type: 'form' | 'alignment' | 'range' | 'tempo' | 'safety';
  suggestion: string;
}

interface AnalysisResultsProps {
  score: number;
  feedback: FeedbackItem[];
  videoUrl: string;
}

const Container = styled.div`
  width: 100%;
  max-width: 800px;
  margin: 20px auto;
  padding: 20px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.color.background)};
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const ScoreSection = styled.div`
  text-align: center;
  margin-bottom: 24px;
`;

const Score = styled.div<{ score: number }>`
  font-size: 48px;
  font-weight: bold;
  color: ${({ score }) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 70) return '#FFC107';
    return '#F44336';
  }};
  margin-bottom: 8px;
`;

const ScoreLabel = styled.div`
  font-size: 16px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  opacity: 0.8;
`;

const FeedbackSection = styled.div`
  margin-top: 24px;
`;

const FeedbackTitle = styled.h3`
  font-size: 20px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  margin-bottom: 16px;
`;

const FeedbackCard = styled.div<{ severity: 'low' | 'medium' | 'high' }>`
  background-color: ${({ theme, severity }) => {
    const colors = {
      low: getThemeValue(theme, 'colors.success', '#4CAF50'),
      medium: getThemeValue(theme, 'colors.warning', '#FFC107'),
      high: getThemeValue(theme, 'colors.error', '#F44336')
    };
    return `${colors[severity]}10`;
  }};
  border-left: 4px solid ${({ theme, severity }) => {
    const colors = {
      low: getThemeValue(theme, 'colors.success', '#4CAF50'),
      medium: getThemeValue(theme, 'colors.warning', '#FFC107'),
      high: getThemeValue(theme, 'colors.error', '#F44336')
    };
    return colors[severity];
  }};
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 8px;
`;

const FeedbackMessage = styled.div`
  font-size: 16px;
  font-weight: 500;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  margin-bottom: 8px;
`;

const FeedbackSuggestion = styled.div`
  font-size: 14px;
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  opacity: 0.8;
`;

const FeedbackType = styled.span<{ type: 'form' | 'alignment' | 'range' | 'tempo' | 'safety' }>`
  display: inline-block;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  margin-right: 8px;
  background-color: ${({ type }) => {
    const colors: Record<'form' | 'alignment' | 'range' | 'tempo' | 'safety', string> = {
      form: '#E3F2FD',
      alignment: '#F3E5F5',
      range: '#E8F5E9',
      tempo: '#FFF3E0',
      safety: '#FFEBEE'
    };
    return colors[type];
  }};
  color: ${({ type }) => {
    const colors: Record<'form' | 'alignment' | 'range' | 'tempo' | 'safety', string> = {
      form: '#1976D2',
      alignment: '#7B1FA2',
      range: '#388E3C',
      tempo: '#F57C00',
      safety: '#D32F2F'
    };
    return colors[type];
  }};
`;

const VideoPreview = styled.video`
  width: 100%;
  max-width: 600px;
  margin: 20px auto;
  display: block;
  border-radius: 8px;
`;

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  score,
  feedback,
  videoUrl
}) => {
  return (
    <Container>
      <ScoreSection>
        <Score score={score}>{Math.round(score)}%</Score>
        <ScoreLabel>Form Score</ScoreLabel>
      </ScoreSection>

      <VideoPreview src={videoUrl} controls />

      <FeedbackSection>
        <FeedbackTitle>Form Analysis</FeedbackTitle>
        {feedback.map((item, index) => (
          <FeedbackCard key={index} severity={item.severity}>
            <FeedbackType type={item.type}>
              {item.type.charAt(0).toUpperCase() + item.type.slice(1)}
            </FeedbackType>
            <FeedbackMessage>{item.message}</FeedbackMessage>
            <FeedbackSuggestion>{item.suggestion}</FeedbackSuggestion>
          </FeedbackCard>
        ))}
      </FeedbackSection>
    </Container>
  );
}; 