import React from 'react';
import { FormTip } from '../FormTipsOverlay';

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
  return (
    <div data-testid="form-tips-overlay">
      <div className="score" data-testid="form-score">
        Score: {score}
      </div>
      {tips.map((tip) => (
        <div 
          key={tip.id} 
          className={`tip ${tip.type}`}
          onClick={() => onTipClick?.(tip)}
          data-testid={`tip-${tip.id}`}
        >
          {tip.message}
        </div>
      ))}
    </div>
  );
}; 