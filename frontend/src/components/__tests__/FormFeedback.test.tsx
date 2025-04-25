import React from 'react';
import { testRender } from '../../test-utils';
import { FormFeedback } from '../FormFeedback';
import { FormValidationResult } from '../../services/poseAnalysis/types';

describe('FormFeedback', () => {
  const mockProps = {
    feedback: [
      { isValid: true, message: 'Good form' },
      { isValid: false, message: 'Keep knees aligned' }
    ] as FormValidationResult[],
    confidence: 0.85,
    repetitionCount: 5,
    phase: 'middle' as const
  };

  it('renders without crashing', () => {
    const { getByTestId } = testRender(<FormFeedback {...mockProps} />);
    expect(getByTestId('form-feedback')).toBeInTheDocument();
  });

  it('matches snapshot', () => {
    const { asFragment } = testRender(<FormFeedback {...mockProps} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('displays feedback messages with correct styling', () => {
    const { getByText } = testRender(<FormFeedback {...mockProps} />);
    const goodFormMessage = getByText('Good form');
    const kneeMessage = getByText('Keep knees aligned');
    
    expect(goodFormMessage).toBeInTheDocument();
    expect(kneeMessage).toBeInTheDocument();
    expect(goodFormMessage.parentElement).toHaveStyle({ color: expect.any(String) });
    expect(kneeMessage.parentElement).toHaveStyle({ color: expect.any(String) });
  });

  it('displays confidence percentage', () => {
    const { getByText } = testRender(<FormFeedback {...mockProps} />);
    expect(getByText('85%')).toBeInTheDocument();
  });

  it('displays repetition count', () => {
    const { getByText } = testRender(<FormFeedback {...mockProps} />);
    expect(getByText('5')).toBeInTheDocument();
  });

  it('displays current phase with capitalized first letter', () => {
    const { getByText } = testRender(<FormFeedback {...mockProps} />);
    expect(getByText('Middle')).toBeInTheDocument();
  });

  it('handles empty feedback array', () => {
    const propsWithNoFeedback = {
      ...mockProps,
      feedback: []
    };
    const { getByTestId } = testRender(<FormFeedback {...propsWithNoFeedback} />);
    expect(getByTestId('form-feedback')).toBeInTheDocument();
  });
}); 