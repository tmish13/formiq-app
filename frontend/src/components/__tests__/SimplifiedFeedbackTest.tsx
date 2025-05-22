import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Create a simple mock component
const SimpleFeedback = ({ feedback }: { feedback: string }) => (
  <div data-testid="simple-feedback">
    {feedback}
  </div>
);

// Test suite
describe('SimpleFeedback Component', () => {
  it('renders the feedback text', () => {
    render(<SimpleFeedback feedback="Great job!" />);
    expect(screen.getByTestId('simple-feedback')).toHaveTextContent('Great job!');
  });
}); 