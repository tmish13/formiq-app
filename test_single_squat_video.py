#!/usr/bin/env python3
"""
Test script to process a single squat video
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from batch_process_squat_videos import process_video, ensure_dir_exists

def main():
    # Configuration
    INPUT_DIR = os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/videos")
    OUTPUT_DIR = os.path.expanduser("~/Desktop/Squat More/Labeled_Dataset/processed_videos")
    
    # Create output directory
    ensure_dir_exists(OUTPUT_DIR)
    
    # Get first video
    video_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.mp4')]
    if not video_files:
        print("No video files found!")
        return
    
    test_video = os.path.join(INPUT_DIR, video_files[0])
    print(f"Testing with video: {test_video}")
    
    # Process the video
    result = process_video(test_video, OUTPUT_DIR)
    
    # Print results
    print("\n--- Processing Results ---")
    for key, value in result.items():
        print(f"{key}: {value}")
    
    # Check if keypoints were extracted
    if result.get('status') == 'success' and 'keypoints_path' in result:
        import json
        with open(result['keypoints_path'], 'r') as f:
            keypoints = json.load(f)
        print(f"\nExtracted keypoints for {len(keypoints)} frames")
        print(f"First frame has {len(keypoints[0]['landmarks'])} landmarks" if keypoints[0]['landmarks'] else "No landmarks in first frame")

if __name__ == "__main__":
    main()