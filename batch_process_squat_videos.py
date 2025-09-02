#!/usr/bin/env python3
"""
Batch Processing Script for FormIQ Squat Videos

This script processes raw squat videos by:
1. Extracting frames at 30fps
2. Detecting poses using MediaPipe
3. Extracting 33+ keypoints per frame
4. Saving the results in a structured format
"""

import os
import cv2
import json
import numpy as np
import mediapipe as mp
import gc
from tqdm import tqdm
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

# MediaPipe pose detection setup
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Configuration
INPUT_DIR = os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/videos")  # Input directory with squat videos
OUTPUT_DIR = os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/processed_videos")  # Output directory
EXTRACT_FRAMES = True  # Whether to extract and save frames
DETECT_KEYPOINTS = True  # Whether to detect and save keypoints
TARGET_FPS = 30  # Target frames per second for extraction
SKIP_PROCESSED = True  # Skip videos that have already been processed
MAX_WORKERS = 3  # Number of parallel workers


def ensure_dir_exists(directory):
    """Create directory if it doesn't exist"""
    os.makedirs(directory, exist_ok=True)


def extract_frames(video_path, output_dir, target_fps=30):
    """Extract frames from video at target FPS"""
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    frames_dir = os.path.join(output_dir, "frames", video_name)
    ensure_dir_exists(frames_dir)
    
    # Open video file
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video file: {video_path}")
        return None, None
    
    # Get video properties
    orig_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate frame interval to achieve target FPS
    if orig_fps > target_fps:
        interval = max(1, round(orig_fps / target_fps))
    else:
        interval = 1
    
    frames = []
    frame_paths = []
    frame_idx = 0
    
    # Process frames
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx % interval == 0:
            # Save frame
            frame_path = os.path.join(frames_dir, f"frame_{frame_idx:06d}.jpg")
            cv2.imwrite(frame_path, frame)
            frames.append(frame)
            frame_paths.append(frame_path)
        
        frame_idx += 1
    
    cap.release()
    
    return frames, frame_paths


def detect_keypoints(frames, video_path, output_dir):
    """Detect pose keypoints in frames using MediaPipe"""
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    keypoints_dir = os.path.join(output_dir, "keypoints")
    ensure_dir_exists(keypoints_dir)
    
    keypoints_path = os.path.join(keypoints_dir, f"{video_name}_keypoints.json")
    
    all_keypoints = []
    
    # Initialize MediaPipe Pose
    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,  # Reduced model complexity to save memory
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:
        for i, frame in enumerate(frames):
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame
            results = pose.process(frame_rgb)
            
            frame_keypoints = {}
            
            # Check if pose landmarks were detected
            if results.pose_landmarks:
                # Extract landmark coordinates and visibility
                landmarks = results.pose_landmarks.landmark
                frame_keypoints = {
                    'frame_index': i,
                    'landmarks': [
                        {
                            'x': landmark.x,
                            'y': landmark.y,
                            'z': landmark.z,
                            'visibility': landmark.visibility
                        } for landmark in landmarks
                    ]
                }
            else:
                frame_keypoints = {
                    'frame_index': i,
                    'landmarks': []
                }
            
            all_keypoints.append(frame_keypoints)
            
            # Clear memory for current frame
            del frame_rgb
    
    # Save keypoints to JSON file
    with open(keypoints_path, 'w') as f:
        json.dump(all_keypoints, f, indent=2)
    
    return keypoints_path


def is_already_processed(video_path, output_dir):
    """Check if a video has already been processed by looking for keypoints file"""
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    keypoints_path = os.path.join(output_dir, "keypoints", f"{video_name}_keypoints.json")
    return os.path.exists(keypoints_path)


