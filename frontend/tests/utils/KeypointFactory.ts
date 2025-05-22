import * as poseDetection from '@tensorflow-models/pose-detection';

/**
 * Factory for generating realistic pose keypoint data for testing
 * Used by pose analysis components and services for consistent test data
 */

// Interface for a single keypoint
export interface Keypoint {
  x: number;
  y: number;
  z?: number;
  score?: number;
  name?: string;
}

// Interface for a pose containing multiple keypoints
export interface Pose {
  keypoints: Keypoint[];
  score?: number;
}

// Standard keypoint names in TensorFlow MoveNet/PoseNet format
export enum KeypointName {
  NOSE = 'nose',
  LEFT_EYE = 'left_eye',
  RIGHT_EYE = 'right_eye',
  LEFT_EAR = 'left_ear',
  RIGHT_EAR = 'right_ear',
  LEFT_SHOULDER = 'left_shoulder',
  RIGHT_SHOULDER = 'right_shoulder',
  LEFT_ELBOW = 'left_elbow',
  RIGHT_ELBOW = 'right_elbow',
  LEFT_WRIST = 'left_wrist',
  RIGHT_WRIST = 'right_wrist',
  LEFT_HIP = 'left_hip',
  RIGHT_HIP = 'right_hip',
  LEFT_KNEE = 'left_knee',
  RIGHT_KNEE = 'right_knee',
  LEFT_ANKLE = 'left_ankle',
  RIGHT_ANKLE = 'right_ankle'
}

/**
 * Create a single keypoint with standardized properties
 */
export const createKeypoint = (
  name: KeypointName,
  x: number,
  y: number,
  score = 0.9
): Keypoint => ({
  x,
  y,
  score,
  name
});

/**
 * Create a complete pose with all required keypoints
 * Can be customized with specific keypoint positions
 */
export const createPose = (
  customKeypoints: Partial<Record<KeypointName, Keypoint>> = {},
  score = 0.85
): Pose => {
  // Default keypoints in a "neutral" pose (standing)
  const defaultKeypoints: Record<KeypointName, Keypoint> = {
    [KeypointName.NOSE]: createKeypoint(KeypointName.NOSE, 320, 100),
    [KeypointName.LEFT_EYE]: createKeypoint(KeypointName.LEFT_EYE, 330, 95),
    [KeypointName.RIGHT_EYE]: createKeypoint(KeypointName.RIGHT_EYE, 310, 95),
    [KeypointName.LEFT_EAR]: createKeypoint(KeypointName.LEFT_EAR, 340, 100),
    [KeypointName.RIGHT_EAR]: createKeypoint(KeypointName.RIGHT_EAR, 300, 100),
    [KeypointName.LEFT_SHOULDER]: createKeypoint(KeypointName.LEFT_SHOULDER, 350, 150),
    [KeypointName.RIGHT_SHOULDER]: createKeypoint(KeypointName.RIGHT_SHOULDER, 290, 150),
    [KeypointName.LEFT_ELBOW]: createKeypoint(KeypointName.LEFT_ELBOW, 360, 200),
    [KeypointName.RIGHT_ELBOW]: createKeypoint(KeypointName.RIGHT_ELBOW, 280, 200),
    [KeypointName.LEFT_WRIST]: createKeypoint(KeypointName.LEFT_WRIST, 370, 250),
    [KeypointName.RIGHT_WRIST]: createKeypoint(KeypointName.RIGHT_WRIST, 270, 250),
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 340, 250),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 300, 250),
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 340, 320),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 300, 320),
    [KeypointName.LEFT_ANKLE]: createKeypoint(KeypointName.LEFT_ANKLE, 340, 390),
    [KeypointName.RIGHT_ANKLE]: createKeypoint(KeypointName.RIGHT_ANKLE, 300, 390)
  };

  // Merge default keypoints with custom keypoints
  const mergedKeypoints = { ...defaultKeypoints, ...customKeypoints };

  // Convert to array format expected by pose analysis
  const keypointsArray = Object.values(mergedKeypoints);

  return {
    keypoints: keypointsArray,
    score
  };
};

/**
 * Create a pose representing good squat form
 * Deep bend in knees, straight back, feet shoulder-width apart
 */
