import React from 'react';
import styled from 'styled-components';
import { Theme } from '../../theme';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

const ResultsContainer = styled.div<{ theme?: Partial<Theme> }>`
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: 24px;
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.colors.background)};
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const ScoreContainer = styled.div<{ theme?: Partial<Theme> }>`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
`;

const ScoreCircle = styled.div<{ score: number; theme?: Partial<Theme> }>`
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: ${({ theme }) => getThemeValue(theme, 'typography.fontSize.xlarge', fallbacks.typography.fontSize.xlarge)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.bold', fallbacks.typography.fontWeight.bold)};
  background: ${({ score, theme }) => {
    if (score >= 0.8) return getThemeValue(theme, 'colors.success', fallbacks.colors.success);
    if (score >= 0.6) return getThemeValue(theme, 'colors.warning', fallbacks.colors.warning);
    return getThemeValue(theme, 'colors.error', fallbacks.colors.error);
  }};
  color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.colors.white)};
`;

const FeedbackList = styled.ul<{ theme?: Partial<Theme> }>`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const FeedbackItem = styled.li<{ severity: 'low' | 'medium' | 'high'; theme?: Partial<Theme> }>`
  padding: 12px 16px;
  margin-bottom: 8px;
  border-radius: 8px;
  background-color: ${({ severity, theme }) => {
    switch (severity) {
      case 'low':
        return getThemeValue(theme, 'colors.successLight', fallbacks.colors.successLight);
      case 'medium':
        return getThemeValue(theme, 'colors.warningLight', fallbacks.colors.warningLight);
      case 'high':
        return getThemeValue(theme, 'colors.errorLight', fallbacks.colors.errorLight);
    }
  }};
  color: ${({ severity, theme }) => {
    switch (severity) {
      case 'low':
        return getThemeValue(theme, 'colors.success', fallbacks.colors.success);
      case 'medium':
        return getThemeValue(theme, 'colors.warning', fallbacks.colors.warning);
      case 'high':
        return getThemeValue(theme, 'colors.error', fallbacks.colors.error);
    }
  }};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', fallbacks.typography.fontWeight.medium)};
`;

const RiskLevel = styled.div<{ level: 'low' | 'medium' | 'high'; theme?: Partial<Theme> }>`
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', fallbacks.typography.fontWeight.medium)};
  background-color: ${({ level, theme }) => {
    switch (level) {
      case 'low':
        return getThemeValue(theme, 'colors.successLight', fallbacks.colors.successLight);
      case 'medium':
        return getThemeValue(theme, 'colors.warningLight', fallbacks.colors.warningLight);
      case 'high':
        return getThemeValue(theme, 'colors.errorLight', fallbacks.colors.errorLight);
    }
  }};
  color: ${({ level, theme }) => {
    switch (level) {
      case 'low':
        return getThemeValue(theme, 'colors.success', fallbacks.colors.success);
      case 'medium':
        return getThemeValue(theme, 'colors.warning', fallbacks.colors.warning);
      case 'high':
        return getThemeValue(theme, 'colors.error', fallbacks.colors.error);
    }
  }};
  text-align: center;
  margin-top: 16px;
`;

interface FormAnalysisResultsProps {
  score: number;
  feedback: string[];
  riskLevel: 'low' | 'medium' | 'high';
}

export const FormAnalysisResults: React.FC<FormAnalysisResultsProps> = ({
  score,
  feedback,
  riskLevel
}) => {
  const scorePercentage = Math.round(score * 100);

  return (
    <ResultsContainer>
      <ScoreContainer>
        <ScoreCircle score={score}>
          {scorePercentage}%
        </ScoreCircle>
      </ScoreContainer>

      <FeedbackList>
        {feedback.map((item, index) => (
          <FeedbackItem key={index} severity={riskLevel}>
            {item}
          </FeedbackItem>
        ))}
      </FeedbackList>

      <RiskLevel level={riskLevel}>
        {riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)} Risk Level
      </RiskLevel>
    </ResultsContainer>
  );
}; 