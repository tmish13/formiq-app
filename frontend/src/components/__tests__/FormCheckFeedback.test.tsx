import React from 'react';
import { testRender } from '../../test-utils';
import FormCheckFeedback from '../FormCheckFeedback';

describe('FormCheckFeedback', () => {
  const mockProps = {
    feedback: 'Good form with minor adjustments needed',
    score: 85
  };

  it('renders without crashing', () => {
    const { getByTestId } = testRender(<FormCheckFeedback {...mockProps} />);
    expect(getByTestId('form-check-feedback')).toBeInTheDocument();
  });

  it('matches snapshot', () => {
    const { asFragment } = testRender(<FormCheckFeedback {...mockProps} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('displays the feedback', () => {
    const { getByText } = testRender(<FormCheckFeedback {...mockProps} />);
    expect(getByText('Good form with minor adjustments needed')).toBeInTheDocument();
  });

  it('displays the score', () => {
    const { getByText } = testRender(<FormCheckFeedback {...mockProps} />);
    expect(getByText('Form Check Score: 85%')).toBeInTheDocument();
  });
}); 