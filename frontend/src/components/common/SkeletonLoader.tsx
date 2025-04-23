import React from 'react';
import styled, { keyframes } from 'styled-components';
import { getThemeValue, fallbacks } from '../../utils/themeUtils';

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
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.disabled', fallbacks.color.disabled)};
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
  border-radius: 50%;
`;

const CardSkeleton = styled.div`
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '0.5rem')};
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.white', fallbacks.color.white)};
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
`;

const ListSkeleton = styled.div`
  margin-bottom: ${({ theme }) => getThemeValue(theme, 'spacing.md', '1rem')};
`;

const ListItem = styled.div`
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')};
  border-bottom: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  display: flex;
  align-items: center;
  
  &:last-child {
    border-bottom: none;
  }
`;

const TableSkeleton = styled.div`
  width: 100%;
  border: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  border-radius: ${({ theme }) => getThemeValue(theme, 'borderRadius.md', '0.5rem')};
  overflow: hidden;
`;

const TableRow = styled.div`
  display: flex;
  padding: ${({ theme }) => getThemeValue(theme, 'spacing.sm', '0.75rem')};
  border-bottom: 1px solid ${({ theme }) => getThemeValue(theme, 'colors.border', fallbacks.color.border)};
  
  &:last-child {
    border-bottom: none;
  }
`;

const TableHeader = styled(TableRow)`
  background-color: ${({ theme }) => getThemeValue(theme, 'colors.background', fallbacks.color.background)};
  font-weight: ${({ theme }) => getThemeValue(theme, 'typography.fontWeight.medium', '500')};
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