# Squat Video Batch Processing

This tool processes squat videos to extract frames and perform pose detection according to the FormIQ AI pipeline.

## Features

- Extracts video frames at 30 FPS
- Detects human pose using MediaPipe (33+ keypoints per frame)
- Processes videos in parallel for improved performance
- Preserves the category structure of the videos (good_form/bad_form/etc.)
- Saves results as both image frames and structured JSON data

## Requirements

- Python 3.8 or newer
- OpenCV
- MediaPipe
- NumPy
- tqdm

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements_batch_processing.txt
```

## Usage

1. Edit the configuration variables in `batch_process_squat_videos.py` if needed:

```python
# Configuration
INPUT_DIR = os.path.expanduser("~/Desktop/squat")  # Input directory with squat videos
OUTPUT_DIR = os.path.expanduser("~/Desktop/squat_processed")  # Output directory
EXTRACT_FRAMES = True  # Whether to extract and save frames
DETECT_KEYPOINTS = True  # Whether to detect and save keypoints
TARGET_FPS = 30  # Target frames per second for extraction
MAX_WORKERS = 4  # Number of parallel processes
```

2. Run the script:

```bash
python batch_process_squat_videos.py
```

## Output Structure

The script will create the following directory structure:

```
squat_processed/
├── frames/
│   ├── 1770/
│   │   ├── frame_000000.jpg
│   │   ├── frame_000001.jpg
│   │   └── ...
│   └── ...
├── keypoints/
│   ├── 1770_keypoints.json
│   └── ...
└── processing_summary.json
```

- **frames/**: Contains extracted frames from each video
- **keypoints/**: Contains JSON files with MediaPipe pose landmarks for each video
- **processing_summary.json**: Summary of the processing results

## Keypoint Data Format

Each keypoint JSON file contains an array of frames, with each frame having:

```json
{
  "frame_index": 0,
  "landmarks": [
    {
      "x": 0.5,
      "y": 0.6,
      "z": 0.1,
      "visibility": 0.95
    },
    ...
  ]
}
```

MediaPipe detects 33 landmarks, corresponding to different body parts:

0. nose
1. left_eye_inner
2. left_eye
...
32. right_heel

## Troubleshooting

- If you encounter memory issues, reduce `MAX_WORKERS`
- For higher accuracy, increase `min_detection_confidence` and `min_tracking_confidence`
- For faster processing, decrease `model_complexity` (options: 0, 1, 2) 