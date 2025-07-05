import React from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { LoadingSpinner } from '../components/atoms/LoadingSpinner';
import { Progress } from '../components/ui/progress';

const ModernProcessingPage: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const [progress, setProgress] = React.useState(0);

  React.useEffect(() => {
    // Simulate processing progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        const newProgress = prev + Math.random() * 10;
        return newProgress >= 100 ? 100 : newProgress;
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Processing Your Video</CardTitle>
          <CardDescription>
            {videoId ? `Video ID: ${videoId}` : 'Analyzing your exercise form...'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="text-center">
            <LoadingSpinner size="lg" />
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="w-full" />
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              This may take a few minutes. Please don't close this page.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ModernProcessingPage;