"""
Pose estimation utility module for analyzing exercise form.
This module provides functions to detect and analyze exercise poses using MediaPipe.
"""

import cv2
import mediapipe as mp
import numpy as np
import json
import os
import tempfile
import boto3
from typing import Dict, List, Tuple, Any
import math
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Initialize MediaPipe pose model
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Exercise reference angles and rules
EXERCISE_REFERENCES = {
    "squat": {
        "key_angles": {
            "hip": {"min": 50, "max": 100, "optimal": 90},
            "knee": {"min": 70, "max": 110, "optimal": 90},
            "ankle": {"min": 70, "max": 110, "optimal": 90}
        },
        "rules": [
            {"description": "Keep back straight", "check": "back_angle"},
            {"description": "Knees should not go beyond toes", "check": "knee_position"},
            {"description": "Feet should be shoulder width apart", "check": "feet_width"},
            {"description": "Depth should reach parallel or below", "check": "squat_depth"}
        ]
    },
    "deadlift": {
        "key_angles": {
            "hip": {"min": 50, "max": 100, "optimal": 90},
            "knee": {"min": 130, "max": 170, "optimal": 160},
            "back": {"min": 80, "max": 100, "optimal": 90}
        },
        "rules": [
            {"description": "Keep back flat", "check": "back_angle"},
            {"description": "Bar path should be vertical", "check": "bar_path"},
            {"description": "Hip hinge movement pattern", "check": "hip_hinge"},
            {"description": "Neutral spine throughout the lift", "check": "neutral_spine"}
        ]
    },
    "bench_press": {
        "key_angles": {
            "elbow": {"min": 70, "max": 110, "optimal": 90},
            "shoulder": {"min": 45, "max": 90, "optimal": 70},
            "wrist": {"min": 160, "max": 180, "optimal": 180}
        },
        "rules": [
            {"description": "Elbows at 45-degree angle", "check": "elbow_angle"},
            {"description": "Bar path should be vertical", "check": "bar_path"},
            {"description": "Shoulders should be retracted", "check": "shoulder_retraction"},
            {"description": "Wrists should be straight", "check": "wrist_angle"}
        ]
    }
}

def calculate_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Calculate the angle between three points."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    
    if angle > 180.0:
        angle = 360 - angle
        
    return angle

def get_pose_landmarks(video_path: str) -> List[Dict[str, Any]]:
    """Extract pose landmarks from video frames."""
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Sample frames (1 frame per second)
    sample_rate = int(fps)
    landmarks_frames = []
    
    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    ) as pose:
        frame_idx = 0
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break
                
            # Only process every Nth frame
            if frame_idx % sample_rate == 0:
                # Convert the BGR image to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Process the image and detect pose
                results = pose.process(image_rgb)
                
                if results.pose_landmarks:
                    # Convert landmarks to dictionary
                    frame_landmarks = {}
                    for idx, landmark in enumerate(results.pose_landmarks.landmark):
                        frame_landmarks[idx] = {
                            "x": landmark.x,
                            "y": landmark.y,
                            "z": landmark.z,
                            "visibility": landmark.visibility
                        }
                    
                    landmarks_frames.append({
                        "frame": frame_idx,
                        "timestamp": frame_idx / fps,
                        "landmarks": frame_landmarks
                    })
            
            frame_idx += 1
    
    cap.release()
    return landmarks_frames

def identify_exercise(landmarks_frames: List[Dict[str, Any]]) -> str:
    """Identify which exercise is being performed."""
    # Use middle frame for identification
    middle_idx = len(landmarks_frames) // 2
    if not landmarks_frames or middle_idx >= len(landmarks_frames):
        return "unknown"
    
    middle_frame = landmarks_frames[middle_idx]
    landmarks = middle_frame["landmarks"]
    
    # Check if squatting
    if len(landmarks) >= 33:  # Full pose detected
        hip = np.array([landmarks[24]["x"], landmarks[24]["y"]])
        knee = np.array([landmarks[26]["x"], landmarks[26]["y"]])
        ankle = np.array([landmarks[28]["x"], landmarks[28]["y"]])
        
        hip_height = hip[1]
        shoulder_height = landmarks[12]["y"]
        
        if hip_height > 0.6 and shoulder_height > 0.5:
            return "squat"
        
        # Check if deadlifting
        if hip_height > 0.5 and shoulder_height > 0.4 and hip_height - knee[1] < 0.1:
            return "deadlift"
        
        # Check if bench pressing
        if hip_height < 0.5 and shoulder_height < 0.4:
            return "bench_press"
    
    return "unknown"

