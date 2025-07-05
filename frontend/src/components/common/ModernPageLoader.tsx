import React from 'react';
import { LoadingSpinner } from '../atoms/LoadingSpinner';

interface PageLoaderProps {
  text?: string;
  showSkeleton?: boolean;
}

const ModernPageLoader: React.FC<PageLoaderProps> = ({ 
  text = 'Loading...', 
  showSkeleton = false 
}) => {
  if (showSkeleton) {
    return (
      <div className="p-8 max-w-6xl mx-auto min-h-screen">
        {/* Header Skeleton */}
        <div className="mb-12">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4 animate-pulse"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2 animate-pulse"></div>
        </div>

        {/* Content Skeleton */}
        <div className="space-y-8">
          <div className="grid md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
                <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4 animate-pulse"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2 animate-pulse"></div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3 animate-pulse"></div>
              </div>
            ))}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-sm">
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4 animate-pulse"></div>
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full animate-pulse"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-gray-600 dark:text-gray-400 text-lg">{text}</p>
      </div>
    </div>
  );
};

export default ModernPageLoader;

// Export with original name for compatibility
export { ModernPageLoader as PageLoader };