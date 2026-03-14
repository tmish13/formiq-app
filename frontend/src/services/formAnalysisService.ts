import apiService from './apiService';
import { FormAnalysisRequest, FormAnalysisResult, FormAnalysisResponse, JointAngles, FormFeedback } from '../types/formAnalysis';
import { EventEmitter } from 'events';
import * as poseDetection from '@tensorflow-models/pose-detection';
import { Keypoint } from '@tensorflow-models/pose-detection';

// Default values for required FormAnalysisResult fields that this service cannot compute
const DEFAULT_METRICS = { alignment: 0, stability: 0, symmetry: 0, consistency: 0 };

interface FormAnalysisState {
  isAnalyzing: boolean;
  error: string | null;
  lastAnalysis: FormAnalysisResult | null;
}

export class FormAnalysisService extends EventEmitter {
  private static instance: FormAnalysisService | null = null;
  private detector: poseDetection.PoseDetector | null = null;
  private isAnalyzing: boolean = false;
  private minConfidence: number = 0.5;

  private constructor() {
    super();
  }

  public static getInstance(): FormAnalysisService {
    if (!FormAnalysisService.instance) {
      FormAnalysisService.instance = new FormAnalysisService();
    }
    return FormAnalysisService.instance;
  }

  async initialize(): Promise<void> {
    if (this.detector) {
      return; // Already initialized
    }

    try {
      const model = poseDetection.SupportedModels.MoveNet;
      const detectorConfig = {
        modelType: poseDetection.movenet.modelType.SINGLEPOSE_LIGHTNING,
      };
      this.detector = await poseDetection.createDetector(model, detectorConfig);
    } catch (error) {
      console.error('Failed to initialize pose detector:', error);
      throw new Error('Failed to initialize pose detector');
    }
  }

  async startAnalysis(videoElement: HTMLVideoElement): Promise<void> {
    if (!this.detector) {
      await this.initialize();
    }

    if (this.isAnalyzing) {
      return;
    }

    this.isAnalyzing = true;
    try {
      await this.processVideo(videoElement);
    } catch (error) {
      this.emit('error', error);
      throw error;
    } finally {
      this.isAnalyzing = false;
    }
  }

  stopAnalysis(): void {
    this.isAnalyzing = false;
  }

  private async processVideo(videoElement: HTMLVideoElement): Promise<void> {
    while (this.isAnalyzing && this.detector) {
      try {
        const poses = await this.detector.estimatePoses(videoElement);
        if (poses.length > 0) {
          const result = this.analyzePose(poses[0]);
          this.emit('analysis', result);
        }
      } catch (error) {
        console.error('Error processing video frame:', error);
        this.emit('error', error);
      }
      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  private analyzePose(pose: poseDetection.Pose): FormAnalysisResult {
    const keypoints = pose.keypoints;
    const angles = this.calculateJointAngles(keypoints);
    const feedback = this.generateFeedback(keypoints, angles);

    return {
      confidence: pose.score || 0,
      isReliable: (pose.score || 0) > this.minConfidence,
      keypoints,
      angles,
      feedback,
      suggestions: [],
      metrics: DEFAULT_METRICS,
      timestamp: Date.now(),
      videoUrl: ''
    };
  }

  private calculateJointAngles(keypoints: poseDetection.Keypoint[]): JointAngles {
    const angles: JointAngles = {};

    // Calculate angles between keypoints
    const findKeypoint = (name: string) => keypoints.find(kp => kp.name === name);

    // Calculate knee angle
    const leftHip = findKeypoint('left_hip');
    const leftKnee = findKeypoint('left_knee');
    const leftAnkle = findKeypoint('left_ankle');

    if (leftHip && leftKnee && leftAnkle) {
      const angle = this.calculateAngle(
        { x: leftHip.x, y: leftHip.y },
        { x: leftKnee.x, y: leftKnee.y },
        { x: leftAnkle.x, y: leftAnkle.y }
      );

      angles.leftKnee = {
        value: angle,
        confidence: Math.min(leftHip.score || 0, leftKnee.score || 0, leftAnkle.score || 0)
      };
    }

    return angles;
  }

  private calculateAngle(p1: {x: number, y: number}, p2: {x: number, y: number}, p3: {x: number, y: number}): number {
    const radians = Math.atan2(p3.y - p2.y, p3.x - p2.x) - Math.atan2(p1.y - p2.y, p1.x - p2.x);
    let angle = Math.abs(radians * 180.0 / Math.PI);

    if (angle > 180.0) {
      angle = 360 - angle;
    }

    return angle;
  }

  private generateFeedback(keypoints: poseDetection.Keypoint[], angles: JointAngles): FormFeedback[] {
    const feedback: FormFeedback[] = [];

    // Generate feedback based on angles and keypoint positions
    const leftKnee = angles.leftKnee;
    if (leftKnee && leftKnee.value < 90) {
      feedback.push({
        type: 'warning',
        message: 'Bend your knees more to achieve proper form',
        confidence: leftKnee.confidence,
        jointName: 'leftKnee'
      });
    }

    return feedback;
  }

  private state: FormAnalysisState = {
    isAnalyzing: false,
    error: null,
    lastAnalysis: null
  };

  private setState(newState: Partial<FormAnalysisState>) {
    this.state = { ...this.state, ...newState };
  }

  public getState(): FormAnalysisState {
    return this.state;
  }

  async analyzeForm(request: FormAnalysisRequest): Promise<FormAnalysisResponse> {
    try {
      if (!this.detector) {
        await this.initialize();
      }

      let result: FormAnalysisResult;
      const startTime = Date.now();

      if (request.keypoints) {
        const pose = {
          keypoints: request.keypoints,
          score: 1.0
        };
        result = this.analyzePose(pose as poseDetection.Pose);
        if (request.videoUrl) {
          result.videoUrl = request.videoUrl;
        }
      } else if (request.videoUrl) {
        throw new Error('No keypoints or video URL provided');
      } else {
        throw new Error('No keypoints or video URL provided');
      }

      const processingTime = Date.now() - startTime;

      return {
        result,
        stats: {
          averageConfidence: result.confidence,
          successRate: result.isReliable ? 1.0 : 0.0,
          processingTime
        },
        status: 'success'
      };
    } catch (error) {
      return {
        result: {
          confidence: 0,
          isReliable: false,
          keypoints: [],
          angles: {},
          feedback: [],
          suggestions: [],
          metrics: DEFAULT_METRICS,
          timestamp: Date.now(),
          videoUrl: ''
        },
        stats: {
          averageConfidence: 0,
          successRate: 0,
          processingTime: 0
        },
        status: 'error',
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  public async getAnalysisHistory(): Promise<FormAnalysisResult[]> {
    try {
      const response = await apiService.get<FormAnalysisResult[]>('/form-checks/history');
      return response.data;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch analysis history';
      this.setState({ error: errorMessage });
      throw error;
    }
  }

  public async saveAnalysis(result: FormAnalysisResult): Promise<void> {
    try {
      await apiService.post('/form-checks', result);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save analysis';
      this.setState({ error: errorMessage });
      throw error;
    }
  }
}

export const formAnalysisService = FormAnalysisService.getInstance();