def analyze_form(landmarks_frames: List[Dict[str, Any]], exercise_type: str) -> Dict[str, Any]:
    """Analyze exercise form and provide feedback."""
    if exercise_type not in EXERCISE_REFERENCES:
        return {
            "exercise_type": "unknown",
            "score": 0,
            "overall_feedback": "Exercise not recognized. Please try again with a supported exercise.",
            "issues": ["Unsupported exercise type"]
        }
    
    # Get reference for this exercise
    exercise_ref = EXERCISE_REFERENCES[exercise_type]
    
    # Analyze each frame and collect metrics
    metrics = []
    issues = []
    
    for frame_data in landmarks_frames:
        landmarks = frame_data["landmarks"]
        
        # Calculate key angles based on exercise type
        frame_metrics = {}
        
        if exercise_type == "squat":
            # Hip angle (spine to hip to knee)
            if 12 in landmarks and 24 in landmarks and 26 in landmarks:
                hip_angle = calculate_angle(
                    [landmarks[12]["x"], landmarks[12]["y"]],
                    [landmarks[24]["x"], landmarks[24]["y"]],
                    [landmarks[26]["x"], landmarks[26]["y"]]
                )
                frame_metrics["hip"] = hip_angle
            
            # Knee angle (hip to knee to ankle)
            if 24 in landmarks and 26 in landmarks and 28 in landmarks:
                knee_angle = calculate_angle(
                    [landmarks[24]["x"], landmarks[24]["y"]],
                    [landmarks[26]["x"], landmarks[26]["y"]],
                    [landmarks[28]["x"], landmarks[28]["y"]]
                )
                frame_metrics["knee"] = knee_angle
                
            # Back angle (vertical)
            if 12 in landmarks and 24 in landmarks:
                shoulder = np.array([landmarks[12]["x"], landmarks[12]["y"]])
                hip = np.array([landmarks[24]["x"], landmarks[24]["y"]])
                vertical = np.array([hip[0], 0])  # Point directly above hip
                back_angle = calculate_angle(vertical, hip, shoulder)
                frame_metrics["back"] = back_angle
        
        metrics.append(frame_metrics)
    
    # Analyze metrics across frames
    average_metrics = {}
    for key in exercise_ref["key_angles"]:
        values = [m.get(key, 0) for m in metrics if key in m]
        if values:
            average_metrics[key] = sum(values) / len(values)
    
    # Calculate score and identify issues
    score = 100
    for key, ref_values in exercise_ref["key_angles"].items():
        if key in average_metrics:
            value = average_metrics[key]
            optimal = ref_values["optimal"]
            min_val = ref_values["min"]
            max_val = ref_values["max"]
            
            # Reduce score based on deviation from optimal
            deviation = abs(value - optimal) / (max_val - min_val) * 100
            score -= min(deviation, 20)  # Cap penalty at 20 points per metric
            
            # Add issue if significant deviation
            if deviation > 30:
                issues.append(f"Improve {key} angle for better form")
    
    # Ensure score is between 0 and 100
    score = max(0, min(100, score))
    
    # Generate overall feedback
    if score >= 90:
        overall_feedback = "Excellent form! Keep up the good work."
    elif score >= 75:
        overall_feedback = "Good form with minor issues to improve."
    elif score >= 50:
        overall_feedback = "Several form issues detected that need attention."
    else:
        overall_feedback = "Significant form issues. Consider lighter weight and focus on technique."
    
    return {
        "exercise_type": exercise_type,
        "score": round(score),
        "overall_feedback": overall_feedback,
        "issues": issues
    }

