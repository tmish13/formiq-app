import { EventEmitter } from 'events';
import { PoseAnalysisResult, Keypoint, JointAngles } from '../../types/pose';

interface ExtendedPoseAnalysisResult extends PoseAnalysisResult {
  confidence: number;
  isReliable: boolean;
  feedback: {
    posture: string;
    alignment: string;
    suggestions: string[];
  };
  timestamp: number;
  videoUrl: string;
}

export class MockFormAnalysisService extends EventEmitter {
  private initialized: boolean = false;
  private isAnalyzing: boolean = false;
  private detector: any = null;
  private analysisHistory: ExtendedPoseAnalysisResult[] = [];

  constructor() {
    super();
  }

  async initialize(): Promise<void> {
    if (this.initialized) {
      throw new Error('FormAnalysisService is already initialized');
    }
    try {
      this.detector = {
        estimatePoses: jest.fn().mockResolvedValue([{
          keypoints: [
            { x: 0, y: 0, score: 0.9, name: 'nose' },
            { x: 10, y: 10, score: 0.9, name: 'left_shoulder' },
            { x: -10, y: 10, score: 0.9, name: 'right_shoulder' },
            { x: 10, y: 20, score: 0.9, name: 'left_elbow' },
            { x: -10, y: 20, score: 0.9, name: 'right_elbow' },
            { x: 10, y: 30, score: 0.9, name: 'left_wrist' },
            { x: -10, y: 30, score: 0.9, name: 'right_wrist' },
            { x: 10, y: 40, score: 0.9, name: 'left_hip' },
            { x: -10, y: 40, score: 0.9, name: 'right_hip' },
            { x: 10, y: 50, score: 0.9, name: 'left_knee' },
            { x: -10, y: 50, score: 0.9, name: 'right_knee' },
            { x: 10, y: 60, score: 0.9, name: 'left_ankle' },
            { x: -10, y: 60, score: 0.9, name: 'right_ankle' }
          ]
        }])
      };
      this.initialized = true;
    } catch (error) {
      throw new Error('Failed to initialize pose detector');
    }
  }

  async startAnalysis(videoUrl: string): Promise<void> {
    if (!this.initialized) {
      throw new Error('FormAnalysisService must be initialized before starting analysis');
    }
    if (this.isAnalyzing) {
      throw new Error('Analysis is already in progress');
    }
    this.isAnalyzing = true;
    
    const mockResult: ExtendedPoseAnalysisResult = {
      confidence: 0.95,
      isReliable: true,
      keypoints: [
        { x: 0, y: 0, score: 0.9, name: 'nose' },
        { x: 10, y: 10, score: 0.9, name: 'left_shoulder' },
        { x: -10, y: 10, score: 0.9, name: 'right_shoulder' },
        { x: 10, y: 20, score: 0.9, name: 'left_elbow' },
        { x: -10, y: 20, score: 0.9, name: 'right_elbow' },
        { x: 10, y: 30, score: 0.9, name: 'left_wrist' },
        { x: -10, y: 30, score: 0.9, name: 'right_wrist' },
        { x: 10, y: 40, score: 0.9, name: 'left_hip' },
        { x: -10, y: 40, score: 0.9, name: 'right_hip' },
        { x: 10, y: 50, score: 0.9, name: 'left_knee' },
        { x: -10, y: 50, score: 0.9, name: 'right_knee' },
        { x: 10, y: 60, score: 0.9, name: 'left_ankle' },
        { x: -10, y: 60, score: 0.9, name: 'right_ankle' }
      ],
      score: 0.95,
      angles: {
        leftElbow: 90,
        rightElbow: 90,
        leftShoulder: 45,
        rightShoulder: 45,
        leftHip: 180,
        rightHip: 180,
        leftKnee: 180,
        rightKnee: 180,
        leftAnkle: 90,
        rightAnkle: 90,
      } as JointAngles,
      feedback: {
        posture: 'Good posture maintained',
        alignment: 'Proper alignment detected',
        suggestions: ['Keep up the good form!']
      },
      timestamp: Date.now(),
      videoUrl: videoUrl
    };

    this.analysisHistory.push(mockResult);
    this.emit('analysisResult', mockResult);
  }

  async stopAnalysis(): Promise<void> {
    if (!this.isAnalyzing) {
      throw new Error('No analysis in progress');
    }
    this.isAnalyzing = false;
  }

  async analyzeForm(videoUrl: string): Promise<ExtendedPoseAnalysisResult> {
    if (!this.initialized) {
      throw new Error('FormAnalysisService must be initialized before analyzing form');
    }
    if (!this.detector) {
      throw new Error('Pose detector not initialized');
    }

    const poses = await this.detector.estimatePoses();
    if (!poses || poses.length === 0) {
      throw new Error('No poses detected');
    }

    const result: ExtendedPoseAnalysisResult = {
      confidence: 0.95,
      isReliable: true,
      keypoints: poses[0].keypoints,
      score: 0.95,
      angles: {
        leftElbow: 90,
        rightElbow: 90,
        leftShoulder: 45,
        rightShoulder: 45,
        leftHip: 180,
        rightHip: 180,
        leftKnee: 180,
        rightKnee: 180,
        leftAnkle: 90,
        rightAnkle: 90,
      } as JointAngles,
      feedback: {
        posture: 'Good posture maintained',
        alignment: 'Proper alignment detected',
        suggestions: ['Keep up the good form!']
      },
      timestamp: Date.now(),
      videoUrl: videoUrl
    };

    this.analysisHistory.push(result);
    return result;
  }

  async getAnalysisHistory(): Promise<ExtendedPoseAnalysisResult[]> {
    return this.analysisHistory;
  }

  async saveAnalysis(result: ExtendedPoseAnalysisResult): Promise<void> {
    this.analysisHistory.push(result);
  }

  dispose(): void {
    this.initialized = false;
    this.isAnalyzing = false;
    this.detector = null;
    this.analysisHistory = [];
    this.removeAllListeners();
  }
}

export const mockFormAnalysisService = new MockFormAnalysisService();
export default mockFormAnalysisService; 