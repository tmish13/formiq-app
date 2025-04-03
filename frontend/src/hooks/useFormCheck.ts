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
    video: File | null,
    exerciseType: ExerciseType,
    notes?: string,
    videoUrl?: string
  ) => {
    try {
      dispatch(setLoading(true));
      let data;
      
      if (videoUrl) {
        // If we already have a video URL (from direct S3 upload), use it
        data = await formCheckService.submitFormCheckWithUrl(
          videoUrl,
          exerciseType,
          notes
        );
      } else if (video) {
        // Otherwise, upload the video file through the API
        data = await formCheckService.submitFormCheck(
          video,
          exerciseType,
          notes
        );
      } else {
        throw new Error('Either video file or video URL must be provided');
      }
      
      dispatch(addFormCheck(data));
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to submit form check';
      dispatch(setError(errorMessage));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const getPresignedUploadUrl = useCallback(async (
    filename: string,
    contentType: string,
    exerciseType: ExerciseType
  ) => {
    try {
      dispatch(setLoading(true));
      return await formCheckService.getPresignedUploadUrl(
        filename,
        contentType,
        exerciseType
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get upload URL';
      dispatch(setError(errorMessage));
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete form check';
      dispatch(setError(errorMessage));
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to complete analysis';
      dispatch(setError(errorMessage));
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
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch form checks by exercise';
      dispatch(setError(errorMessage));
      throw err;
    } finally {
      dispatch(setLoading(false));
    }
  }, [dispatch]);

  const addFeedback = useCallback(async (
    formCheckId: number,
    feedbackData: {
      feedbackType: string;
      severity: string;
      timestamp: number;
      description: string;
      suggestions?: string;
      isAiGenerated?: boolean;
    }
  ) => {
    try {
      dispatch(setLoading(true));
      const feedback = await formCheckService.addFeedback(formCheckId, feedbackData);
      
      // Get updated form check with new feedback
      const updatedFormCheck = await formCheckService.getFormCheck(formCheckId);
      dispatch(updateFormCheck(updatedFormCheck));
      
      return feedback;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to add feedback';
      dispatch(setError(errorMessage));
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
    getPresignedUploadUrl,
    deleteFormCheck: removeFormCheck,
    completeAnalysis,
    fetchFormChecksByExercise,
    addFeedback,
  };
}; 