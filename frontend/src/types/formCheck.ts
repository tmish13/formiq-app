// Supported in V1: 'squat'. Future: 'ohp', 'barbell_row'.
// TODO(OHP): add PostureV2_OHP pipeline before enabling overhead_press in UI
// TODO(Row): add PostureV2_Row pipeline before enabling barbell_row in UI
export type ExerciseType = 'squat' | 'deadlift' | 'bench_press' | 'overhead_press' | 'ohp' | 'barbell_row' | 'pullup' | 'pushup';

export type FormCheckStatus = 'pending' | 'analyzing' | 'processing' | 'completed' | 'failed';

export type FeedbackType = 'posture' | 'form' | 'technique' | 'safety' | 'general' | 'range_of_motion' | 'balance' | 'tempo';

export type FeedbackSeverity = 'low' | 'medium' | 'high';

export interface FeedbackItem {
  id?: number;
  form_check_id?: number;
  type: FeedbackType;
  severity: FeedbackSeverity;
  timestamp: number;
  description: string;
  message?: string;
  suggestions: string;
  joint_angles?: Record<string, number>;
  is_ai_generated?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface FormCheck {
  id: string;
  user_id: string;
  exercise_type?: ExerciseType;           // Optional — backend returns classified_exercise_slug instead
  classified_exercise_slug?: string;      // Backend field for exercise slug (e.g. "squat")
  exercise_name?: string;                 // Human-readable name from backend
  video_url: string;
  analysis_url?: string;
  score?: number;
  overall_score?: number;
  summary?: string;
  notes?: string;
  overall_feedback?: string;
  issues?: string[];
  status: FormCheckStatus;
  processing_time?: number;
  confidence_score?: number;
  form_metadata?: Record<string, any>;
  results?: Record<string, any>;
  thumbnail_url?: string;
  created_at: string;
  updated_at: string;
  feedback_items?: FeedbackItem[];
  // ML Model Scores (0-100 scale)
  posture_score?: number;        // Alignment and correctness of body positioning
  stability_score?: number;      // Balance and control during exercise
  depth_score?: number;          // Range of motion and movement depth
  ml_model_version?: string;     // Version of ML model used for analysis
  classification_confidence?: number; // Model confidence in exercise classification
  weight_kg?: number | null;     // User-entered weight for this session (kg)
  reps?: number | null;          // User-entered rep count for this session
}

export interface HighlightFrame {
  frame_index: number;
  timestamp_sec: number;
  knee_angle_left: number | null;
  knee_angle_right: number | null;
  hip_angle: number | null;
  depth_proxy: number;
}

export interface PostureV1TopSignal {
  name: string;
  value: number;
  z: number;
  direction: string;
  message_short: string;
}

export interface ComponentDetail {
  value: number | null;
  status: 'ok' | 'insufficient_data';
  reason: string | null;
}

export interface PostureV1Result {
  decision: 'good_form' | 'fault' | 'uncertain';
  prob_fault: number;
  confidence: number;
  posture_score: number;
  /** Qualitative score band (thresholds: 90/75/60 — must match backend compute_score_band). */
  score_band?: 'excellent' | 'good' | 'needs_work' | 'poor';
  component_scores: {
    trunk_control: number | null;
    knee_stability: number | null;
    hip_drive: number | null;
  };
  named_scores: {
    torso_stability_score: number | null;
    knee_symmetry_score: number | null;
    bottom_control_score: number | null;
    forward_lean_score: number | null;
  };
  /** Renamed aliases for named_scores — from the canonical pipeline API. */
  components?: {
    torso_stability: number | null;
    knee_symmetry: number | null;
    bottom_control: number | null;
    forward_lean: number | null;
  };
  top_signals: PostureV1TopSignal[];
  /** Top-signal feature names as a flat string list (e.g. "knee_asymmetry_mean"). */
  feature_insights?: string[];
  /** Pre-computed deepest-squat frame with joint angles for evidence overlay. */
  highlight_frame?: HighlightFrame;
  /** Optional: exercise type from backend (e.g. "squat"). */
  exercise_type?: string;
  /** Optional: support status flag (e.g. "not_supported" for unrecognized exercises). */
  status?: string;
  quality: {
    quality_flags: string[];
    quality_ok: boolean;
  };
  model: {
    name: string;
    version: string;
    threshold: number;
  };
  preprocessing: {
    original_frames: number;
    valid_frames: number;
    sequence_length: number;
  };
  component_visibility?: {
    trunk_control: number;
    knee_stability: number;
    hip_drive: number;
    forward_lean: number;
  };
  /** Score Integrity Fix: per-component detail (value + status). */
  component_details?: Record<string, ComponentDetail>;
  /** Components excluded from the weighted average due to low visibility. */
  score_exclusions?: string[];
  /** Renormalized weights used in the weighted average (sums to 1.0). */
  weights_used?: Record<string, number>;
}

export interface MLAnalysisResponse {
  ml_scores: {
    posture_score: number | null;
    stability_score: number | null;
    depth_score: number | null;
    confidence: number | null;
  };
  posture_v1: PostureV1Result;
  detected_issues: Array<{
    type: string;
    severity: string;
    description: string;
    confidence?: number;
    quality_flags?: string[];
  }>;
  decision: string;
  confidence: number;
  named_scores: PostureV1Result['named_scores'];
  component_scores: PostureV1Result['component_scores'];
  top_signals: PostureV1TopSignal[];
  highlight_frame?: HighlightFrame;
  calibrated_confidence?: { score: number; label: 'High' | 'Moderate' | 'Low' };
  delta?: {
    baseline_session: boolean;
    overall_score_delta?: number | null;
    personal_best?: boolean;
    torso_stability_delta?: number | null;
    knee_symmetry_delta?: number | null;
    bottom_control_delta?: number | null;
    forward_lean_delta?: number | null;
  };
  level?: {
    current_level: string | null;
    percent_to_next_level: number | null;
  };
  primary_limiter?: {
    key: string;
    persistent_limiter: boolean;
  };
  critical_frame_image_url?: string | null;
  critical_frame_angles?: {
    hip_angle?: number;
    knee_angle?: number;
  };
  /** Score Integrity Fix: per-component detail (value + status). */
  component_details?: Record<string, ComponentDetail>;
  /** Components excluded from the weighted average due to low visibility. */
  score_exclusions?: string[];
  /** Renormalized weights used in the weighted average (sums to 1.0). */
  weights_used?: Record<string, number>;
  /** AI-generated coaching paragraph (populated when RAG/OpenAI is enabled). */
  feedback_text?: string | null;
}

/**
 * Returns true only when a score is meaningful (non-null and non-zero).
 * Use this before displaying stability_score / depth_score from FormCheck,
 * which are NOT computed by PostureV1 and will always be null or 0 for squats.
 * posture_score and the named_scores (torso_stability etc.) ARE meaningful.
 */
export function isMeaningfulScore(value: number | null | undefined): value is number {
  return value != null && value > 0;
}

// ---------------------------------------------------------------------------
// Squat Training Session — frontend-only, localStorage-persisted
// FUTURE EXTENSIBILITY: SquatExerciseId will grow to 'squat' | 'ohp' | 'barbell_row'.
// SquatTrainingSession will generalize to TrainingSession<TComponents> with
// exercise-specific component maps. See squatSessions.ts for storage helpers.
//
// NOTE: Do NOT rename to ExerciseId — that name is used by features/training/types.ts
// for the full 58-exercise workout-mode union.
// ---------------------------------------------------------------------------

export type SquatExerciseId = 'squat';

export interface SquatTrainingSet {
  setIndex: number;
  reps: number;
  formScore?: number;
  primaryLimiter?: string;
}

export interface SquatTrainingSession {
  id: string;
  exercise: SquatExerciseId;
  date: string;           // ISO string
  workingWeight: number;  // lbs
  overallScore: number;   // 0–100
  components: {
    torsoStability: number;
    kneeSymmetry: number;
    bottomControl: number;
    forwardLean: number;
  };
  primaryLimiter: string;
  notes?: string;
  sets: SquatTrainingSet[];
}

export interface FormCheckResponse {
  id: string;
  video_url: string;
  exercise_id: string;
  user_id: string;
  status: 'pending' | 'processing' | 'completed';
  score?: number;
  overall_feedback?: string;
  analysis_url?: string;
  created_at: string;
  updated_at?: string;
  // ML Model Scores (0-100 scale)
  posture_score?: number;
  stability_score?: number;
  depth_score?: number;
  ml_model_version?: string;
  classification_confidence?: number;
} 