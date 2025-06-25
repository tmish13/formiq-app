/**
 * Machine Learning related types for FormIQ
 */

// ML Score data structure
export interface MLScores {
  posture_score: number;      // 0-100 score for posture quality
  stability_score: number;    // 0-100 score for balance/stability
  depth_score: number;        // 0-100 score for range of motion
  confidence?: number;        // Overall model confidence (0-1)
  ml_model_version?: string;  // Version of the ML model used
}

// Keypoint data structure for pose visualization
export interface Keypoint {
  x: number;                  // X coordinate (normalized 0-1 or pixel)
  y: number;                  // Y coordinate (normalized 0-1 or pixel)
  z?: number;                 // Z coordinate for 3D poses (optional)
  score: number;              // Confidence score (0-1)
  name: string;               // Keypoint name (e.g., 'left_shoulder', 'right_knee')
  visible?: boolean;          // Whether keypoint is visible in frame
}

// Pose data structure
export interface PoseData {
  keypoints: Keypoint[];      // Array of detected keypoints
  score: number;              // Overall pose detection confidence
  timestamp?: number;         // Frame timestamp in milliseconds
  frame_index?: number;       // Frame number in video sequence
}

// Pose issue/fault detection
export interface PoseIssue {
  type: 'posture' | 'stability' | 'depth' | 'tempo' | 'alignment';
  severity: 'low' | 'medium' | 'high';
  description: string;
  affected_keypoints: string[]; // Names of keypoints involved in the issue
  timestamp?: number;         // When the issue occurs in the video
  suggestions: string[];      // Specific improvement suggestions
}

// Visual overlay configuration
export interface OverlayConfig {
  showSkeleton?: boolean;           // Show skeleton connections
  showKeypoints?: boolean;          // Show individual keypoints
  showConfidenceThreshold?: number; // Min confidence to display (0-1)
  keypointRadius?: number;          // Size of keypoint circles
  lineWidth?: number;               // Width of skeleton lines
  colors?: {
    keypoints?: string;             // Color for keypoints
    skeleton?: string;              // Color for skeleton lines
    reference?: string;             // Color for reference pose
    issues?: string;                // Color for highlighted issues
  };
}

// Reference pose data for exercise demonstrations
export interface ReferencePose {
  exercise_id: string;
  exercise_name: string;
  key_phases: {
    name: string;                   // e.g., 'start', 'bottom', 'top'
    keypoints: Keypoint[];          // Ideal keypoint positions for this phase
    duration?: number;              // How long to hold this position (ms)
    description?: string;           // Description of this phase
  }[];
  ideal_angles?: {
    joint: string;                  // e.g., 'knee', 'hip', 'elbow'
    min_angle: number;              // Minimum acceptable angle
    max_angle: number;              // Maximum acceptable angle
    ideal_angle: number;            // Target angle
  }[];
}

// ML Score trend data for progress tracking
export interface MLScoreTrend {
  date: string;                     // ISO date string
  posture_score: number;
  stability_score: number;
  depth_score: number;
  overall_score?: number;           // Computed overall score
  exercise_type: string;
}

// Analysis results with ML data
export interface MLAnalysisResult {
  ml_scores: MLScores;
  pose_data: PoseData[];            // Frame-by-frame pose data
  detected_issues?: PoseIssue[];    // Issues found by ML model
  reference_pose?: ReferencePose;   // Reference pose for comparison
  recommendations: string[];        // AI-generated improvement suggestions
  analysis_metadata: {
    processing_time: number;        // Time taken for analysis (ms)
    frames_analyzed: number;        // Total frames processed
    frames_with_issues: number;     // Frames with detected issues
    model_confidence: number;       // Overall model confidence
  };
}

// Component prop types for ML score display
export interface MLScoreCardProps {
  scores: MLScores;
  previousScores?: MLScores;        // For comparison/trend display
  variant?: 'detailed' | 'summary' | 'compact';
  showTrend?: boolean;
  showConfidence?: boolean;
  onScoreClick?: (scoreType: keyof MLScores) => void;
}

export interface MLScoreComparisonProps {
  currentScores: MLScores;
  previousScores?: MLScores;
  targetScores?: MLScores;
  timeframe?: 'session' | 'week' | 'month';
  exerciseType: string;
}

// Pose overlay component props
export interface PoseOverlayProps {
  userPose?: PoseData;
  referencePose?: PoseData;
  config?: OverlayConfig;
  highlightIssues?: PoseIssue[];
  onKeypointHover?: (keypoint: Keypoint) => void;
  onIssueClick?: (issue: PoseIssue) => void;
}

// Real-time analysis state
export interface RealTimeAnalysisState {
  isAnalyzing: boolean;
  currentPose?: PoseData;
  liveScores?: Partial<MLScores>;   // Scores may be partial during analysis
  detectedIssues?: PoseIssue[];
  analysisQuality: 'poor' | 'fair' | 'good' | 'excellent';
}

export default {};