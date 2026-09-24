# FormIQ - AI-Powered Exercise Form Analysis Application

## Project Overview
FormIQ is a comprehensive AI-powered exercise form analysis application that uses machine learning to evaluate workout technique from videos. The system provides real-time feedback on form quality, identifies specific faults, and delivers personalized recommendations to improve exercise performance.

## Current Architecture Status

### ✅ COMPLETED PHASES (Based on backend_ai_pipeline_integration_plan.md)

#### Phase 1.0: Video Upload and Service Validation
- **Status**: COMPLETE ✅
- Video upload mechanism with presigned S3 URLs
- Metadata handling and database persistence
- Unit and API tests passing

#### Phase 1.1: Core Processing and Asynchronicity
- **Status**: COMPLETE ✅ 
- **Step 1.1.1**: VideoProcessingService & Celery Integration (88% coverage)
- **Step 1.1.2**: AI Service Pose Detection & Celery Integration (21% coverage, core logic verified)
- **Step 1.1.3**: Initial Angle Calculation (COMPLETE ✅)

### 🔄 IN PROGRESS

#### Phase 1.2: Comprehensive ML-Driven Form Analysis
- **Step 1.2.1**: Design and Develop Comprehensive Form Analysis ML Model
  - **Current Status** (2026-09-24): PostureV1 is trained and served, labelled experimental because it is below the acceptance bar (`docs/ml/ACCEPTANCE_BAR.md`); its notebook codebase is imported as provenance under `backend/ml_training/`; the next lever is the graded relabelling pilot (`bench/relabel/`), not another training run
  - **Focus**: Squat classification (good_form vs bad_form with fault analysis)
  - **Model Output**: Posture fault, stability fault, depth fault classification
  - **Next**: Integrate trained model into AIService

### 🔲 PENDING PHASES

#### Phase 1.3: Advanced Feedback - Visual and Textual
- Fallback exercise classification infrastructure
- Backend support for reference visual overlays  
- Langflow/OpenAI integration for feedback generation

#### Phase 1.4: User Experience and Delivery
- Visual comparison aids (user pose vs reference overlay)
- Robust results delivery via API & WebSockets

#### Phase 1.5: Backend Goals and Polish
- Comprehensive Celery retry and error handling
- Validation and data integrity checks
- Configuration refinements

## Technology Stack

### Backend
- **Framework**: FastAPI with clean architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Celery with Redis
- **Storage**: AWS S3 for video storage
- **Authentication**: JWT-based auth system

### AI/ML Pipeline
- **Pose Detection**: MediaPipe, MoveNet (33+ keypoints)
- **Video Processing**: ffmpeg, OpenCV
- **ML Framework**: PyTorch, TensorFlow
- **Angle Calculation**: NumPy, custom geometry utils
- **Feedback Generation**: Langflow, OpenAI integration (planned)

### Frontend (Baseline Implementation)
- **Framework**: React with TypeScript
- **Mobile**: Capacitor for iOS/Android
- **UI**: Material-UI, Styled Components
- **Real-time**: WebSocket support for live feedback

## Key Services & Components

### Core Services
- `video_service.py` - Video upload and metadata management
- `storage_service.py` - S3 integration and file management
- `video_processing_service.py` - Frame extraction and normalization
- `ai_service.py` - Pose detection and angle calculation
- `dynamic_form_analysis_service.py` - Rule-based form validation
- `form_analysis_service.py` - Analysis orchestration
- `feedback_service.py` - Real-time feedback delivery

### AI Pipeline (10-Step Process)
1. **Video Upload** - Presigned S3 URLs with metadata
2. **Video Processing** - 30fps frame extraction, normalization
3. **Pose Detection** - 33+ keypoint detection via MediaPipe
4. **Angle Calculation** - Joint angles with trajectory smoothing
5. **Exercise Classification** - LSTM/CNN/Transformer models (planned)
6. **Rule-Based Validation** - Biomechanical rules engine
7. **Feedback Generation** - Langflow/OpenAI natural language
8. **Visual Comparison** - Pose overlay with fault annotation
9. **Results Storage** - PostgreSQL with comprehensive schema
10. **Results Delivery** - REST API and WebSocket delivery

