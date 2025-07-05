import apiService from './apiService';
import { EventEmitter } from 'events';

export type ExerciseType = 'squat' | 'pushup' | 'plank' | 'lunges' | 'deadlift' | 'burpees' | 'mountain_climbers';

export interface FeedbackItem {
  text: string;
  severity: 'high' | 'medium' | 'low';
  type: 'form' | 'range' | 'safety' | 'alignment' | 'tempo';
  details: string;
  confidence: number;
  timestamp: number;
}

export interface PoseAnalysisResult {
  confidence: number;
  feedback: FeedbackItem[];
  exerciseType: ExerciseType;
  isReliable: boolean;
  detectedIssues: string[];
  keypoints?: any[]; // Simplified for backend consumption
}

export interface MLScores {
  posture_score: number;
  stability_score: number;
  depth_score: number;
  overall_score: number;
}

/**
 * Simplified Pose Analysis Service for Backend Integration
 * 
 * This service replaces the complex client-side pose detection with
 * simple backend API calls aligned with the AI pipeline integration plan.
 * 
 * Backend handles:
 * - Video processing and frame extraction
 * - Pose detection using MediaPipe/MoveNet
 * - Angle calculation and movement analysis
 * - ML scoring (posture, stability, depth)
 * - Feedback generation
 */
export class PoseAnalysisService extends EventEmitter {
  private static instance: PoseAnalysisService | null = null;
  private isAnalyzing = false;
  private currentFormCheckId: string | null = null;

  private constructor() {
    super();
  }

  /**
   * Get or create singleton instance
   */
  public static async getInstance(options?: {
    minConfidence?: number;
    modelType?: string;
    exerciseType?: ExerciseType;
    onAnalysisResult?: (analysis: PoseAnalysisResult) => void;
  }): Promise<PoseAnalysisService> {
    if (!PoseAnalysisService.instance) {
      PoseAnalysisService.instance = new PoseAnalysisService();
      
      // Set up event listeners based on options
      if (options?.onAnalysisResult) {
        PoseAnalysisService.instance.on('analysisComplete', options.onAnalysisResult);
      }
    }
    
    return PoseAnalysisService.instance;
  }

  /**
   * Start analysis by uploading video to backend
   * Backend will handle all pose detection and analysis
   */
  async startAnalysis(videoElement: HTMLVideoElement, exerciseType: ExerciseType = 'squat'): Promise<void> {
    if (this.isAnalyzing) return;

    try {
      this.isAnalyzing = true;
      this.emit('analysisStarted');

      // Convert video element to blob for upload
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = videoElement.videoWidth;
      canvas.height = videoElement.videoHeight;
      ctx?.drawImage(videoElement, 0, 0);
      
      const blob = await new Promise<Blob>((resolve) => {
        canvas.toBlob((blob) => resolve(blob!), 'video/webm');
      });

      // Upload to backend for processing
      const formData = new FormData();
      formData.append('video', blob, 'exercise_video.webm');
      formData.append('exercise_type', exerciseType);

      const uploadResponse = await apiService.post('/form-checks/upload', formData);
      this.currentFormCheckId = uploadResponse.data.id;

      // Poll for analysis results
      this.pollForResults();

    } catch (error) {
      console.error('Analysis failed:', error);
      this.emit('analysisError', error);
      this.isAnalyzing = false;
    }
  }

  /**
   * Poll backend for analysis completion and results
   */
  private async pollForResults(): Promise<void> {
    if (!this.currentFormCheckId) return;

    const pollInterval = setInterval(async () => {
      try {
        const statusResponse = await apiService.get(`/form-checks/${this.currentFormCheckId}/status`);
        const { status } = statusResponse.data;

        this.emit('analysisProgress', { status });

        if (status === 'completed') {
          clearInterval(pollInterval);
          
          // Get ML analysis results
          const resultsResponse = await apiService.get(`/form-checks/${this.currentFormCheckId}/ml-analysis`);
          const mlResults = resultsResponse.data;

          // Convert backend results to frontend format
          const analysisResult: PoseAnalysisResult = {
            confidence: mlResults.confidence || 0.8,
            feedback: this.convertBackendFeedback(mlResults),
            exerciseType: mlResults.exercise_type as ExerciseType,
            isReliable: mlResults.confidence > 0.6,
            detectedIssues: mlResults.detected_issues || []
          };

          this.emit('analysisComplete', analysisResult);
          this.isAnalyzing = false;
          
        } else if (status === 'failed') {
          clearInterval(pollInterval);
          this.emit('analysisError', new Error('Backend analysis failed'));
          this.isAnalyzing = false;
        }
        
      } catch (error) {
        clearInterval(pollInterval);
        this.emit('analysisError', error);
        this.isAnalyzing = false;
      }
    }, 2000); // Poll every 2 seconds
  }

  /**
   * Convert backend ML results to frontend feedback format
   */
  private convertBackendFeedback(mlResults: any): FeedbackItem[] {
    const feedback: FeedbackItem[] = [];

    // Convert ML scores to feedback
    if (mlResults.ml_scores) {
      const { posture_score, stability_score, depth_score } = mlResults.ml_scores;
      
      if (posture_score < 0.7) {
        feedback.push({
          text: 'Improve your posture alignment',
          severity: posture_score < 0.5 ? 'high' : 'medium',
          type: 'form',
          details: `Posture score: ${Math.round(posture_score * 100)}%`,
          confidence: 0.9,
          timestamp: Date.now()
        });
      }

      if (stability_score < 0.7) {
        feedback.push({
          text: 'Focus on maintaining stability',
          severity: stability_score < 0.5 ? 'high' : 'medium',
          type: 'form',
          details: `Stability score: ${Math.round(stability_score * 100)}%`,
          confidence: 0.9,
          timestamp: Date.now()
        });
      }

      if (depth_score < 0.7) {
        feedback.push({
          text: 'Adjust your range of motion',
          severity: depth_score < 0.5 ? 'high' : 'medium',
          type: 'range',
          details: `Depth score: ${Math.round(depth_score * 100)}%`,
          confidence: 0.9,
          timestamp: Date.now()
        });
      }
    }

    // Add general feedback from backend
    if (mlResults.feedback && Array.isArray(mlResults.feedback)) {
      mlResults.feedback.forEach((item: any) => {
        feedback.push({
          text: item.message || item.text,
          severity: item.severity || 'medium',
          type: item.type || 'form',
          details: item.suggestion || item.details || '',
          confidence: item.confidence || 0.8,
          timestamp: Date.now()
        });
      });
    }

    return feedback;
  }

  /**
   * Stop analysis
   */
  stopAnalysis(): void {
    this.isAnalyzing = false;
    this.currentFormCheckId = null;
    this.emit('analysisStopped');
  }

  /**
   * Get current analysis state
   */
  getAnalysisState(): { isAnalyzing: boolean; formCheckId: string | null } {
    return {
      isAnalyzing: this.isAnalyzing,
      formCheckId: this.currentFormCheckId
    };
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.stopAnalysis();
    this.removeAllListeners();
  }
}

// Export singleton instance
export const poseAnalysisService = new PoseAnalysisService();
export default poseAnalysisService;