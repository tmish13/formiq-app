"""
Keypoint utility functions.

This module provides functions for processing and analyzing pose keypoints.
"""
import math
import numpy as np
from typing import Dict, List, Any, Tuple, Optional

# Keypoint indices for common pose estimation models (e.g., BlazePose, MoveNet)
KEYPOINT_DICT = {
    "nose": 0,
    "leftEye": 1,
    "rightEye": 2,
    "leftEar": 3,
    "rightEar": 4,
    "leftShoulder": 5,
    "rightShoulder": 6,
    "leftElbow": 7,
    "rightElbow": 8,
    "leftWrist": 9,
    "rightWrist": 10,
    "leftHip": 11,
    "rightHip": 12,
    "leftKnee": 13,
    "rightKnee": 14,
    "leftAnkle": 15,
    "rightAnkle": 16
}

# Define joint connections for angle calculation
JOINT_CONNECTIONS = {
    "leftElbow": ["leftShoulder", "leftElbow", "leftWrist"],
    "rightElbow": ["rightShoulder", "rightElbow", "rightWrist"],
    "leftShoulder": ["leftElbow", "leftShoulder", "leftHip"],
    "rightShoulder": ["rightElbow", "rightShoulder", "rightHip"],
    "leftHip": ["leftShoulder", "leftHip", "leftKnee"],
    "rightHip": ["rightShoulder", "rightHip", "rightKnee"],
    "leftKnee": ["leftHip", "leftKnee", "leftAnkle"],
    "rightKnee": ["rightHip", "rightKnee", "rightAnkle"],
    "leftAnkle": ["leftKnee", "leftAnkle", "leftHeel"],
    "rightAnkle": ["rightKnee", "rightAnkle", "rightHeel"],
    "neck": ["nose", "neck", "midHip"],
    "back": ["neck", "midHip", "midKnee"]
}

def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """
    Calculate the angle between three points.
    
    Args:
        a (np.ndarray): First point coordinates [x, y]
        b (np.ndarray): Middle point coordinates [x, y] (vertex)
        c (np.ndarray): Last point coordinates [x, y]
        
    Returns:
        float: Angle in degrees
    """
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)  # Ensure value is in valid range
    
    angle = np.arccos(cosine_angle)
    angle = np.degrees(angle)
    
    return angle

def get_keypoint_coordinates(keypoints: List[Dict[str, Any]], frame_idx: int = 0) -> Dict[str, np.ndarray]:
    """
    Extract keypoint coordinates from a frame.
    
    Args:
        keypoints (List[Dict[str, Any]]): Pose keypoints data
        frame_idx (int): Frame index to extract
        
    Returns:
        Dict[str, np.ndarray]: Dictionary mapping keypoint names to coordinates
    """
    coordinates = {}
    
    # Check if we have enough frames
    if frame_idx >= len(keypoints):
        return coordinates
    
    frame = keypoints[frame_idx]
    
    # Handle different keypoint formats
    if "keypoints" in frame:
        # Format: { keypoints: [ { position: { x, y }, name: "name", score: 0.9 }, ... ] }
        kps = frame["keypoints"]
        for kp in kps:
            if "name" in kp and "position" in kp:
                name = kp["name"]
                x = kp["position"]["x"]
                y = kp["position"]["y"]
                coordinates[name] = np.array([x, y])
    elif "pose" in frame and "keypoints" in frame["pose"]:
        # Format: { pose: { keypoints: [ { x, y, name, score }, ... ] } }
        kps = frame["pose"]["keypoints"]
        for kp in kps:
            if "name" in kp:
                name = kp["name"]
                x = kp["x"]
                y = kp["y"]
                coordinates[name] = np.array([x, y])
    
    return coordinates

