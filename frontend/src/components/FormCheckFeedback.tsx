import React from 'react';

interface FormCheckFeedbackProps {
  overallFeedback: string;
  issues: string[];
  suggestions: string[];
}

const FormCheckFeedback: React.FC<FormCheckFeedbackProps> = ({
  overallFeedback,
  issues,
  suggestions,
}) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Overall Feedback</h3>
        <p className="text-gray-700">{overallFeedback}</p>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Issues Identified</h3>
        <ul className="list-disc list-inside space-y-1">
          {issues.map((issue, index) => (
            <li key={index} className="text-red-600">{issue}</li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Suggestions for Improvement</h3>
        <ul className="list-disc list-inside space-y-1">
          {suggestions.map((suggestion, index) => (
            <li key={index} className="text-blue-600">{suggestion}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default FormCheckFeedback; 