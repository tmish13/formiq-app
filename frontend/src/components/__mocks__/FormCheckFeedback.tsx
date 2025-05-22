import React from 'react';

interface FormCheckFeedbackProps {
  feedback: string;
  score: number;
}

const FormCheckFeedback: React.FC<FormCheckFeedbackProps> = ({ feedback, score }) => {
  return (
    <div data-testid="form-check-feedback">
      <div>Form Check Score: {score}%</div>
      <div>{feedback}</div>
    </div>
  );
};

export default FormCheckFeedback; 