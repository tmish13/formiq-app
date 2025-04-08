import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Skeleton } from '../components/common/SkeletonLoader';
import styled from 'styled-components';

// Lazy load components to improve performance
const LoginPage = lazy(() => import('../pages/auth/LoginPage').then(module => ({ default: module.LoginPage })));
const RegisterPage = lazy(() => import('../pages/auth/RegisterPage').then(module => ({ default: module.RegisterPage })));
const DashboardPage = lazy(() => import('../pages/dashboard/DashboardPage').then(module => ({ default: module.DashboardPage })));
const ProfilePage = lazy(() => import('../pages/profile/ProfilePage').then(module => ({ default: module.ProfilePage })));
const WorkoutPage = lazy(() => import('../pages/workout/WorkoutPage').then(module => ({ default: module.WorkoutPage })));
const FormCheckUploadPage = lazy(() => import('../pages/workout/FormCheckUploadPage').then(module => ({ default: module.FormCheckUploadPage })));
const AnalysisPage = lazy(() => import('../pages/analysis/AnalysisPage').then(module => ({ default: module.AnalysisPage })));
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then(module => ({ default: module.NotFoundPage })));

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

export const AppRoutes: React.FC = () => {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            <ProtectedRoute requireAuth={false}>
              <LoginPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/register"
          element={
            <ProtectedRoute requireAuth={false}>
              <RegisterPage />
            </ProtectedRoute>
          }
        />

        {/* Protected routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/workout"
          element={
            <ProtectedRoute>
              <WorkoutPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/workout/form-check/upload"
          element={
            <ProtectedRoute>
              <FormCheckUploadPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analysis"
          element={
            <ProtectedRoute>
              <AnalysisPage />
            </ProtectedRoute>
          }
        />

        {/* Admin routes */}
        <Route
          path="/admin/*"
          element={
            <ProtectedRoute roles={['admin']}>
              <AdminRoutes />
            </ProtectedRoute>
          }
        />

        {/* 404 page */}
        <Route path="/404" element={<NotFoundPage />} />

        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Catch all route */}
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </Suspense>
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