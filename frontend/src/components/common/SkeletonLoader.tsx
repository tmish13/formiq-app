import React from 'react';
import styled, { keyframes } from 'styled-components';

// Types for skeleton loader
export type SkeletonVariant = 'text' | 'circular' | 'rectangular' | 'card' | 'list' | 'table';

interface SkeletonProps {
  variant?: SkeletonVariant;
  width?: string;
  height?: string;
  borderRadius?: string;
  count?: number;
  className?: string;
  animation?: boolean;
}

// Animation keyframes
const shimmer = keyframes`
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
`;

const SkeletonBase = styled.div<{
  width?: string;
  height?: string;
  borderRadius?: string;
  animation?: boolean;
}>`
  display: inline-block;
  width: ${({ width }) => width || '100%'};
  height: ${({ height }) => height || '16px'};
  border-radius: ${({ borderRadius }) => borderRadius || '4px'};
  background-color: ${({ theme }) => theme.colors.disabled};
  position: relative;
  overflow: hidden;
  
  ${({ animation }) =>
    animation !== false &&
    `
    &::after {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-image: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0) 0,
        rgba(255, 255, 255, 0.2) 20%,
        rgba(255, 255, 255, 0.5) 60%,
        rgba(255, 255, 255, 0)
      );
      background-size: 200px 100%;
      background-repeat: no-repeat;
      animation: ${shimmer} 1.5s infinite;
    }
  `}
`;

const TextSkeleton = styled(SkeletonBase)`
  margin-bottom: 8px;
`;

const CircularSkeleton = styled(SkeletonBase)`
  border-radius: ${({ theme }) => theme.borderRadius.full};
`;

const CardSkeleton = styled.div`
  border-radius: ${({ theme }) => theme.borderRadius.md};
  padding: ${({ theme }) => theme.spacing.md};
  background-color: ${({ theme }) => theme.colors.white};
  box-shadow: ${({ theme }) => theme.shadows.sm};
  border: 1px solid ${({ theme }) => theme.colors.border};
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const ListSkeleton = styled.div`
  margin-bottom: ${({ theme }) => theme.spacing.md};
`;

const ListItem = styled.div`
  padding: ${({ theme }) => theme.spacing.sm};
  border-bottom: 1px solid ${({ theme }) => theme.colors.border};
  display: flex;
  align-items: center;
  
  &:last-child {
    border-bottom: none;
  }
`;

const TableSkeleton = styled.div`
  width: 100%;
  border: 1px solid ${({ theme }) => theme.colors.border};
  border-radius: ${({ theme }) => theme.borderRadius.md};
  overflow: hidden;
`;

const TableRow = styled.div`
  display: flex;
  padding: ${({ theme }) => theme.spacing.sm};
  border-bottom: 1px solid ${({ theme }) => theme.colors.border};
  
  &:last-child {
    border-bottom: none;
  }
`;

const TableHeader = styled(TableRow)`
  background-color: ${({ theme }) => theme.colors.background};
  font-weight: ${({ theme }) => theme.typography.fontWeight.medium};
`;

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  width,
  height,
  borderRadius,
  count = 1,
  className,
  animation = true,
}) => {
  // Helper function to render multiple skeletons
  const renderSkeletons = (Component: React.ElementType, count: number) => {
    return Array.from({ length: count }).map((_, index) => (
      <Component
        key={index}
        width={width}
        height={height}
        borderRadius={borderRadius}
        animation={animation}
        className={className}
      />
    ));
  };

  switch (variant) {
    case 'text':
      return <>{renderSkeletons(TextSkeleton, count)}</>;
    case 'circular':
      return <>{renderSkeletons(CircularSkeleton, count)}</>;
    case 'rectangular':
      return <>{renderSkeletons(SkeletonBase, count)}</>;
    case 'card':
      return (
        <CardSkeleton className={className}>
          <TextSkeleton width="60%" height="24px" animation={animation} />
          <TextSkeleton width="90%" animation={animation} />
          <TextSkeleton width="80%" animation={animation} />
        </CardSkeleton>
      );
    case 'list':
      return (
        <ListSkeleton className={className}>
          {Array.from({ length: count }).map((_, index) => (
            <ListItem key={index}>
              <CircularSkeleton width="40px" height="40px" animation={animation} />
              <div style={{ marginLeft: '12px', width: '100%' }}>
                <TextSkeleton width="40%" animation={animation} />
                <TextSkeleton width="70%" animation={animation} />
              </div>
            </ListItem>
          ))}
        </ListSkeleton>
      );
    case 'table':
      return (
        <TableSkeleton className={className}>
          <TableHeader>
            <SkeletonBase width="20%" height="24px" animation={animation} />
            <SkeletonBase width="30%" height="24px" animation={animation} style={{ margin: '0 12px' }} />
            <SkeletonBase width="30%" height="24px" animation={animation} />
          </TableHeader>
          {Array.from({ length: count }).map((_, index) => (
            <TableRow key={index}>
              <SkeletonBase width="20%" height="16px" animation={animation} />
              <SkeletonBase width="30%" height="16px" animation={animation} style={{ margin: '0 12px' }} />
              <SkeletonBase width="30%" height="16px" animation={animation} />
            </TableRow>
          ))}
        </TableSkeleton>
      );
    default:
      return <>{renderSkeletons(SkeletonBase, count)}</>;
  }
};

export default Skeleton; 