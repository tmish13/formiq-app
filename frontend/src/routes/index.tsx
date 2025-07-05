import React, { Suspense } from 'react';
import { useRoutes } from 'react-router-dom';
import { PageLoader } from '../components/common/PageLoader';
import { appRoutes } from './routes';

// Enhanced loading component for route transitions
const RouteLoader = () => (
  <PageLoader text="Loading page..." showSkeleton={true} />
);

export const AppRoutes: React.FC = () => {
  const routing = useRoutes(appRoutes);

  return (
    <Suspense fallback={<RouteLoader />}>
      {routing}
    </Suspense>
  );
};