def generate_feedback_video(video_path: str, landmarks_frames: List[Dict[str, Any]], exercise_type: str) -> str:
    """Generate feedback video with pose landmarks and annotations."""
    cap = cv2.VideoCapture(video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Create temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
        output_path = tmp_file.name
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_landmarks_map = {frame["frame"]: frame["landmarks"] for frame in landmarks_frames}
    
    with mp_pose.Pose() as pose:
        frame_idx = 0
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break
            
            # Check if we have landmarks for this frame
            if frame_idx in frame_landmarks_map:
                landmarks = frame_landmarks_map[frame_idx]
                
                # Convert dictionary landmarks to proper format for drawing
                landmark_list = mp.solutions.pose.PoseLandmark
                pose_landmarks = mp_pose.PoseLandmark
                
                # Create a custom landmark proto for drawing
                mp_drawing.draw_landmarks(
                    image,
                    _landmarks_dict_to_proto(landmarks),
                    mp_pose.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)
                )
                
                # Add annotations based on exercise type
                if exercise_type == "squat":
                    # Add angle annotations
                    if 24 in landmarks and 26 in landmarks and 28 in landmarks:
                        # Draw knee angle
                        hip = (int(landmarks[24]["x"] * width), int(landmarks[24]["y"] * height))
                        knee = (int(landmarks[26]["x"] * width), int(landmarks[26]["y"] * height))
                        ankle = (int(landmarks[28]["x"] * width), int(landmarks[28]["y"] * height))
                        
                        knee_angle = calculate_angle(
                            [landmarks[24]["x"], landmarks[24]["y"]],
                            [landmarks[26]["x"], landmarks[26]["y"]],
                            [landmarks[28]["x"], landmarks[28]["y"]]
                        )
                        
                        # Draw angle arc and text
                        cv2.line(image, hip, knee, (0, 255, 0), 2)
                        cv2.line(image, knee, ankle, (0, 255, 0), 2)
                        cv2.putText(image, f"{int(knee_angle)}", 
                                   (knee[0]-30, knee[1]+30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Write the frame
            out.write(image)
            frame_idx += 1
    
    cap.release()
    out.release()
    
    # Upload to S3 if configured
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and settings.AWS_BUCKET_NAME:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Generate unique filename
        filename = f"processed/{os.path.basename(video_path)}"
        
        # Upload file
        s3_client.upload_file(output_path, settings.AWS_BUCKET_NAME, filename)
        
        # Generate URL
        url = f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{filename}"
    else:
        # For local development/testing
        url = output_path
    
    return url

def _landmarks_dict_to_proto(landmarks_dict):
    """Convert dictionary landmarks to MediaPipe landmark proto format."""
    from mediapipe.framework.formats import landmark_pb2
    
    landmarks_proto = landmark_pb2.NormalizedLandmarkList()
    
    for i in range(33):  # MediaPipe pose has 33 landmarks
        if i in landmarks_dict:
            landmark = landmarks_dict[i]
            landmarks_proto.landmark.add(
                x=landmark["x"],
                y=landmark["y"],
                z=landmark["z"],
                visibility=landmark["visibility"]
            )
        else:
            # Add a placeholder with zero visibility if landmark is missing
            landmarks_proto.landmark.add(
                x=0,
                y=0,
                z=0,
                visibility=0
            )
    
    return landmarks_proto

def process_exercise_video(video_path: str) -> Dict[str, Any]:
    """Process exercise video and return analysis."""
    # Extract pose landmarks
    landmarks_frames = get_pose_landmarks(video_path)
    
    if not landmarks_frames:
        return {
            "exercise_type": "unknown",
            "score": 0,
            "overall_feedback": "No pose detected in video. Please ensure your full body is visible.",
            "issues": ["No pose detected"],
            "video_url": None
        }
    
    # Identify exercise
    exercise_type = identify_exercise(landmarks_frames)
    
    # Analyze form
    analysis = analyze_form(landmarks_frames, exercise_type)
    
    # Generate feedback video
    video_url = generate_feedback_video(video_path, landmarks_frames, exercise_type)
    
    # Add video URL to analysis
    analysis["video_url"] = video_url
    
    return analysis 