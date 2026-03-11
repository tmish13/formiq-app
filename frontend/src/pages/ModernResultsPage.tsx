/**
 * ModernResultsPage — redirect wrapper.
 *
 * Route: /form-check/results/:videoId
 *
 * Resolves videoId → formCheckId via the backend, then redirects to
 * the canonical AnalysisPage at /analysis/:formCheckId.
 *
 * If the form check hasn't been created yet (processing still in
 * progress), falls back to the processing page.
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LoadingSpinner } from '../components/atoms/LoadingSpinner';
import { formCheckService } from '../services/formCheckService';

const ModernResultsPage: React.FC = () => {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) return;

    const resolve = async () => {
      try {
        // GET /form-checks/{videoId} returns the FormCheck associated with this video
        const formCheck = await formCheckService.getFormCheck(videoId);
        navigate(`/analysis/${formCheck.id}`, { replace: true });
      } catch (err) {
        console.error('Failed to resolve form check for video:', err);
        setError('Analysis not found. The video may still be processing.');
      }
    };

    resolve();
  }, [videoId, navigate]);

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center px-4">
        <div className="text-center space-y-4">
          <p className="text-gray-600 dark:text-gray-400">{error}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <LoadingSpinner size="lg" />
    </div>
  );
};

export default ModernResultsPage;
