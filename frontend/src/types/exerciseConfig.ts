/**
 * TypeScript interfaces for exercise configurations
 */

/**
 * Joint angle rule with min, max, ideal angles and tolerance
 */
export interface JointAngleRule {
  min_angle: number;
  max_angle: number;
  ideal_angle: number;
  tolerance: number;
}

/**
 * Condition that triggers a phase transition
 */
export interface TriggerCondition {
  joint: string;
  condition: string;
  value: number;
  comparator: string;
}

/**
 * Movement phase with description and triggers
 */
export interface MovementPhase {
  description: string;
  triggers: {
    next: TriggerCondition[];
    previous: TriggerCondition[];
  };
}

/**
 * Feedback template for rule violations
 */
export interface FeedbackTemplate {
  message: string;
  severity: 'low' | 'medium' | 'high';
  type: 'form' | 'alignment' | 'range' | 'tempo' | 'safety';
  details?: string;
}

/**
 * Rules for joints in a specific phase
 */
export interface PhaseJointRules {
  angles: Record<string, JointAngleRule>;
}

/**
 * All joint angle rules across different phases
 */
export interface JointAngleRules {
  phases: Record<string, PhaseJointRules>;
  joints: string[];
}

/**
 * Metadata for exercise classification
 */
export interface ClassificationMetadata {
  keypoints: string[];
  frame_count: number;
  features: Record<string, any>;
}

/**
 * Base exercise configuration
 */
export interface ExerciseConfigBase {
  name: string;
  version: number;
  is_active: boolean;
  joint_angle_rules: JointAngleRules;
  movement_phases: Record<string, MovementPhase>;
  feedback_templates: Record<string, FeedbackTemplate>;
  classification_metadata?: ClassificationMetadata;
}

/**
 * Exercise configuration in database with ID and timestamps
 */
export interface ExerciseConfig extends ExerciseConfigBase {
  id: string;
  exercise_id: string;
  created_at: string;
  updated_at: string;
}

/**
 * Exercise configuration with exercise details
 */
export interface ExerciseConfigWithExercise extends ExerciseConfig {
  exercise_name: string;
}

/**
 * Data needed to create an exercise configuration
 */
export interface ExerciseConfigCreate extends ExerciseConfigBase {
  exercise_id: string;
}

/**
 * Data for updating an exercise configuration
 */
export interface ExerciseConfigUpdate {
  name?: string;
  version?: number;
  is_active?: boolean;
  joint_angle_rules?: JointAngleRules;
  movement_phases?: Record<string, MovementPhase>;
  feedback_templates?: Record<string, FeedbackTemplate>;
  classification_metadata?: ClassificationMetadata;
} 