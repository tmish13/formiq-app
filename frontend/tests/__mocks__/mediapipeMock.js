class PoseMock {
  constructor() {
    this.onResults = null;
  }

  setOptions(options) {
    return Promise.resolve();
  }

  send() {
    if (this.onResults) {
      this.onResults({
        poseLandmarks: [
          // Face landmarks
          { x: 0.5, y: 0.5, z: 0, visibility: 1 }, // nose
          { x: 0.6, y: 0.4, z: 0, visibility: 1 }, // left eye inner
          { x: 0.65, y: 0.4, z: 0, visibility: 1 }, // left eye
          { x: 0.7, y: 0.4, z: 0, visibility: 1 }, // left eye outer
          { x: 0.4, y: 0.4, z: 0, visibility: 1 }, // right eye inner
          { x: 0.35, y: 0.4, z: 0, visibility: 1 }, // right eye
          { x: 0.3, y: 0.4, z: 0, visibility: 1 }, // right eye outer
          { x: 0.75, y: 0.45, z: 0, visibility: 1 }, // left ear
          { x: 0.25, y: 0.45, z: 0, visibility: 1 }, // right ear
          { x: 0.6, y: 0.5, z: 0, visibility: 1 }, // mouth left
          { x: 0.4, y: 0.5, z: 0, visibility: 1 }, // mouth right

          // Upper body landmarks
          { x: 0.3, y: 0.6, z: 0, visibility: 1 }, // left shoulder
          { x: 0.7, y: 0.6, z: 0, visibility: 1 }, // right shoulder
          { x: 0.2, y: 0.7, z: 0, visibility: 1 }, // left elbow
          { x: 0.8, y: 0.7, z: 0, visibility: 1 }, // right elbow
          { x: 0.1, y: 0.8, z: 0, visibility: 1 }, // left wrist
          { x: 0.9, y: 0.8, z: 0, visibility: 1 }, // right wrist

          // Lower body landmarks
          { x: 0.3, y: 0.8, z: 0, visibility: 1 }, // left hip
          { x: 0.7, y: 0.8, z: 0, visibility: 1 }, // right hip
          { x: 0.3, y: 0.9, z: 0, visibility: 1 }, // left knee
          { x: 0.7, y: 0.9, z: 0, visibility: 1 }, // right knee
          { x: 0.3, y: 1.0, z: 0, visibility: 1 }, // left ankle
          { x: 0.7, y: 1.0, z: 0, visibility: 1 }, // right ankle

          // Feet landmarks
          { x: 0.25, y: 1.05, z: 0, visibility: 1 }, // left heel
          { x: 0.75, y: 1.05, z: 0, visibility: 1 }, // right heel
          { x: 0.35, y: 1.1, z: 0, visibility: 1 }, // left foot index
          { x: 0.65, y: 1.1, z: 0, visibility: 1 }  // right foot index
        ],
        image: {
          width: 640,
          height: 480,
        },
      });
    }
    return Promise.resolve();
  }

  close() {
    return Promise.resolve();
  }
}

module.exports = {
  Pose: PoseMock,
  POSE_CONNECTIONS: [
    // Face connections
    [0, 1], [1, 2], [2, 3], [3, 7], // left eye
    [0, 4], [4, 5], [5, 6], [6, 8], // right eye
    [9, 10], // mouth
    
    // Upper body connections
    [11, 12], // shoulders
    [11, 13], [13, 15], // left arm
    [12, 14], [14, 16], // right arm
    
    // Lower body connections
    [11, 17], [12, 18], // shoulders to hips
    [17, 18], // hips
    [17, 19], [19, 21], // left leg
    [18, 20], [20, 22], // right leg
    
    // Feet connections
    [21, 23], [23, 25], // left foot
    [22, 24], [24, 26]  // right foot
  ],
  POSE_LANDMARKS: {
    NOSE: 0,
    LEFT_EYE_INNER: 1,
    LEFT_EYE: 2,
    LEFT_EYE_OUTER: 3,
    RIGHT_EYE_INNER: 4,
    RIGHT_EYE: 5,
    RIGHT_EYE_OUTER: 6,
    LEFT_EAR: 7,
    RIGHT_EAR: 8,
    MOUTH_LEFT: 9,
    MOUTH_RIGHT: 10,
    LEFT_SHOULDER: 11,
    RIGHT_SHOULDER: 12,
    LEFT_ELBOW: 13,
    RIGHT_ELBOW: 14,
    LEFT_WRIST: 15,
    RIGHT_WRIST: 16,
    LEFT_HIP: 17,
    RIGHT_HIP: 18,
    LEFT_KNEE: 19,
    RIGHT_KNEE: 20,
    LEFT_ANKLE: 21,
    RIGHT_ANKLE: 22,
    LEFT_HEEL: 23,
    RIGHT_HEEL: 24,
    LEFT_FOOT_INDEX: 25,
    RIGHT_FOOT_INDEX: 26
  },
}; 