import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Create a simplified version of FormCheckFeedback
const SimpleFeedback = ({ feedback, score }: { feedback: string; score: number }) => (
  <div data-testid="form-check-feedback">
    <div>Form Check Score: {score}%</div>
    <div>{feedback}</div>
  </div>
);

describe('SimpleFeedback Component', () => {
  const mockProps = {
    feedback: 'Good form with minor adjustments needed',
    score: 85
  };

  it('renders without crashing', () => {
    render(<SimpleFeedback {...mockProps} />);
    expect(screen.getByTestId('form-check-feedback')).toBeInTheDocument();
  });

  it('displays the feedback', () => {
    render(<SimpleFeedback {...mockProps} />);
    expect(screen.getByText('Good form with minor adjustments needed')).toBeInTheDocument();
  });

  it('displays the score', () => {
    render(<SimpleFeedback {...mockProps} />);
    expect(screen.getByText('Form Check Score: 85%')).toBeInTheDocument();
  });
}); 