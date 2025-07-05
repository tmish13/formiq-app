import React, { Suspense } from 'react';
import { useRoutes } from 'react-router-dom';
import { appRoutes } from './routes';
import { LoadingSpinner } from '../components/atoms/LoadingSpinner';
import ErrorBoundary from '../components/common/ErrorBoundary';

export const AppRoutes: React.FC = () => {
  const element = useRoutes(appRoutes);

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        {element}
      </Suspense>
    </ErrorBoundary>
  );
}; 