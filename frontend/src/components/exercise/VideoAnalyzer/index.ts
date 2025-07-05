export { default as VideoAnalyzer } from './VideoAnalyzer';
export { VideoAnalyzer as default } from './VideoAnalyzer';

export interface VideoAnalyzerProps {
  videoFile: File;
  exerciseType: string;
  isAnalyzing: boolean;
  onError: (error: unknown) => void;
  onAnalysisStart: () => void;
} 