def calculate_joint_angles(keypoints: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate joint angles from pose keypoints.
    
    Args:
        keypoints: List of pose keypoints with x, y, z coordinates
        
    Returns:
        Dict mapping joint names to angle values in degrees
    """
    # Extract keypoints as dictionary by name
    keypoints_dict = {}
    for kp in keypoints:
        if "name" in kp and "x" in kp and "y" in kp and kp.get("visibility", 0) > 0.5:
            keypoints_dict[kp["name"]] = (kp["x"], kp["y"])
    
    # Calculate joint angles
    angles = {}
    
    # Calculate hip angle (between shoulder, hip, and knee)
    if all(k in keypoints_dict for k in ["left_shoulder", "left_hip", "left_knee"]):
        angles["left_hip"] = _angle_between_points(
            keypoints_dict["left_shoulder"],
            keypoints_dict["left_hip"],
            keypoints_dict["left_knee"]
        )
        
    if all(k in keypoints_dict for k in ["right_shoulder", "right_hip", "right_knee"]):
        angles["right_hip"] = _angle_between_points(
            keypoints_dict["right_shoulder"],
            keypoints_dict["right_hip"],
            keypoints_dict["right_knee"]
        )
        
    # Calculate knee angle (between hip, knee, and ankle)
    if all(k in keypoints_dict for k in ["left_hip", "left_knee", "left_ankle"]):
        angles["left_knee"] = _angle_between_points(
            keypoints_dict["left_hip"],
            keypoints_dict["left_knee"],
            keypoints_dict["left_ankle"]
        )
        
    if all(k in keypoints_dict for k in ["right_hip", "right_knee", "right_ankle"]):
        angles["right_knee"] = _angle_between_points(
            keypoints_dict["right_hip"],
            keypoints_dict["right_knee"],
            keypoints_dict["right_ankle"]
        )
        
    # Calculate elbow angle (between shoulder, elbow, and wrist)
    if all(k in keypoints_dict for k in ["left_shoulder", "left_elbow", "left_wrist"]):
        angles["left_elbow"] = _angle_between_points(
            keypoints_dict["left_shoulder"],
            keypoints_dict["left_elbow"],
            keypoints_dict["left_wrist"]
        )
        
    if all(k in keypoints_dict for k in ["right_shoulder", "right_elbow", "right_wrist"]):
        angles["right_elbow"] = _angle_between_points(
            keypoints_dict["right_shoulder"],
            keypoints_dict["right_elbow"],
            keypoints_dict["right_wrist"]
        )
        
    # Calculate average angles (left and right)
    if "left_hip" in angles and "right_hip" in angles:
        angles["hip"] = (angles["left_hip"] + angles["right_hip"]) / 2
        
    if "left_knee" in angles and "right_knee" in angles:
        angles["knee"] = (angles["left_knee"] + angles["right_knee"]) / 2
        
    if "left_elbow" in angles and "right_elbow" in angles:
        angles["elbow"] = (angles["left_elbow"] + angles["right_elbow"]) / 2
        
    return angles

def _angle_between_points(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    """
    Calculate angle between three points in degrees.
    
    Args:
        p1: First point (x, y)
        p2: Second point (x, y) - the vertex
        p3: Third point (x, y)
        
    Returns:
        Angle in degrees
    """
    # Convert to numpy arrays
    p1 = np.array(p1)
    p2 = np.array(p2)
    p3 = np.array(p3)
    
    # Calculate vectors
    v1 = p1 - p2
    v2 = p3 - p2
    
    # Calculate angle
    cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine_angle))
    
    return angle

def get_keypoint_visibility(keypoints: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Get visibility scores for each keypoint.
    
    Args:
        keypoints: List of pose keypoints
        
    Returns:
        Dict mapping keypoint names to visibility scores
    """
    return {kp["name"]: kp.get("visibility", 0) for kp in keypoints if "name" in kp}

def calculate_pose_confidence(keypoints: List[Dict[str, Any]]) -> float:
    """
    Calculate overall pose confidence score.
    
    Args:
        keypoints: List of pose keypoints
        
    Returns:
        Confidence score from 0 to 1
    """
    if not keypoints:
        return 0.0
        
    visibility_scores = [kp.get("visibility", 0) for kp in keypoints if "visibility" in kp]
    if not visibility_scores:
        return 0.0
        
    return sum(visibility_scores) / len(visibility_scores)

def get_body_side_keypoints(keypoints: List[Dict[str, Any]], side: str = "right") -> List[Dict[str, Any]]:
    """
    Filter keypoints for a specific body side.
    
    Args:
        keypoints: List of pose keypoints
        side: Body side to filter for ("left" or "right")
        
    Returns:
        List of keypoints for the specified side
    """
    prefix = side.lower() + "_"
    return [kp for kp in keypoints if "name" in kp and kp["name"].startswith(prefix)]

def distance_between_keypoints(kp1: Dict[str, Any], kp2: Dict[str, Any]) -> float:
    """
    Calculate Euclidean distance between two keypoints.
    
    Args:
        kp1: First keypoint
        kp2: Second keypoint
        
    Returns:
        Distance between keypoints
    """
    if "x" not in kp1 or "y" not in kp1 or "x" not in kp2 or "y" not in kp2:
        return float('inf')
        
    return math.sqrt((kp1["x"] - kp2["x"])**2 + (kp1["y"] - kp2["y"])**2)

def calculate_joint_velocities(keypoints: List[Dict[str, Any]], fps: float = 30.0) -> Dict[str, float]:
    """
    Calculate joint angular velocities from keypoints.
    
    Args:
        keypoints (List[Dict[str, Any]]): Pose keypoints data
        fps (float): Frames per second
        
    Returns:
        Dict[str, float]: Dictionary mapping joint names to angular velocities
    """
    velocities = {}
    
    # Need at least 2 frames to calculate velocity
    if len(keypoints) < 2:
        return velocities
    
    # Calculate time step
    dt = 1.0 / fps
    
    # Calculate angles for all frames
    all_angles = []
    for i in range(len(keypoints)):
        coordinates = get_keypoint_coordinates(keypoints, i)
        frame_angles = {}
        
        for joint, points in JOINT_CONNECTIONS.items():
            p1, p2, p3 = points
            
            if p1 in coordinates and p2 in coordinates and p3 in coordinates:
                angle = calculate_angle(
                    coordinates[p1],
                    coordinates[p2],
                    coordinates[p3]
                )
                frame_angles[joint] = angle
        
        all_angles.append(frame_angles)
    
    # Calculate angular velocities
    for joint in JOINT_CONNECTIONS.keys():
        joint_angles = [angles.get(joint) for angles in all_angles if joint in angles]
        
        if len(joint_angles) >= 2:
            # Calculate velocity using central difference
            diffs = np.diff(joint_angles)
            velocity = np.mean(diffs) / dt
            velocities[joint] = velocity
    
    return velocities

def detect_repetitions(keypoints: List[Dict[str, Any]], joint: str = "leftKnee") -> int:
    """
    Detect exercise repetitions from keypoints.
    
    Args:
        keypoints (List[Dict[str, Any]]): Pose keypoints data
        joint (str): Joint to track for repetitions
        
    Returns:
        int: Number of repetitions detected
    """
    # Extract joint angles across frames
    angles = []
    
    for i in range(len(keypoints)):
        coordinates = get_keypoint_coordinates(keypoints, i)
        
        if joint in JOINT_CONNECTIONS:
            p1, p2, p3 = JOINT_CONNECTIONS[joint]
            
            if p1 in coordinates and p2 in coordinates and p3 in coordinates:
                angle = calculate_angle(
                    coordinates[p1],
                    coordinates[p2],
                    coordinates[p3]
                )
                angles.append(angle)
    
    if not angles:
        return 0
    
    # Smooth angles
    angles = np.array(angles)
    window_size = min(5, len(angles))
    smooth_angles = np.convolve(angles, np.ones(window_size)/window_size, mode='valid')
    
    # Find peaks and valleys
    from scipy.signal import find_peaks
    
    # Find peaks (extension)
    peaks, _ = find_peaks(smooth_angles, height=None, distance=len(smooth_angles)//10)
    
    # Find valleys (flexion)
    valleys, _ = find_peaks(-smooth_angles, height=None, distance=len(smooth_angles)//10)
    
    # Count repetitions
    reps = min(len(peaks), len(valleys))
    
    return reps 