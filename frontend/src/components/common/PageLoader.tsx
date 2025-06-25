import React from 'react';
import styled from 'styled-components';
import { LoadingSpinner } from '../atoms/LoadingSpinner';
import { Skeleton } from './SkeletonLoader';

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

/**
 * Enhanced page loader with skeleton UI
 * Used as a fallback during lazy loading of routes
 */
export const PageLoader: React.FC = () => (
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
 * Simplified page loader for admin pages
 */
export const AdminPageLoader: React.FC = () => (
  <LoaderContainer>
    <HeaderSkeleton>
      <Skeleton variant="text" width="30%" height="36px" />
      <Skeleton variant="text" width="50%" height="20px" />
    </HeaderSkeleton>
    
    <Skeleton variant="table" count={5} />
  </LoaderContainer>
); 