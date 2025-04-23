import React, { Suspense } from 'react';
import { useRoutes } from 'react-router-dom';
import { routes } from './routes';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorBoundary } from '../components/common/ErrorBoundary';

export const AppRoutes: React.FC = () => {
  const element = useRoutes(routes);

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        {element}
      </Suspense>
    </ErrorBoundary>
  );
}; 