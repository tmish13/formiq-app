import React from 'react';
import ErrorPage from './ErrorPage';

const NotFoundPage: React.FC = () => {
  return (
    <ErrorPage
      code={404}
      title="Page Not Found"
      message="The page you're looking for doesn't exist or has been moved."
      showRetryButton={false}
    />
  );
};

export default NotFoundPage; 