export const createGoodSquat = (score = 0.9): Pose => {
  return createPose({
    // Move the knees forward and down for a squat position
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 350, 300),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 290, 300),
    // Lower the hips for proper depth
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 340, 220),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 300, 220),
    // Ankles stay in place but adjust slightly
    [KeypointName.LEFT_ANKLE]: createKeypoint(KeypointName.LEFT_ANKLE, 360, 380),
    [KeypointName.RIGHT_ANKLE]: createKeypoint(KeypointName.RIGHT_ANKLE, 280, 380),
  }, score);
};

/**
 * Create a pose representing bad squat form
 * Knees caving in, not deep enough, leaning forward
 */
export const createBadSquat = (score = 0.9): Pose => {
  return createPose({
    // Knees caving in (bad form)
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 320, 280),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 320, 280),
    // Not low enough
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 340, 200),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 300, 200),
    // Leaning forward (rounded back)
    [KeypointName.LEFT_SHOULDER]: createKeypoint(KeypointName.LEFT_SHOULDER, 350, 180),
    [KeypointName.RIGHT_SHOULDER]: createKeypoint(KeypointName.RIGHT_SHOULDER, 290, 180),
  }, score);
};

/**
 * Create a pose representing good pushup form
 * Straight body, proper elbow angle, head aligned
 */
export const createGoodPushup = (score = 0.9): Pose => {
  return createPose({
    // Lower body position in straight plank
    [KeypointName.NOSE]: createKeypoint(KeypointName.NOSE, 150, 200),
    [KeypointName.LEFT_SHOULDER]: createKeypoint(KeypointName.LEFT_SHOULDER, 180, 200),
    [KeypointName.RIGHT_SHOULDER]: createKeypoint(KeypointName.RIGHT_SHOULDER, 120, 200),
    [KeypointName.LEFT_ELBOW]: createKeypoint(KeypointName.LEFT_ELBOW, 220, 230),
    [KeypointName.RIGHT_ELBOW]: createKeypoint(KeypointName.RIGHT_ELBOW, 80, 230),
    [KeypointName.LEFT_WRIST]: createKeypoint(KeypointName.LEFT_WRIST, 260, 200),
    [KeypointName.RIGHT_WRIST]: createKeypoint(KeypointName.RIGHT_WRIST, 40, 200),
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 320, 200),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 280, 200),
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 380, 200),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 220, 200),
    [KeypointName.LEFT_ANKLE]: createKeypoint(KeypointName.LEFT_ANKLE, 440, 200),
    [KeypointName.RIGHT_ANKLE]: createKeypoint(KeypointName.RIGHT_ANKLE, 160, 200),
  }, score);
};

/**
 * Create a pose representing bad pushup form
 * Sagging hips, elbows flaring, improper head position
 */
export const createBadPushup = (score = 0.9): Pose => {
  return createPose({
    // Sagging hips
    [KeypointName.NOSE]: createKeypoint(KeypointName.NOSE, 150, 180),
    [KeypointName.LEFT_SHOULDER]: createKeypoint(KeypointName.LEFT_SHOULDER, 180, 200),
    [KeypointName.RIGHT_SHOULDER]: createKeypoint(KeypointName.RIGHT_SHOULDER, 120, 200),
    // Elbows flaring outward
    [KeypointName.LEFT_ELBOW]: createKeypoint(KeypointName.LEFT_ELBOW, 230, 210),
    [KeypointName.RIGHT_ELBOW]: createKeypoint(KeypointName.RIGHT_ELBOW, 70, 210),
    [KeypointName.LEFT_WRIST]: createKeypoint(KeypointName.LEFT_WRIST, 260, 200),
    [KeypointName.RIGHT_WRIST]: createKeypoint(KeypointName.RIGHT_WRIST, 40, 200),
    // Hips sagging
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 320, 230),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 280, 230),
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 380, 220),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 220, 220),
    [KeypointName.LEFT_ANKLE]: createKeypoint(KeypointName.LEFT_ANKLE, 440, 200),
    [KeypointName.RIGHT_ANKLE]: createKeypoint(KeypointName.RIGHT_ANKLE, 160, 200),
  }, score);
};

/**
 * Create a pose representing good plank form
 * Straight body, engaged core, proper alignment
 */
