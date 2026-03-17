// Workout Mode — canonical data model.
// Standardized to lb throughout UI.

export type Unit = "lb";

export type Goal = "strength" | "hypertrophy" | "general";

export type LoadType =
  | "barbell_plates"
  | "machine_stack"
  | "machine_plate_loaded"
  | "dumbbell_pair"
  | "kettlebell"
  | "cable"
  | "fixed";

/**
 * Equipment type — intentionally small set.
 * Determines load increment defaults and display labels.
 */
export type EquipmentType =
  | "barbell"
  | "dumbbell"
  | "cable_stack"
  | "machine_plate_loaded"
  | "machine_selectorized"
  | "smith"
  | "bodyweight"
  | "weighted_bodyweight"
  | "other";

export type ExerciseId =
  | "barbell_back_squat"
  | "barbell_bench_press"
  | "barbell_overhead_press"
  | "barbell_row"
  | "deadlift"
  | "lat_pulldown"
  | "seated_cable_row"
  | "machine_chest_press"
  | "leg_press"
  | "leg_extension"
  | "leg_curl"
  | "dumbbell_bench_press"
  | "dumbbell_shoulder_press"
  | "dumbbell_row"
  | "bicep_curl"
  | "tricep_pushdown"
  | "calf_raise"
  | "pull_up"
  | "dip"
  | "smith_squat"
  | "hack_squat"
  | "hip_thrust"
  | "rdl"
  | "incline_bench"
  | "lateral_raise"
  | "rear_delt_fly"
  | "chest_fly"
  | "cable_curl"
  | "hammer_curl"
  | "skullcrusher"
  | "split_squat"
  | "step_up"
  | "row_machine"
  | "t_bar_row"
  | "pec_deck"
  | "ab_crunch_machine"
  | "barbell_front_squat"
  | "barbell_curl"
  | "goblet_squat"
  | "dumbbell_rdl"
  | "cable_lateral_raise"
  | "cable_overhead_tricep"
  | "face_pull"
  | "smith_bench_press"
  | "smith_incline_press"
  | "smith_ohp"
  | "smith_rdl"
  | "smith_split_squat"
  | "smith_hip_thrust"
  | "smith_calf_raise"
  | "plate_loaded_chest_press"
  | "plate_loaded_row"
  | "plate_loaded_pulldown"
  | "chin_up"
  | "push_up"
  | "bodyweight_squat"
  | "inverted_row"
  | "hanging_leg_raise"
  | "adductor_machine"
  | "abductor_machine"
  | "machine_curl"
  | "machine_tricep_extension"
  | "machine_shoulder_press"
  | "assisted_pull_up_dip";

export interface Exercise {
  id: ExerciseId;
  name: string;
  primaryMuscles: string[];
  movementPattern?: string;
  defaultLoadType: LoadType;
  /** Smallest weight step for this exercise. */
  defaultIncrementLb: number;
  /** Rep range intent — never a single "target reps" value. */
  defaultRepIntent: { min: number; max: number };
  /** Equipment types this exercise can be performed with. */
  allowedEquipment: EquipmentType[];
}

export type GymChainId =
  | "club_sport"
  | "twenty_four_hour"
  | "fitness_19"
  | "private_gym"
  | "other";

export interface Gym {
  id: string;
  name: string;
  isDefault?: boolean;
}

export interface EquipmentProfile {
  id: string;
  /** Display name — derived as "brand • TypeLabel" or nickname if set. */
  name: string;
  /** New field: equipment type for increment defaults and display. */
  type: EquipmentType;
  incrementLb: number;
  brand?: string;
  notes?: string;
  isDefault?: boolean;
  // Legacy fields — kept optional for backward compat with stored data.
  chainId?: GymChainId;
  exerciseId?: ExerciseId;
  loadType?: LoadType;
  gymId?: string;
  nickname?: string;
}

export type SetType = "warmup" | "working" | "backoff";

export interface SetLog {
  id: string;
  sessionId: string;
  exerciseId: ExerciseId;
  equipmentProfileId?: string;
  setIndex: number;
  setType: SetType;
  weightLb: number;
  reps: number;
  /** Required on working sets for engine; optional on warmups/backoffs. */
  rir?: number;
  createdAt: string;
  /** Optional; never used to override next-set recommendations. */
  formScore?: number;
}

export interface WorkoutSession {
  id: string;
  startedAt: string;
  goal: Goal;
  chainId?: GymChainId;
  gymId?: string;
  title?: string;
}

export type RecommendationAction = "increase" | "hold" | "reduce" | "stop";

/** Whether the lifter should continue the exercise, wrap it up, or has reached their target. */
export type ExerciseStatus = "continue" | "optional" | "finish";

/** Overall fatigue trend derived from RIR trajectory across working sets. */
export type FatigueSignal = "normal" | "rising" | "high";

export interface NextSetRecommendation {
  action: RecommendationAction;
  nextWeightLb: number;
  nextRepsRange: { min: number; max: number };
  restSeconds?: number;
  reasons: string[];
  /** How many working sets have been completed this exercise. */
  setsCompleted: number;
  /** Goal-appropriate working set target. */
  setsRecommended: number;
  /** Whether to keep going, wrap up, or stop. */
  exerciseStatus: ExerciseStatus;
  /** Derived fatigue trend across working sets. */
  fatigueSignal: FatigueSignal;
  /** Human-readable coaching message (undefined when nothing to say). */
  statusMessage?: string;
  debug?: {
    lastWorkingSetRir?: number;
    prevWorkingSetRir?: number;
    lastWorkingSetWeight?: number;
    increment?: number;
  };
}
