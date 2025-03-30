import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { formCheckService } from '../services/formCheckService';
import {
  setFormChecks,
  setCurrentFormCheck,
  addFormCheck,
  updateFormCheck,
  deleteFormCheck,
  updateFormCheckStatus,
  setLoading,
  setError,
} from '../store/slices/formCheckSlice';
import { ExerciseType } from '../types';
import { FormCheck } from '../types/formCheck';

export const useFormCheck = () => {
  const dispatch = useDispatch();
  const {
    formChecks,
    currentFormCheck,
    isLoading,
    error,
  } = useSelector((state: RootState) => state.formCheck);

  const fetchFormChecks = useCallback(async () => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.getUserFormChecks();
      dispatch(setFormChecks(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch form checks'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchFormCheck = useCallback(async (id: number) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.getFormCheck(id);
      dispatch(setCurrentFormCheck(data));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch form check'));
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const submitFormCheck = useCallback(async (
    video: File,
    exerciseType: ExerciseType,
    notes?: string
  ) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.submitFormCheck(video, exerciseType, notes);
      dispatch(addFormCheck(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to submit form check'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const removeFormCheck = useCallback(async (id: number) => {
    try {
      dispatch(setLoading(true));
      await formCheckService.deleteFormCheck(id);
      dispatch(deleteFormCheck(id));
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to delete form check'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const completeAnalysis = useCallback(async (
    id: number,
    summary: string,
    overallScore: number
  ) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.completeAnalysis(id, summary, overallScore);
      dispatch(updateFormCheck(data));
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to complete analysis'));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const fetchFormChecksByExercise = useCallback(async (exerciseType: ExerciseType) => {
    try {
      dispatch(setLoading(true));
      const data = await formCheckService.getFormChecksByExercise(exerciseType);
      return data;
    } catch (err) {
      dispatch(setError(err instanceof Error ? err.message : 'Failed to fetch form checks by exercise'));
      throw err;
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
    deleteFormCheck: removeFormCheck,
    completeAnalysis,
    fetchFormChecksByExercise,
  };
}; 