export const createGoodPlank = (score = 0.9): Pose => {
  return createPose({
    // Straight line from head to heels
    [KeypointName.NOSE]: createKeypoint(KeypointName.NOSE, 150, 200),
    [KeypointName.LEFT_SHOULDER]: createKeypoint(KeypointName.LEFT_SHOULDER, 180, 200),
    [KeypointName.RIGHT_SHOULDER]: createKeypoint(KeypointName.RIGHT_SHOULDER, 120, 200),
    [KeypointName.LEFT_ELBOW]: createKeypoint(KeypointName.LEFT_ELBOW, 220, 250),
    [KeypointName.RIGHT_ELBOW]: createKeypoint(KeypointName.RIGHT_ELBOW, 80, 250),
    [KeypointName.LEFT_WRIST]: createKeypoint(KeypointName.LEFT_WRIST, 220, 300),
    [KeypointName.RIGHT_WRIST]: createKeypoint(KeypointName.RIGHT_WRIST, 80, 300),
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 320, 200),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 280, 200),
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 380, 200),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 220, 200),
    [KeypointName.LEFT_ANKLE]: createKeypoint(KeypointName.LEFT_ANKLE, 440, 200),
    [KeypointName.RIGHT_ANKLE]: createKeypoint(KeypointName.RIGHT_ANKLE, 160, 200),
  }, score);
};

/**
 * Create a pose representing bad plank form
 * Sagging hips, head dropping, poor shoulder position
 */
export const createBadPlank = (score = 0.9): Pose => {
  return createPose({
    // Head dropping
    [KeypointName.NOSE]: createKeypoint(KeypointName.NOSE, 150, 220),
    [KeypointName.LEFT_SHOULDER]: createKeypoint(KeypointName.LEFT_SHOULDER, 180, 200),
    [KeypointName.RIGHT_SHOULDER]: createKeypoint(KeypointName.RIGHT_SHOULDER, 120, 200),
    [KeypointName.LEFT_ELBOW]: createKeypoint(KeypointName.LEFT_ELBOW, 220, 250),
    [KeypointName.RIGHT_ELBOW]: createKeypoint(KeypointName.RIGHT_ELBOW, 80, 250),
    [KeypointName.LEFT_WRIST]: createKeypoint(KeypointName.LEFT_WRIST, 220, 300),
    [KeypointName.RIGHT_WRIST]: createKeypoint(KeypointName.RIGHT_WRIST, 80, 300),
    // Sagging hips
    [KeypointName.LEFT_HIP]: createKeypoint(KeypointName.LEFT_HIP, 320, 230),
    [KeypointName.RIGHT_HIP]: createKeypoint(KeypointName.RIGHT_HIP, 280, 230),
    [KeypointName.LEFT_KNEE]: createKeypoint(KeypointName.LEFT_KNEE, 380, 210),
    [KeypointName.RIGHT_KNEE]: createKeypoint(KeypointName.RIGHT_KNEE, 220, 210),
    [KeypointName.LEFT_ANKLE]: createKeypoint(KeypointName.LEFT_ANKLE, 440, 200),
    [KeypointName.RIGHT_ANKLE]: createKeypoint(KeypointName.RIGHT_ANKLE, 160, 200),
  }, score);
};

/**
 * Create a sequence of poses for testing over time
 * @param poseCreator Function that creates a pose
 * @param count Number of poses to create
 * @param variation How much to vary keypoints between frames (0-1)
 */
export const createPoseSequence = (
  poseCreator: ((score: number) => Pose) = (score: number) => createPose({}, score),
  count = 10,
  variation = 0.05
): Pose[] => {
  return Array.from({ length: count }, (_, i) => {
    const baseScore = 0.8 + (Math.random() * 0.15);
    const pose = poseCreator(baseScore);
    
    // Add slight variations to each keypoint for realism
    return {
      ...pose,
      keypoints: pose.keypoints.map(kp => ({
        ...kp,
        x: kp.x + (Math.random() * variation * 10) - (variation * 5),
        y: kp.y + (Math.random() * variation * 10) - (variation * 5),
        score: Math.min(1, Math.max(0.5, (kp.score || 0.9) + (Math.random() * variation) - (variation / 2)))
      }))
    };
  });
};

/**
 * Generate analysis results from a pose or sequence of poses
 * @param pose Single pose or array of poses to analyze
 * @param exerciseType Type of exercise being performed
 * @param score Overall form score (0-100)
 * @returns Analysis results with feedback
 */
