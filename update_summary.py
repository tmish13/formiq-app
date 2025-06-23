#!/usr/bin/env python3
import json
import os

# Load the current processing summary
with open(os.path.expanduser('~/Desktop/squat_processed/processing_summary.json'), 'r') as f:
    summary = json.load(f)

# Load the list of videos to remove
with open(os.path.expanduser('~/Desktop/videos_to_remove.txt'), 'r') as f:
    videos_to_remove = [line.strip() for line in f]

# Filter out entries for videos that no longer exist
new_summary = [entry for entry in summary if entry['video_name'] not in videos_to_remove]

print(f'Original entries: {len(summary)}, New entries: {len(new_summary)}')

# Save the updated processing summary
with open(os.path.expanduser('~/Desktop/squat_processed/processing_summary.json'), 'w') as f:
    json.dump(new_summary, f, indent=2)

print('Processing summary updated successfully') 