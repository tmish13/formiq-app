import { Keypoint } from '@tensorflow-models/pose-detection';
import { JointAngle, FormValidationResult } from './types';

export enum ExerciseType {
  SQUAT = 'squat',
  PUSHUP = 'pushup',
  PLANK = 'plank',
  BENCH_PRESS = 'benchPress',
  DEADLIFT = 'deadlift',
  LAT_PULLDOWN = 'latPulldown',
  BICEP_CURL = 'bicepCurl'
}

export interface FormCheckRule {
  name: string;
  description: string;
}

export interface ExerciseConfig {
  requiredKeypoints: string[];
  minConfidence: number;
  targetAngles: {
    [key: string]: {
      min: number;
      max: number;
    };
  };
  movementPhases: {
    [key: string]: {
      startAngle: number;
      endAngle: number;
      duration: number;
    };
  };
  formChecks: FormCheckRule[];
}

export const exerciseConfigs: Record<ExerciseType, ExerciseConfig> = {
  [ExerciseType.SQUAT]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_hip',
      'left_knee',
      'left_ankle',
      'right_shoulder',
      'right_hip',
      'right_knee',
      'right_ankle'
    ],
    minConfidence: 0.5,
    targetAngles: {
      knee: {
        min: 90,
        max: 120
      },
      hip: {
        min: 70,
        max: 100
      },
      back: {
        min: 160,
        max: 180
      }
    },
    movementPhases: {
      eccentric: {
        startAngle: 180,
        endAngle: 90,
        duration: 3
      },
      concentric: {
        startAngle: 90,
        endAngle: 180,
        duration: 2
      }
    },
    formChecks: [
      {
        name: 'Knee Position',
        description: 'Keep knees over toes'
      },
      {
        name: 'Back Position',
        description: 'Keep back straight'
      }
    ]
  },
  [ExerciseType.PUSHUP]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_elbow',
      'left_wrist',
      'right_shoulder',
      'right_elbow',
      'right_wrist'
    ],
    minConfidence: 0.5,
    targetAngles: {
      elbow: {
        min: 80,
        max: 100
      },
      shoulder: {
        min: 0,
        max: 30
      }
    },
    movementPhases: {
      eccentric: {
        startAngle: 180,
        endAngle: 90,
        duration: 2
      },
      concentric: {
        startAngle: 90,
        endAngle: 180,
        duration: 1
      }
    },
    formChecks: [
      {
        name: 'Elbow Position',
        description: 'Keep elbows at 45-degree angle'
      },
      {
        name: 'Core Engagement',
        description: 'Keep core tight'
      }
    ]
  },
  [ExerciseType.PLANK]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_hip',
      'left_ankle',
      'right_shoulder',
      'right_hip',
      'right_ankle'
    ],
    minConfidence: 0.5,
    targetAngles: {
      back: {
        min: 170,
        max: 180
      },
      hip: {
        min: 170,
        max: 180
      }
    },
    movementPhases: {
      hold: {
        startAngle: 180,
        endAngle: 180,
        duration: 60
      }
    },
    formChecks: [
      {
        name: 'Back Position',
        description: 'Keep back straight and aligned'
      },
      {
        name: 'Hip Position',
        description: 'Keep hips level with shoulders'
      }
    ]
  },
  [ExerciseType.BENCH_PRESS]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_elbow',
      'left_wrist',
      'right_shoulder',
      'right_elbow',
      'right_wrist'
    ],
    minConfidence: 0.5,
    targetAngles: {
      elbow: {
        min: 80,
        max: 100
      },
      shoulder: {
        min: 0,
        max: 30
      }
    },
    movementPhases: {
      eccentric: {
        startAngle: 180,
        endAngle: 90,
        duration: 2
      },
      concentric: {
        startAngle: 90,
        endAngle: 180,
        duration: 1
      }
    },
    formChecks: []
  },
  [ExerciseType.DEADLIFT]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_hip',
      'left_knee',
      'left_ankle',
      'right_shoulder',
      'right_hip',
      'right_knee',
      'right_ankle'
    ],
    minConfidence: 0.5,
    targetAngles: {
      back: {
        min: 160,
        max: 180
      },
      hip: {
        min: 70,
        max: 100
      },
      knee: {
        min: 90,
        max: 120
      }
    },
    movementPhases: {
      eccentric: {
        startAngle: 180,
        endAngle: 90,
        duration: 3
      },
      concentric: {
        startAngle: 90,
        endAngle: 180,
        duration: 2
      }
    },
    formChecks: []
  },
  [ExerciseType.LAT_PULLDOWN]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_elbow',
      'left_wrist',
      'right_shoulder',
      'right_elbow',
      'right_wrist'
    ],
    minConfidence: 0.5,
    targetAngles: {
      elbow: {
        min: 80,
        max: 100
      },
      shoulder: {
        min: 0,
        max: 30
      }
    },
    movementPhases: {
      eccentric: {
        startAngle: 180,
        endAngle: 90,
        duration: 2
      },
      concentric: {
        startAngle: 90,
        endAngle: 180,
        duration: 1
      }
    },
    formChecks: []
  },
  [ExerciseType.BICEP_CURL]: {
    requiredKeypoints: [
      'left_shoulder',
      'left_elbow',
      'left_wrist',
      'right_shoulder',
      'right_elbow',
      'right_wrist'
    ],
    minConfidence: 0.5,
    targetAngles: {
      elbow: {
        min: 30,
        max: 50
      },
      shoulder: {
        min: 0,
        max: 30
      }
    },
    movementPhases: {
      eccentric: {
        startAngle: 30,
        endAngle: 180,
        duration: 2
      },
      concentric: {
        startAngle: 180,
        endAngle: 30,
        duration: 1
      }
    },
    formChecks: []
  }
} as const; 