import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { formCheckService } from '../services/formCheckService';
import { ExerciseType } from '../types';
import {
  setLoading,
  setError,
  setFormChecks,
  setCurrentFormCheck,
  deleteFormCheck,
} from '../store/slices/formCheckSlice';
import { RootState } from '../store';

export const useFormCheck = () => {
  const dispatch = useDispatch();
  const { isLoading, error, formChecks, currentFormCheck } = useSelector((state: RootState) => state.formCheck);

  const fetchFormChecks = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.getFormChecks();
      dispatch(setFormChecks(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch form checks'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchFormCheck = async (id: string) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.getFormCheck(id);
      dispatch(setCurrentFormCheck(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch form check'));
    } finally {
      dispatch(setLoading(false));
    }
  };

  const submitFormCheck = async (
    video: File,
    exerciseType: ExerciseType,
    onProgress?: (progress: number) => void
  ) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.uploadVideo(video, exerciseType, onProgress);
      dispatch(setCurrentFormCheck(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to submit form check'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  };

  const deleteFormCheckById = async (id: number) => {
    try {
      await formCheckService.deleteFormCheck(id);
      dispatch(deleteFormCheck(id));
    } catch (error) {
      console.error('Error deleting form check:', error);
      throw error;
    }
  };

  const analyzeFormCheck = async (id: string) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.analyze(id);
      dispatch(setCurrentFormCheck(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to analyze form check'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  };

  const fetchHistory = async () => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.getHistory();
      dispatch(setFormChecks(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch history'));
    } finally {
      dispatch(setLoading(false));
    }
  };

  return {
    fetchFormChecks,
    fetchFormCheck,
    submitFormCheck,
    deleteFormCheckById,
    analyzeFormCheck,
    fetchHistory,
    formChecks,
    currentFormCheck,
    isLoading,
    error,
  };
}; 