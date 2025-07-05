import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import apiService, { endpoints } from '../services/apiService';

interface AnalysisResult {
  id: string;
  date: string;
  exercise: string;
  score: number;
  feedback: string[];
  videoUrl: string;
}

interface ProgressContextType {
  history: AnalysisResult[];
  loading: boolean;
  error: string | null;
  fetchHistory: () => Promise<void>;
  getAnalysis: (id: string) => Promise<AnalysisResult>;
  clearError: () => void;
}

const ProgressContext = createContext<ProgressContextType | undefined>(undefined);

export const useProgress = () => {
  const context = useContext(ProgressContext);
  if (!context) {
    throw new Error('useProgress must be used within a ProgressProvider');
  }
  return context;
};

export const ProgressProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [history, setHistory] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.get(endpoints.formChecks.history);
      setHistory(response.data as AnalysisResult[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setLoading(false);
    }
  }, []);

  const getAnalysis = useCallback(async (id: string): Promise<AnalysisResult> => {
    try {
      const response = await apiService.get(endpoints.formChecks.detail(id));
      return response.data as AnalysisResult;
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to fetch analysis');
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Fetch history when the component mounts
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const value = {
    history,
    loading,
    error,
    fetchHistory,
    getAnalysis,
    clearError,
  };

  return <ProgressContext.Provider value={value}>{children}</ProgressContext.Provider>;
}; 