def process_video(video_path, output_dir):
    """Process a single video: extract frames, detect keypoints"""
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    category = os.path.basename(os.path.dirname(video_path))
    subcategory = os.path.basename(os.path.dirname(os.path.dirname(video_path))) if category in ['posture_faults', 'hypertrophy_faults', 'stability_faults'] else None
    
    # Check if video was already processed
    if SKIP_PROCESSED and is_already_processed(video_path, output_dir):
        print(f"Skipping already processed video: {video_name}")
        return {
            'video_name': video_name,
            'video_path': video_path,
            'category': category,
            'subcategory': subcategory,
            'status': 'skipped',
            'reason': 'already processed'
        }
    
    print(f"Processing video: {video_name} (Category: {subcategory}/{category if subcategory else category})")
    
    metadata = {
        'video_name': video_name,
        'video_path': video_path,
        'category': category,
        'subcategory': subcategory,
    }
    
    try:
        # Extract frames
        if EXTRACT_FRAMES:
            frames, frame_paths = extract_frames(video_path, output_dir, TARGET_FPS)
            if frames is None:
                return {**metadata, 'status': 'failed', 'error': 'Frame extraction failed'}
            metadata['frame_count'] = len(frames)
            
            # Detect keypoints
            if DETECT_KEYPOINTS and frames:
                keypoints_path = detect_keypoints(frames, video_path, output_dir)
                metadata['keypoints_path'] = keypoints_path
            
            # Clean up memory
            del frames
            gc.collect()
        
        return {**metadata, 'status': 'success'}
    
    except Exception as e:
        print(f"Error processing video {video_name}: {str(e)}")
        return {**metadata, 'status': 'failed', 'error': str(e)}


def find_all_videos(root_dir):
    """Find all MP4 videos in the root directory recursively"""
    video_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.lower().endswith('.mp4') and not file.startswith('.'):
                video_files.append(os.path.join(root, file))
    return video_files


def load_existing_summary(output_dir):
    """Load existing processing summary if available"""
    summary_path = os.path.join(output_dir, 'processing_summary.json')
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def main():
    """Main function to process all videos"""
    # Create output directory
    ensure_dir_exists(OUTPUT_DIR)
    
    # Find all videos
    video_files = find_all_videos(INPUT_DIR)
    print(f"Found {len(video_files)} video files")
    
    # Load previous results if any
    existing_results = load_existing_summary(OUTPUT_DIR)
    print(f"Loaded {len(existing_results)} results from previous run")
    
    # Create dictionary of successfully processed videos
    processed_videos = {r['video_path']: r for r in existing_results if r.get('status') == 'success'}
    print(f"{len(processed_videos)} videos already processed successfully")
    
    # Filter videos that need processing
    videos_to_process = [v for v in video_files if not is_already_processed(v, OUTPUT_DIR)]
    print(f"{len(videos_to_process)} videos need processing")
    
    results = list(existing_results)  # Start with existing results
    
    # Process in small batches to manage memory better
    BATCH_SIZE = 5
    
    for i in range(0, len(videos_to_process), BATCH_SIZE):
        batch = videos_to_process[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1}/{(len(videos_to_process) + BATCH_SIZE - 1)//BATCH_SIZE}")
        
        # Process videos in parallel within the batch
        with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_video, video_path, OUTPUT_DIR) for video_path in batch]
            
            # Track progress
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"Batch {i//BATCH_SIZE + 1}"):
                try:
                    result = future.result()
                    # Only append new results
                    if result['status'] != 'skipped':
                        results.append(result)
                except Exception as e:
                    print(f"Error processing video: {e}")
        
        # Save results after each batch
        with open(os.path.join(OUTPUT_DIR, 'processing_summary.json'), 'w') as f:
            json.dump(results, f, indent=2)
            
        # Force garbage collection between batches
        gc.collect()
        print(f"Completed batch {i//BATCH_SIZE + 1}, saved results")
    
    # Print summary
    success_count = sum(1 for r in results if r.get('status') == 'success')
    failed_count = sum(1 for r in results if r.get('status') == 'failed')
    skipped_count = sum(1 for r in results if r.get('status') == 'skipped')
    print(f"Processing complete. Success: {success_count}, Failed: {failed_count}, Skipped: {skipped_count}")
    print(f"Results saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main() 