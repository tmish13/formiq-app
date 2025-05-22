#!/usr/bin/env python3

import cv2
import numpy as np
import os

def create_sample_video(output_path, duration=5, fps=30):
    """Create a sample video file for load testing.
    
    Args:
        output_path (str): Path where the video will be saved
        duration (int): Duration of the video in seconds
        fps (int): Frames per second
    """
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Video dimensions
    width, height = 640, 480
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Generate frames
    for i in range(duration * fps):
        # Create a frame with a moving rectangle
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Calculate rectangle position
        x = int((i / (fps * duration)) * width)
        y = height // 2
        
        # Draw rectangle
        cv2.rectangle(frame, (x, y-50), (x+100, y+50), (0, 255, 0), -1)
        
        # Add text
        cv2.putText(frame, f"Frame {i}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Write frame
        out.write(frame)
    
    # Release resources
    out.release()
    print(f"Sample video created at: {output_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "sample_video.mp4")
    create_sample_video(output_path) 