## Current ML Development

### Squat Analysis Model (Separate Codebase)
- **Dataset**: Penn Action Dataset (videos 1659-1889)
- **Classification**: Binary (good_form/bad_form) + fault categorization
- **Fault Types**: Posture fault, stability fault, depth fault
- **Architecture**: Multi-output neural network
- **Integration Status**: Model development complete, backend integration pending

## Testing Status

### ✅ Passing Tests
- Video upload unit and API tests
- Video processing service (88% coverage)
- AI service pose detection core logic
- Angle calculation with trajectory smoothing
- Integration tests for Celery tasks

### 🔄 Test Coverage Areas
- AI service general coverage (21% - core logic verified)
- End-to-end pipeline testing
- Form analysis integration tests

## Development Commands

### Backend
```bash
# Start backend server
cd backend && uvicorn app.main:app --reload

# Run tests
pytest backend/tests/

# Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Database migrations
alembic upgrade head
```

### Frontend (When Ready)
```bash
# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

## File Structure & Key Locations

### Documentation
- `docs/planning/backend_ai_pipeline_integration_plan.md` - **MAIN REFERENCE**
- `docs/planning/formiq_ai_pipeline_description.md` - Technical specifications
- `backend/core_ai_pipeline_testing_and_completion_plan.md` - Testing roadmap
- `docs/architecture/README.md` - Backend architecture overview

### Core Implementation
- `backend/app/services/` - All service implementations
- `backend/app/tasks/` - Celery task definitions
- `backend/app/models/` - Database models
- `backend/tests/` - Comprehensive test suite

### AI Pipeline Constants
- `backend/app/constants/angles.py` - UNIVERSAL_ANGLE_DEFINITIONS
- `backend/app/config.py` - Configuration including ML thresholds

## Next Priority Tasks

### Immediate (Phase 1.2.1 Completion)
1. ~~Integrate ML Model~~ done: PostureV1 is served by the worker (`app/ml/posture_v1/`); the API injects a lazy proxy and never loads it (G-54)
2. **Database Schema**: Enhance FormCheck model for ML scores (posture_score, stability_score, depth_score)
3. **Testing**: Complete end-to-end pipeline testing

### Short Term (Phase 1.3)
1. **Langflow Integration**: Natural language feedback generation
2. **Visual Overlays**: Backend support for reference pose data
3. **Exercise Classification**: Fallback classification when exercise_id missing

### Medium Term (Phase 1.4-1.5)
1. **Frontend Integration**: Connect React frontend to backend API
2. **Mobile Support**: iOS/Android integration via Capacitor
3. **Performance Optimization**: Celery retry logic and error handling

## Important Notes

### Development Guidelines
- **Database**: Use `postgresql.UUID(as_uuid=True)` instead of SQLiteUUID
- **Security**: Never commit secrets; use environment variables
- **Testing**: All new features require unit and integration tests
- **Code Style**: Follow existing patterns in service layer
- **ML Models**: Validate all frame data before saving; discard low-confidence frames

### Current Focus
The pipeline goals (trail, batch reliability, cache, backpressure, schema and image checks, CI) are met and measured; see `docs/EXECUTION_PLAN_2026-09-24.md` §0 for the goals verdict and §1a for status. The model is below the bar; the open experiment is the relabelling pilot, and the trainer port (`backend/ml_training/posture_v1/`) is what will consume its labels. Rules that hold for every change: one gap per branch, evidence in `bench/results/`, one logged test read per model, numbers never rounded up.

### Key Files to Reference
- **Primary Planning**: `docs/planning/backend_ai_pipeline_integration_plan.md`
- **Technical Specs**: `docs/planning/formiq_ai_pipeline_description.md`
- **Testing Plan**: `backend/core_ai_pipeline_testing_and_completion_plan.md`
- **Main README**: `README.md`

This CLAUDE.md serves as the central reference point for understanding FormIQ's current state, architecture, and development roadmap.