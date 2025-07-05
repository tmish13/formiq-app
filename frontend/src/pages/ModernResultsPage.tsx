import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';

const ModernResultsPage: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();

  // Mock results data
  const results = {
    score: 85,
    exercise: 'Squat',
    feedback: [
      { type: 'good', message: 'Good knee alignment' },
      { type: 'warning', message: 'Slightly shallow depth' },
      { type: 'tip', message: 'Try to go lower for better hip mobility' }
    ]
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Analysis Results</CardTitle>
            <CardDescription>
              {videoId ? `Video ID: ${videoId}` : 'Your exercise form analysis'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="text-center">
              <div className="text-4xl font-bold text-green-600 mb-2">
                {results.score}%
              </div>
              <Badge variant="secondary" className="text-lg px-4 py-2">
                {results.exercise}
              </Badge>
            </div>

            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Feedback</h3>
              {results.feedback.map((item, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className={`w-2 h-2 rounded-full mt-2 ${
                    item.type === 'good' ? 'bg-green-500' :
                    item.type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'
                  }`} />
                  <p className="text-sm">{item.message}</p>
                </div>
              ))}
            </div>

            <div className="flex space-x-4">
              <Button onClick={() => navigate('/dashboard')} className="flex-1">
                Back to Dashboard
              </Button>
              <Button variant="outline" onClick={() => navigate('/form-analysis')} className="flex-1">
                Analyze Another Video
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ModernResultsPage;