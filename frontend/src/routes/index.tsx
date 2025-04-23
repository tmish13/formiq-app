import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate, useRoutes } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Skeleton } from '../components/common/SkeletonLoader';
import styled from 'styled-components';
import { Navigation } from '../components/navigation/Navigation';
import { FormAnalysis } from '../pages/FormAnalysis';
import { Progress } from '../pages/Progress';
import Login from '../pages/auth/Login';
import { RegisterPage } from '../pages/auth/RegisterPage';
import { DashboardPage } from '../pages/dashboard/DashboardPage';
import { FormCheckUploadPage } from '../pages/workout/FormCheckUploadPage';
import { AnalysisPage } from '../pages/analysis/AnalysisPage';
import { ProfilePage } from '../pages/profile/ProfilePage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { appRoutes } from './routes';
import { PageLoader } from '../components/common/PageLoader';

// Lazy load components to improve performance
const WorkoutPage = lazy(() => import('../pages/workout/WorkoutPage').then(module => ({ default: module.WorkoutPage })));

// Enhanced loading component with skeletons for better UX
const LoaderContainer = styled.div`
  padding: ${({ theme }) => theme.spacing.lg};
  max-width: 1200px;
  margin: 0 auto;
  height: 100vh;
`;

const HeaderSkeleton = styled.div`
  margin-bottom: ${({ theme }) => theme.spacing.xl};
`;

const SectionSkeleton = styled.div`
  margin-bottom: ${({ theme }) => theme.spacing.lg};
`;

const TopMarginSectionSkeleton = styled(SectionSkeleton)`
  margin-top: 24px;
`;

const FlexRow = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.spacing.md};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

// Enhanced page loader with skeleton UI
const PageLoader = () => (
  <LoaderContainer>
    <HeaderSkeleton>
      <Skeleton variant="rectangular" width="100%" height="64px" />
    </HeaderSkeleton>
    
    <SectionSkeleton>
      <Skeleton variant="text" width="30%" height="32px" />
      <Skeleton variant="text" width="50%" height="20px" />
    </SectionSkeleton>
    
    <FlexRow>
      <div style={{ width: '30%' }}>
        <Skeleton variant="rectangular" width="100%" height="120px" />
      </div>
      <div style={{ width: '70%' }}>
        <Skeleton variant="text" count={3} />
      </div>
    </FlexRow>
    
    <Skeleton variant="rectangular" width="100%" height="200px" />
    
    <TopMarginSectionSkeleton>
      <Skeleton variant="text" width="25%" height="24px" />
      <Skeleton variant="text" width="90%" />
      <Skeleton variant="text" width="85%" />
      <Skeleton variant="text" width="80%" />
    </TopMarginSectionSkeleton>
    
    {/* Fallback spinner for very slow loads */}
    <div style={{ textAlign: 'center', padding: '40px 0' }}>
      <LoadingSpinner size="medium" />
    </div>
  </LoaderContainer>
);

/**
 * App Routes component that renders all application routes
 * Uses React Router's useRoutes hook with our centralized route configuration
 */
export const AppRoutes: React.FC = () => {
  const routeElements = useRoutes(appRoutes);
  
  return (
    <>
      <Navigation />
      <Suspense fallback={<PageLoader />}>
        {routeElements}
      </Suspense>
    </>
  );
};

/**
 * Fallback implementation using traditional Routes/Route pattern
 * Only used if the useRoutes approach fails
 */
export const AppRoutesFallback: React.FC = () => {
  return (
    <>
      <Navigation />
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {appRoutes.map((route) => (
            <Route
              key={route.path}
              path={route.path}
              element={route.element}
            />
          ))}
        </Routes>
      </Suspense>
    </>
  );
};

// Admin routes component with improved loader
const AdminPageLoader = () => (
  <LoaderContainer>
    <HeaderSkeleton>
      <Skeleton variant="text" width="30%" height="36px" />
      <Skeleton variant="text" width="50%" height="20px" />
    </HeaderSkeleton>
    
    <Skeleton variant="table" count={5} />
  </LoaderContainer>
);

// Admin routes component as a lazy loaded module
const AdminRoutes: React.FC = () => {
  // Lazy load admin components with named exports
  const UserManagement = lazy(() => 
    import('../pages/admin/UserManagement').then(module => ({ default: module.UserManagement }))
  );
  const AdminSettings = lazy(() => 
    import('../pages/admin/AdminSettings').then(module => ({ default: module.AdminSettings }))
  );
  
  return (
    <Suspense fallback={<AdminPageLoader />}>
      <Routes>
        <Route path="users" element={<UserManagement />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </Suspense>
  );
}; 