import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { motion, AnimatePresence } from 'framer-motion';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

const OverlayContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 10;
`;

const ProgressRing = styled(motion.div)`
  position: absolute;
  top: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
`;

const ProgressCircle = styled(motion.circle)<{ score: number }>`
  transform-origin: center;
  transform: rotate(-90deg);
  stroke: ${({ score }) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 70) return '#FFC107';
    return '#F44336';
  }};
`;

const TipCard = styled(motion.div)<{ type: 'warning' | 'error' | 'success' }>`
  position: absolute;
  background: ${({ theme, type }) => {
    switch (type) {
      case 'warning':
        return getThemeValue(theme, 'colors.warningLight', fallbacks.color.warningLight);
      case 'error':
        return getThemeValue(theme, 'colors.errorLight', fallbacks.color.errorLight);
      case 'success':
        return getThemeValue(theme, 'colors.successLight', fallbacks.color.successLight);
      default:
        return getThemeValue(theme, 'colors.background', fallbacks.color.background);
    }
  }};
  color: ${({ theme, type }) => {
    switch (type) {
      case 'warning':
        return getThemeValue(theme, 'colors.warning', fallbacks.color.warning);
      case 'error':
        return getThemeValue(theme, 'colors.error', fallbacks.color.error);
      case 'success':
        return getThemeValue(theme, 'colors.success', fallbacks.color.success);
      default:
        return getThemeValue(theme, 'colors.text', fallbacks.color.text);
    }
  }};
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.medium || 500};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
  max-width: 200px;
  text-align: center;
  backdrop-filter: blur(8px);
  border: 1px solid ${({ theme, type }) => {
    switch (type) {
      case 'warning':
        return getThemeValue(theme, 'colors.warning', fallbacks.color.warning);
      case 'error':
        return getThemeValue(theme, 'colors.error', fallbacks.color.error);
      case 'success':
        return getThemeValue(theme, 'colors.success', fallbacks.color.success);
      default:
        return 'transparent';
    }
  }};
`;

const ScoreMeter = styled(motion.div)`
  position: absolute;
  top: 20px;
  right: 20px;
  background: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 16px;
  font-weight: ${({ theme }) => theme?.typography?.fontWeight?.bold || 700};
  color: ${({ theme }) => getThemeValue(theme, 'colors.text', fallbacks.color.text)};
  box-shadow: ${({ theme }) => getThemeValue(theme, 'shadows.md', fallbacks.shadows.md)};
  display: flex;
  align-items: center;
  gap: 8px;
`;

const ScoreValue = styled.span<{ score: number }>`
  color: ${({ score }) => {
    if (score >= 90) return '#4CAF50';
    if (score >= 70) return '#FFC107';
    return '#F44336';
  }};
`;

export interface FormTip {
  id: string;
  message: string;
  type: 'warning' | 'error' | 'success';
  position: {
    top: string;
    left: string;
  };
  confidence?: number;
}

interface FormTipsOverlayProps {
  tips: FormTip[];
  score: number;
  onTipClick?: (tip: FormTip) => void;
}

export const FormTipsOverlay: React.FC<FormTipsOverlayProps> = ({ 
  tips, 
  score,
  onTipClick 
}) => {
  const [activeTips, setActiveTips] = useState<FormTip[]>([]);

  useEffect(() => {
    // Filter out low confidence tips and sort by importance
    const filteredTips = tips
      .filter(tip => !tip.confidence || tip.confidence > 0.7)
      .sort((a, b) => {
        const typeOrder = { error: 0, warning: 1, success: 2 };
        return typeOrder[a.type] - typeOrder[b.type];
      })
      .slice(0, 3); // Show max 3 tips at a time

    setActiveTips(filteredTips);
  }, [tips]);

  const circleRadius = 25;
  const circumference = 2 * Math.PI * circleRadius;
  const progress = (score / 100) * circumference;

  return (
    <OverlayContainer>
      <AnimatePresence>
        {activeTips.map((tip) => (
          <TipCard
            key={tip.id}
            type={tip.type}
            initial={{ opacity: 0, y: 20, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9 }}
            transition={{ duration: 0.3 }}
            style={{
              top: tip.position.top,
              left: tip.position.left,
            }}
            onClick={() => onTipClick?.(tip)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            {tip.message}
          </TipCard>
        ))}
      </AnimatePresence>

      <ProgressRing
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        <svg width="50" height="50" viewBox="0 0 50 50">
          <circle
            cx="25"
            cy="25"
            r={circleRadius}
            fill="none"
            stroke="#E0E0E0"
            strokeWidth="4"
          />
          <ProgressCircle
            cx="25"
            cy="25"
            r={circleRadius}
            fill="none"
            strokeWidth="4"
            score={score}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: progress / circumference }}
            transition={{ duration: 0.5, ease: "easeInOut" }}
          />
        </svg>
        <ScoreValue score={score}>{score}</ScoreValue>
      </ProgressRing>
    </OverlayContainer>
  );
}; 