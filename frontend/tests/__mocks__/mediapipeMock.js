class PoseMock {
  constructor() {
    this.onResults = null;
  }

  setOptions() {
    return Promise.resolve();
  }

  send() {
    if (this.onResults) {
      this.onResults({
        poseLandmarks: [
          { x: 0.5, y: 0.5, z: 0, visibility: 1 }, // nose
          { x: 0.6, y: 0.4, z: 0, visibility: 1 }, // left eye
          { x: 0.4, y: 0.4, z: 0, visibility: 1 }, // right eye
          // Add more landmarks as needed
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
  POSE_CONNECTIONS: [],
  POSE_LANDMARKS: {
    NOSE: 0,
    LEFT_EYE: 1,
    RIGHT_EYE: 2,
    // Add more landmark indices as needed
  },
}; 