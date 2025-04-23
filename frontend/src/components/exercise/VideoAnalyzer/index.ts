import VideoAnalyzer from './VideoAnalyzer';

export interface VideoAnalyzerProps {
  videoFile: File;
  exerciseType: string;
  isAnalyzing: boolean;
  onError: (error: unknown) => void;
  onAnalysisStart: () => void;
}

export default VideoAnalyzer; 