#!/usr/bin/env python3
"""
Process squat videos in chunks with automatic report updates
"""

import os
import subprocess
import json
import time
from datetime import datetime

def get_current_progress():
    """Get current processing progress"""
    summary_path = os.path.expanduser('~/Desktop/Squat More/Labeled_Dataset/processed_videos/processing_summary.json')
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            results = json.load(f)
        
        success = sum(1 for r in results if r.get('status') == 'success')
        failed = sum(1 for r in results if r.get('status') == 'failed')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')
        
        return {
            'total_processed': len(results),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'remaining': 1739 - success
        }
    return None

def update_report(progress, start_time):
    """Update the markdown report with current progress"""
    elapsed = time.time() - start_time
    processing_rate = progress['success'] / (elapsed / 60) if elapsed > 0 else 0
    eta_minutes = progress['remaining'] / processing_rate if processing_rate > 0 else 0
    
    report_content = f"""# Squat Video Batch Processing Report

## Summary
Successfully set up and initiated batch processing for squat videos from the Labeled_Dataset.

## Video Dataset
- **Location**: `/Users/tarpanmishra/Desktop/Squat More/Labeled_Dataset/videos/`
- **Total Videos**: 1,739 unique squat videos
- **Format**: All MP4 files
- **Naming Pattern**: `{{video_id}}_{{sequence_number}}.mp4`

## Processing Configuration
- **Output Directory**: `/Users/tarpanmishra/Desktop/Squat More/Labeled_Dataset/processed_videos/`
- **Frame Extraction**: 30 FPS
- **Pose Detection**: MediaPipe with 33 keypoints per frame
- **Batch Size**: 5 videos per batch
- **Parallel Workers**: 3

## Current Progress (Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
- **Videos Processed**: {progress['success']} ({progress['success']/17.39:.1f}%)
- **Videos Remaining**: {progress['remaining']} ({progress['remaining']/17.39:.1f}%)
- **Failed Videos**: {progress['failed']}
- **Success Rate**: {(progress['success']/(progress['success']+progress['failed'])*100 if progress['success']+progress['failed'] > 0 else 100):.1f}%
- **Processing Speed**: {processing_rate:.1f} videos per minute
- **Estimated Time Remaining**: {eta_minutes:.0f} minutes ({eta_minutes/60:.1f} hours)

## Processing History
- Started: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}
- Total Elapsed Time: {elapsed/60:.1f} minutes
- Current Batch: {(progress['success'] // 5) + 1} of 348

## Output Structure
```
processed_videos/
├── frames/
│   └── {{video_name}}/
│       └── frame_000000.jpg, frame_000001.jpg, ...
├── keypoints/
│   └── {{video_name}}_keypoints.json
└── processing_summary.json
```

## Next Steps
To continue processing the remaining videos:
```bash
python3 batch_process_squat_videos.py
```

The script will automatically skip already processed videos and continue from where it left off.

## Integration with FormIQ
Once all videos are processed, the extracted keypoints can be used to:
1. Train the ML models for exercise classification
2. Enhance the squat form analysis with this larger dataset
3. Improve the accuracy of fault detection (posture, stability, depth)

The keypoints format is compatible with FormIQ's AI pipeline, which expects 33 landmarks per frame with x, y, z coordinates and visibility scores.

## Processing Log
"""
    
    # Add recent progress entries
    log_file = '/Users/tarpanmishra/formiq-app-3/processing_log.txt'
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            log_entries = f.readlines()[-10:]  # Last 10 entries
        report_content += "\n### Recent Activity\n```\n"
        report_content += "".join(log_entries)
        report_content += "```\n"
    
    with open('/Users/tarpanmishra/formiq-app-3/squat_video_processing_report.md', 'w') as f:
        f.write(report_content)

def log_progress(message):
    """Log progress to file"""
    log_file = '/Users/tarpanmishra/formiq-app-3/processing_log.txt'
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {message}\n")

def main():
    """Main processing loop"""
    start_time = time.time()
    
    # Get initial progress
    initial_progress = get_current_progress()
    if initial_progress:
        log_progress(f"Starting processing. Already completed: {initial_progress['success']} videos")
    
    while True:
        # Get current progress
        progress = get_current_progress()
        if not progress:
            print("No progress file found. Starting fresh...")
            progress = {'success': 0, 'remaining': 1739}
        
        # Check if all videos are processed
        if progress['remaining'] == 0:
            log_progress("All videos processed successfully!")
            update_report(progress, start_time)
            print("All videos have been processed!")
            break
        
        # Update report
        update_report(progress, start_time)
        
        # Log current status
        log_progress(f"Progress: {progress['success']}/1739 videos completed ({progress['success']/17.39:.1f}%)")
        
        print(f"\nCurrent Progress: {progress['success']}/1739 ({progress['success']/17.39:.1f}%)")
        print(f"Remaining: {progress['remaining']} videos")
        print("Starting next batch processing chunk...")
        
        # Run batch processing for 5 minutes
        try:
            result = subprocess.run(
                ['python3', 'batch_process_squat_videos.py'],
                timeout=300,  # 5 minutes
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                log_progress(f"Error in batch processing: {result.stderr}")
                print(f"Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            log_progress("Batch processing chunk completed (5 min timeout)")
            print("Batch processing chunk completed, updating report...")
        except Exception as e:
            log_progress(f"Unexpected error: {str(e)}")
            print(f"Unexpected error: {str(e)}")
            time.sleep(5)  # Wait before retrying
        
        # Small delay between chunks
        time.sleep(2)
    
    print("Processing complete!")

if __name__ == "__main__":
    main()