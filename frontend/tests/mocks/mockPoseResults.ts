export const mockPoseResults = {
  poseLandmarks: [
    { x: 0.5, y: 0.5, z: 0, visibility: 0.9 }, // nose
    { x: 0.4, y: 0.5, z: 0, visibility: 0.9 }, // left_eye_inner
    { x: 0.3, y: 0.5, z: 0, visibility: 0.9 }, // left_eye
    { x: 0.2, y: 0.5, z: 0, visibility: 0.9 }, // left_eye_outer
    { x: 0.6, y: 0.5, z: 0, visibility: 0.9 }, // right_eye_inner
    { x: 0.7, y: 0.5, z: 0, visibility: 0.9 }, // right_eye
    { x: 0.8, y: 0.5, z: 0, visibility: 0.9 }, // right_eye_outer
    { x: 0.5, y: 0.6, z: 0, visibility: 0.9 }, // left_ear
    { x: 0.5, y: 0.6, z: 0, visibility: 0.9 }, // right_ear
    { x: 0.5, y: 0.7, z: 0, visibility: 0.9 }, // mouth_left
    { x: 0.5, y: 0.7, z: 0, visibility: 0.9 }, // mouth_right
    { x: 0.5, y: 0.8, z: 0, visibility: 0.9 }, // left_shoulder
    { x: 0.5, y: 0.8, z: 0, visibility: 0.9 }, // right_shoulder
    { x: 0.4, y: 0.9, z: 0, visibility: 0.9 }, // left_elbow
    { x: 0.6, y: 0.9, z: 0, visibility: 0.9 }, // right_elbow
    { x: 0.3, y: 1.0, z: 0, visibility: 0.9 }, // left_wrist
    { x: 0.7, y: 1.0, z: 0, visibility: 0.9 }, // right_wrist
    { x: 0.5, y: 1.1, z: 0, visibility: 0.9 }, // left_pinky
    { x: 0.5, y: 1.1, z: 0, visibility: 0.9 }, // right_pinky
    { x: 0.5, y: 1.1, z: 0, visibility: 0.9 }, // left_index
    { x: 0.5, y: 1.1, z: 0, visibility: 0.9 }, // right_index
    { x: 0.5, y: 1.1, z: 0, visibility: 0.9 }, // left_thumb
    { x: 0.5, y: 1.1, z: 0, visibility: 0.9 }, // right_thumb
    { x: 0.4, y: 1.2, z: 0, visibility: 0.9 }, // left_hip
    { x: 0.6, y: 1.2, z: 0, visibility: 0.9 }, // right_hip
    { x: 0.3, y: 1.3, z: 0, visibility: 0.9 }, // left_knee
    { x: 0.7, y: 1.3, z: 0, visibility: 0.9 }, // right_knee
    { x: 0.2, y: 1.4, z: 0, visibility: 0.9 }, // left_ankle
    { x: 0.8, y: 1.4, z: 0, visibility: 0.9 }, // right_ankle
    { x: 0.1, y: 1.5, z: 0, visibility: 0.9 }, // left_heel
    { x: 0.9, y: 1.5, z: 0, visibility: 0.9 }, // right_heel
    { x: 0.2, y: 1.6, z: 0, visibility: 0.9 }, // left_foot_index
    { x: 0.8, y: 1.6, z: 0, visibility: 0.9 }, // right_foot_index
  ],
  imageWidth: 640,
  imageHeight: 480
};

export const mockPoseDetection = {
  results: [{
    poseLandmarks: mockPoseResults.poseLandmarks,
    imageWidth: mockPoseResults.imageWidth,
    imageHeight: mockPoseResults.imageHeight
  }]
}; 