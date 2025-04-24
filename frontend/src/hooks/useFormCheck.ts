import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { formCheckService } from '../services/formCheckService';
import { ExerciseType } from '../types';
import {
  setLoading,
  setError,
  setFormChecks,
  setCurrentFormCheck,
  deleteFormCheck as deleteFormCheckAction,
  updateFormCheck
} from '../store/slices/formCheckSlice';
import { RootState } from '../store';

export const useFormCheck = () => {
  const dispatch = useDispatch();
  const { formChecks, currentFormCheck, isLoading, error } = useSelector((state: RootState) => state.formCheck);

  const fetchFormChecks = useCallback(async () => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      const response = await formCheckService.getFormChecks();
      if (response) {
        dispatch(setFormChecks(response));
      } else {
        dispatch(setFormChecks([]));
      }
    } catch (error) {
      console.error('Error fetching form checks:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch form checks';
      dispatch(setError(errorMessage));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchFormCheck = useCallback(async (id: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    dispatch(setCurrentFormCheck(null));
    try {
      const response = await formCheckService.getFormCheck(id);
      if (response) {
        dispatch(setCurrentFormCheck(response));
      } else {
        dispatch(setError('Form check not found'));
      }
    } catch (error) {
      console.error('Error fetching form check:', error);
      const errorMessage = error instanceof Error ? error.message : 'Error loading form check';
      dispatch(setError(errorMessage));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const submitFormCheck = useCallback(async (
    video: File,
    exerciseType: ExerciseType,
    onProgress?: (progress: number) => void
  ) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      const response = await formCheckService.uploadVideo(video, exerciseType, onProgress);
      if (response) {
        dispatch(setCurrentFormCheck(response));
        return response;
      }
      return null;
    } catch (error) {
      console.error('Error submitting form check:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to submit form check';
      dispatch(setError(errorMessage));
      return null;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const deleteFormCheckById = useCallback(async (id: number) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      await formCheckService.deleteFormCheck(id);
      dispatch(deleteFormCheckAction(id));
      if (currentFormCheck && currentFormCheck.id === id) {
        dispatch(setCurrentFormCheck(null));
      }
      return true;
    } catch (error) {
      console.error('Error deleting form check:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete form check';
      dispatch(setError(errorMessage));
      return false;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch, currentFormCheck]);

  const analyzeFormCheck = useCallback(async (id: string) => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      const response = await formCheckService.analyze(id);
      if (response) {
        dispatch(updateFormCheck(response));
        dispatch(setCurrentFormCheck(response));
        return response;
      }
      return null;
    } catch (error) {
      console.error('Error analyzing form check:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to analyze form check';
      dispatch(setError(errorMessage));
      return null;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchHistory = useCallback(async () => {
    dispatch(setLoading(true));
    dispatch(setError(null));
    try {
      const response = await formCheckService.getHistory();
      if (response) {
        dispatch(setFormChecks(response));
        return response;
      }
      dispatch(setFormChecks([]));
      return null;
    } catch (error) {
      console.error('Error fetching form check history:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch form check history';
      dispatch(setError(errorMessage));
      return null;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  return {
    formChecks,
    currentFormCheck,
    isLoading,
    error,
    fetchFormChecks,
    fetchFormCheck,
    submitFormCheck,
    deleteFormCheckById,
    analyzeFormCheck,
    fetchHistory,
  };
}; 