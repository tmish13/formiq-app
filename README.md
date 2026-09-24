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
- `backend/`: the FastAPI API, the Celery worker and beat, the served model (`backend/app/ml/posture_v1/`, see its `MODEL_CARD.md`)
- `backend/ml_training/posture_v1/provenance/`: the notebook codebase PostureV1 was trained with, imported unchanged with hashes (`PROVENANCE.md`); there is no `notebooks/` directory in this repository
- `bench/`: measurement scripts; every number in the audits has a note in `bench/results/`
- `frontend/`: the React app
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
4. Run the stack: `docker compose -f backend/deployment/docker-compose.yml up -d` (the only deployable description, see `infrastructure/README.md`)
5. Where things stand: `docs/EXECUTION_PLAN_2026-09-24.md` and `docs/ml/ACCEPTANCE_BAR.md`

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