export const createAnalysisResults = (
  pose: Pose | Pose[],
  exerciseType: 'squat' | 'pushup' | 'plank' = 'squat',
  score = 75
) => {
  // Determine if the form is good based on a score threshold
  const isGoodForm = score > 80;
  
  // Feedback based on exercise type and score
  const feedbackMap = {
    squat: {
      good: [
        { type: 'success', text: 'Good depth on your squat' },
        { type: 'success', text: 'Knees tracking over toes properly' },
        { type: 'info', text: 'Weight is properly distributed' }
      ],
      bad: [
        { type: 'warning', text: 'Knees are caving inward' },
        { type: 'error', text: 'Not reaching full depth' },
        { type: 'warning', text: 'Back is not straight' }
      ]
    },
    pushup: {
      good: [
        { type: 'success', text: 'Body forms a straight line' },
        { type: 'success', text: 'Elbows tucked at proper angle' },
        { type: 'info', text: 'Good depth in the movement' }
      ],
      bad: [
        { type: 'warning', text: 'Elbows flaring out too wide' },
        { type: 'error', text: 'Hips sagging' },
        { type: 'warning', text: 'Head position not aligned with spine' }
      ]
    },
    plank: {
      good: [
        { type: 'success', text: 'Perfect straight body alignment' },
        { type: 'success', text: 'Core properly engaged' },
        { type: 'info', text: 'Shoulders stacked over elbows' }
      ],
      bad: [
        { type: 'warning', text: 'Hips are too high' },
        { type: 'error', text: 'Hips are sagging' },
        { type: 'warning', text: 'Neck/head not in neutral position' }
      ]
    }
  };
  
  // Select feedback based on exercise type and form quality
  const feedbackItems = isGoodForm 
    ? feedbackMap[exerciseType].good
    : feedbackMap[exerciseType].bad;
  
  // Create angleData based on exercise type
  const angleData: Record<string, any> = {};
  
  if (exerciseType === 'squat') {
    angleData.leftKnee = { angle: isGoodForm ? 90 : 120, isCorrect: isGoodForm };
    angleData.rightKnee = { angle: isGoodForm ? 92 : 115, isCorrect: isGoodForm };
    angleData.backAlignment = { angle: isGoodForm ? 5 : 15, isCorrect: isGoodForm };
  } else if (exerciseType === 'pushup') {
    angleData.leftElbow = { angle: isGoodForm ? 90 : 60, isCorrect: isGoodForm };
    angleData.rightElbow = { angle: isGoodForm ? 92 : 58, isCorrect: isGoodForm };
    angleData.bodyAlignment = { angle: isGoodForm ? 3 : 12, isCorrect: isGoodForm };
  } else if (exerciseType === 'plank') {
    angleData.shoulderAlignment = { angle: isGoodForm ? 90 : 75, isCorrect: isGoodForm };
    angleData.hipAlignment = { angle: isGoodForm ? 178 : 165, isCorrect: isGoodForm };
    angleData.legAlignment = { angle: isGoodForm ? 180 : 172, isCorrect: isGoodForm };
  }
  
  return {
    score,
    exerciseType,
    feedbackItems,
    angles: angleData,
    timestamp: Date.now(),
    poses: Array.isArray(pose) ? pose : [pose],
    frameCounts: {
      total: Array.isArray(pose) ? pose.length : 1,
      good: isGoodForm ? (Array.isArray(pose) ? Math.floor(pose.length * 0.85) : 1) : 0,
      bad: !isGoodForm ? (Array.isArray(pose) ? Math.floor(pose.length * 0.7) : 1) : 0,
    }
  };
};

/**
 * Converts an analysis result to an API response format
 * For testing API response handlers
 */
export const createAnalysisApiResponse = (
  analysisResult = createAnalysisResults(createGoodSquat(), 'squat', 85),
  userId = '1',
  videoUrl = 'https://example.com/exercise-video.mp4'
) => {
  return {
    id: Math.floor(Math.random() * 1000).toString(),
    user_id: userId,
    exercise_type: analysisResult.exerciseType,
    video_url: videoUrl,
    score: analysisResult.score,
    feedback: analysisResult.feedbackItems
      .filter(item => item.type === 'success' || item.type === 'error')
      .map(item => item.text)
      .join('. '),
    issues: analysisResult.feedbackItems
      .filter(item => item.type === 'warning' || item.type === 'error')
      .map(item => item.text),
    created_at: new Date().toISOString(),
    status: 'completed',
    analysis_data: {
      angles: analysisResult.angles,
      frames: analysisResult.poses.length,
      goodFrames: analysisResult.frameCounts.good,
      badFrames: analysisResult.frameCounts.bad
    }
  };
}; 