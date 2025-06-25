import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import styled from 'styled-components';
import { FormAnalysisResult } from '../../types/formAnalysis';
import VideoPlayer from '../VideoPlayer';
import { FormFeedback } from '../FormFeedback';
import { LoadingSpinner } from '../atoms/LoadingSpinner';

const Container = styled.div`
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
`;

const VideoSection = styled.div`
  margin-bottom: 30px;
`;

const ResultsSection = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`;

const ConfidenceScore = styled.div`
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
  color: ${({ theme }) => theme?.colors?.primary?.main || '#1976d2'};
`;

const ErrorMessage = styled.div`
  color: ${({ theme }) => theme?.colors?.error?.main || '#d32f2f'};
  text-align: center;
  padding: 20px;
`;

export const Results: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [result, setResult] = useState<FormAnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await fetch(`/api/form-analysis/${id}`);
        if (!response.ok) {
          throw new Error('Failed to fetch analysis results');
        }
        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError('Failed to load analysis results. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, [id]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <ErrorMessage>{error}</ErrorMessage>;
  }

  if (!result) {
    return <ErrorMessage>No results found</ErrorMessage>;
  }

  return (
    <Container>
      <VideoSection>
        <VideoPlayer videoUrl={result.videoUrl} />
      </VideoSection>

      <ResultsSection>
        <ConfidenceScore>Confidence Score: {Math.round(result.confidence * 100)}%</ConfidenceScore>
        <FormFeedback 
          feedback={result.feedback.map(f => ({
            isValid: f.type === 'success',
            message: f.message,
            confidence: f.confidence
          }))}
          confidence={result.confidence}
          repetitionCount={1}
          phase="middle"
        />
      </ResultsSection>
    </Container>
  );
}; 