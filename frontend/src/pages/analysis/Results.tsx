import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import FormCheckFeedback from '../../components/FormCheckFeedback';
import { VideoPlayer, LoadingSpinner } from '../../components/common';

interface FormCheck {
  id: string;
  exercise_type: string;
  score: number;
  video_url?: string;
  overall_feedback?: string;
  issues?: string[];
  suggestions?: string[];
}

export const Results: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formCheck, setFormCheck] = useState<FormCheck | null>(null);

  useEffect(() => {
    const fetchFormCheck = async () => {
      if (!id) {
        setError('No form check ID provided');
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`/api/form-checks/${id}`);
        if (!response.ok) {
          if (response.status === 404) {
            setError('Form check not found');
          } else {
            setError('An error occurred while fetching the form check');
          }
          setLoading(false);
          return;
        }

        const data = await response.json();
        setFormCheck(data);
      } catch (err) {
        setError('An error occurred while fetching the form check');
      } finally {
        setLoading(false);
      }
    };

    fetchFormCheck();
  }, [id]);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <LoadingSpinner data-testid="loading-spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-red-500" data-testid="error-message">{error}</div>
      </div>
    );
  }

  if (!formCheck) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-500" data-testid="error-message">Form check not found</div>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="container mx-auto px-4 py-8" data-testid="results-container">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6" data-testid="results-title">Form Analysis Results</h1>
        
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6" data-testid="results-content">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold" data-testid="exercise-type">
              Exercise Type: {formCheck.exercise_type}
            </h2>
            <div className={`text-2xl font-bold ${getScoreColor(formCheck.score)}`} data-testid="score">
              Score: {formCheck.score}%
            </div>
          </div>

          {formCheck.video_url ? (
            <div className="mb-6" data-testid="video-container">
              <VideoPlayer videoUrl={formCheck.video_url} data-testid="video-player" />
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8" data-testid="no-video-message">
              No video available for this form check
            </div>
          )}

          <FormCheckFeedback
            feedback={formCheck.overall_feedback ?? ''}
            score={formCheck.score}
            data-testid="form-check-feedback"
          />
        </div>
      </div>
    </div>
  );
};