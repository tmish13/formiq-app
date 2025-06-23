# FormIQ Squat Analysis Model

## Project Overview
FormIQ is an exercise form analysis application that uses machine learning to evaluate squat technique from videos. The system analyzes joint positions and movement patterns to provide personalized feedback on form quality.

## Key Features
- Multi-angle camera view detection
- View-adaptive joint angle calculations
- Machine learning-based form quality classification
- Identification of specific fault categories (posture, stability, depth)
- Integration with biomechanical analysis for comprehensive feedback

## Development Workflow
1. **Data Collection**: Using videos from Penn Action Dataset (numbers 1659-1889), categorized as "good_form" or "bad_form"
2. **Feature Extraction**: Parsing joint coordinates and calculating biomechanically relevant angles
3. **ML Model Development**: Training a multi-output neural network to classify form quality and fault types
4. **Evaluation & Integration**: Validating the model and integrating with the biomechanical analysis pipeline

## Repository Structure
- `notebooks/`: Jupyter notebooks for model development
  - `01_squat_model_development.ipynb`: Initial development notebook
  - `02_enhanced_squat_model.ipynb`: Main development notebook with ML implementation
  - `03_enhanced_squat_model_demo.ipynb`: Demo notebook for presentation
- `src/`: Source code modules
  - `camera_angle_detection/`: Detects camera view (front/side/back/diagonal)
  - `joint_angle_calculator/`: Calculates biomechanically relevant angles
  - `form_scoring/`: Scores form quality based on biomechanical analysis
  - `exercise_form_analyzer/`: Integrates all components for full analysis
- `data/`: Dataset and processed features
- `models/`: Trained ML models

## Getting Started
1. Set up a virtual environment: `python -m venv venv`
2. Activate the environment: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run Jupyter notebook: `jupyter notebook`
5. Open `notebooks/02_enhanced_squat_model.ipynb` to see the implementation

## ML Model Architecture
The model uses a multi-output neural network architecture to:
- Classify squat form as good or bad (binary classification)
- Identify specific fault categories (multi-class classification)
- Predict form quality scores (regression)

## Future Work
- Collect more diverse training data from different angles and body types
- Implement cross-validation to ensure model robustness
- Develop real-time inference pipeline for live video analysis
- Create user-friendly interface for providing feedback
- Expand to other exercise types through transfer learning