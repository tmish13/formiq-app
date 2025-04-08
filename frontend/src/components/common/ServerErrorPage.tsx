import React from 'react';
import ErrorPage from './ErrorPage';

interface ServerErrorPageProps {
  error?: Error;
  resetError?: () => void;
}

const ServerErrorPage: React.FC<ServerErrorPageProps> = ({ error, resetError }) => {
  const errorMessage = error?.message || 'An unexpected error occurred on our servers.';
  
  return (
    <ErrorPage
      code={500}
      title="Server Error"
      message={errorMessage}
      onRetry={resetError}
    />
  );
};

export default ServerErrorPage; 