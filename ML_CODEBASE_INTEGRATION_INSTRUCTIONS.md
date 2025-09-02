# FormIQ ML Development Codebase Integration Instructions

## Overview
This document provides comprehensive instructions for the separate ML development codebase that will create machine learning models for exercise form analysis. These models will be integrated into the FormIQ backend AI pipeline.

## FormIQ Main Application Architecture

### System Architecture
FormIQ is a comprehensive AI-powered exercise form analysis application with the following components:

**Backend (FastAPI)**
- Clean service-oriented architecture with 27+ specialized services
- PostgreSQL database with SQLAlchemy ORM
- Celery task queue with Redis for async processing
- AWS S3 for video storage with presigned URLs
- JWT-based authentication system
- WebSocket support for real-time feedback

**Frontend (React + TypeScript)**
- Mobile-first responsive design with Capacitor (iOS/Android)
- Real-time WebSocket integration for live updates
- Comprehensive UI for video recording, analysis results, and progress tracking
- Material-UI components with custom styling

**AI Pipeline (10-Step Process)**
1. Video Upload → S3 with metadata
2. Video Processing → 30fps frame extraction
3. Pose Detection → MediaPipe (33+ keypoints)
4. Angle Calculation → Basic angles from pose landmarks (exercise-specific)
5. Exercise Classification → LSTM/CNN/Transformer (YOUR MODELS GO HERE)
6. Rule-Based Validation → Biomechanical rules engine
7. Feedback Generation → Langflow/OpenAI integration (planned)
8. Visual Comparison → Pose overlays with fault annotation
9. Results Storage → PostgreSQL with comprehensive schema
10. Results Delivery → REST API + WebSocket

## Current Backend AI Pipeline Status

### ✅ COMPLETED (Ready for ML Integration)
- **Video Upload & Processing**: Complete S3 integration with frame extraction
- **Pose Detection**: MediaPipe integration with 33+ keypoints
- **Angle Calculation**: Basic angle calculation from pose landmarks (exercise-specific angles defined per exercise)
- **Database Schema**: ML score fields ready (posture_score, stability_score, depth_score)
- **Service Architecture**: MLModelService with multi-model support
- **Feature Extraction**: Enhanced squat feature extractor (23 squat-specific biomechanical features)
- **Task Queue**: Celery integration for async ML processing
- **WebSocket Integration**: Real-time updates for ML analysis progress

### 🔄 IN PROGRESS (Where Your Models Integrate)
- **Exercise Classification**: Placeholder implementation (returns "squat" with 0.95 confidence)
- **ML Model Integration**: Demo RandomForest model, needs production models
- **Form Analysis**: Enhanced ML pipeline with ensemble prediction ready

### 🔲 PENDING (Future Integration Points)
- **Langflow/OpenAI**: Natural language feedback generation
- **Multi-Exercise Support**: Currently focused on squats
- **Advanced Temporal Analysis**: Full sequence-based analysis

## Current ML Infrastructure

### Existing ML Components (`backend/app/services/`)

**MLModelService (`ml_model_service.py`)**
- Multi-model architecture supporting binary, posture, stability, depth models
- Ensemble prediction with weighted voting
- Confidence scoring and uncertainty quantification
- Model caching and performance optimization
- Thread pool execution for async ML operations

**Enhanced Feature Extraction (`enhanced_feature_extraction_service.py`)**
- Extracts 23 squat-specific biomechanical features from pose data
- Temporal sequence analysis with smoothing for squat movements
- Adaptive feature selection for different squat fault model types (posture, stability, depth)
- Integration with squat-specific angle calculations

**Scoring Service (`scoring_service.py`)**
- Converts ML fault classifications to user-friendly scores (0-100)
- Maps complex ML outputs to simple posture/stability/depth scores
- Handles confidence weighting and score normalization

### Squat-Specific Feature Set (23 Features)
For squat analysis, your ML models should work with these squat-specific biomechanical features:

```json
[
  "relative_hip_depth", "hip_rom_sufficient", "depth_flag",
  "min_knee_angle", "posture_score", "max_torso_lean_angle", 
  "torso_control_flag", "excessive_forward_lean", "asymmetry_flag",
  "torso_stability_std", "knee_valgus_flag", "stability_score",
  "ascent_duration", "descent_duration", "tempo_ratio",
  "controlled_descent_flag", "overall_score", "knee_asymmetry",
  "right_knee_valgus_flag", "smooth_ascent_flag", 
  "max_right_knee_valgus_deg", "max_left_knee_valgus_deg", "knee_rom"
]
```

**Note**: These 23 features are specifically designed for squat analysis. Other exercises will require their own exercise-specific feature sets.

### Pose Data Format (33 Keypoints)
Your models receive pose data with these landmarks:
- **Indices 0-10**: Face landmarks (nose, eyes, ears, mouth)
- **Indices 11-22**: Upper body (shoulders, elbows, wrists, hands)
- **Indices 23-32**: Lower body (hips, knees, ankles, feet)

Each keypoint has: `{x: float, y: float, z: float, visibility: float}`

### Joint Angles Available
The system calculates basic angles from pose data as defined in `UNIVERSAL_ANGLE_DEFINITIONS`:
- **Legs**: left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle
- **Arms**: left_shoulder, left_elbow, right_shoulder, right_elbow  
- **Torso**: left_torso_pitch, right_torso_pitch

**Note**: The 23 joint angles with smoothing mentioned earlier are specific to the squat analysis model. Each exercise type will define its own required angles and feature calculations.

## Database Schema for ML Integration

### FormCheck Model (Primary ML Results Storage)
```python
class FormCheck(BaseModel):
    # ML Scores (0-100 scale)
    posture_score: float = Field(..., ge=0, le=100)
    stability_score: float = Field(..., ge=0, le=100) 
    depth_score: float = Field(..., ge=0, le=100)
    
    # Overall metrics
    score: float = Field(..., ge=0, le=100)  # Overall form score
    confidence_score: float = Field(..., ge=0, le=1)  # AI confidence
    
    # Classification results
    classified_exercise_slug: str  # e.g., "squat"
    classification_confidence: float = Field(..., ge=0, le=1)
    
    # Temporal analysis
    reps_detected: int
    reps_per_minute: float
    
    # Detailed results (JSON fields)
    results: dict  # Comprehensive ML analysis output
    form_metadata: dict  # Per-rep ML scores and breakdowns
```

### Video Model (Raw Data Storage)
```python
class Video(BaseModel):
    # Raw ML data
    raw_pose_data: dict  # 33 keypoints per frame
    calculated_angles: dict  # Joint angles per frame (exercise-specific)
    compressed_pose_data: dict  # Optimized storage
    analysis_results: dict  # Raw ML model outputs
```

## ML Model Requirements

### 1. **Exercise Classification Model**
**Current Status**: Placeholder implementation
**Your Task**: Create LSTM/CNN/Transformer model for exercise classification

**Input**: Sequence of pose data (33 keypoints × T frames)
**Output**: 
```python
{
    "exercise_slug": str,  # e.g., "squat", "pushup", "deadlift"
    "confidence": float,   # 0-1 confidence score
    "temporal_features": dict  # Additional sequence features
}
```

**Integration Point**: `ai_service.py` line ~400-450 in `classify_exercise_from_pose_data()`

### 2. **Squat Analysis Model (Priority)**
**Current Status**: Demo RandomForest model exists
**Your Task**: Create production-ready squat analysis model

**Model Architecture**: Multi-output neural network
**Input**: 23 squat-specific biomechanical features extracted from pose sequences (see "Squat-Specific Feature Set" above)
**Output**: 
```python
{
    "binary_classification": {"good_form": float, "bad_form": float},
    "posture_fault": float,    # 0-1 score for posture issues
    "stability_fault": float,  # 0-1 score for stability issues  
    "depth_fault": float,      # 0-1 score for depth issues
    "confidence": float,       # Overall model confidence
    "feature_importance": dict # Feature contribution scores
}
```

**Integration Point**: `ml_model_service.py` in `EnhancedSquatModelLoader`

### 3. **Temporal Sequence Analysis**
**Current Status**: Infrastructure ready
**Your Task**: Enhance models for full sequence analysis

**Requirements**:
- Process variable-length sequences (typically 3-10 seconds)
- Handle different frame rates (target 30fps)
- Segment repetitions automatically
- Provide per-rep analysis scores

### 4. **Multi-Exercise Support**
**Future Task**: Extend beyond squats to other exercises

**Planned Exercises**:
- Deadlifts, Push-ups, Pull-ups, Lunges, Planks
- Each exercise needs specific biomechanical feature extraction (similar to the 23 squat-specific features)
- Each exercise will define its own angle calculations and feature sets
- Modular architecture for adding new exercises

## Frontend Integration Points

### Real-Time Analysis Display
Your ML models integrate with these UI components:

**AnalysisPage.tsx**
- Displays ML scores: posture_score, stability_score, depth_score (currently optimized for squat analysis)
- Shows AI confidence and overall form score
- Presents category-based analysis with status indicators
- Provides expandable details with ML-generated insights

**RecordPage.tsx**
- Real-time pose detection feedback during recording
- WebSocket integration for live ML analysis updates
- Progress tracking through ML pipeline stages

**DashboardPage.tsx**
- Progress visualization using ML scores over time
- Trend analysis and improvement tracking
- Achievement system based on ML performance metrics

### WebSocket Integration
```javascript
// Real-time ML updates
websocket.onMessage((data) => {
    if (data.type === 'ml_analysis_update') {
        // Update UI with ML progress
        setPostureScore(data.posture_score);
        setStabilityScore(data.stability_score);
        setDepthScore(data.depth_score);
    }
});
```

## ML Development Guidelines

### 1. **Data Format Standards**
- Use pose data with 33 keypoints (MediaPipe format)
- Normalize coordinates to frame dimensions
- Handle missing/low-confidence keypoints gracefully
- Support variable sequence lengths

### 2. **Model Output Standards**
- All scores should be 0-1 range (converted to 0-100 for UI)
- Include confidence scores for uncertainty quantification
- Provide feature importance for explainability
- Support batch processing for efficiency

### 3. **Performance Requirements**
- Models should process 30fps video in <30 seconds
- Memory usage <2GB for typical sequences
- Support GPU acceleration when available
- Fallback to CPU processing

### 4. **Model Packaging**
Save models in this format for integration:
```
/models/
├── exercise_classification/
│   ├── model.pkl or model.pt
│   ├── scaler.pkl
│   ├── metadata.json
│   └── feature_names.json
├── squat_analysis/
│   ├── binary_model.pkl
│   ├── posture_model.pkl
│   ├── stability_model.pkl
│   ├── depth_model.pkl
│   ├── feature_scaler.pkl
│   └── model_metadata.json
```

### 5. **Testing Requirements**
- Unit tests for individual model components
- Integration tests with sample pose sequences
- Performance benchmarks with typical video lengths
- Validation against known good/bad form examples

## Dataset Specifications

### Current Dataset (Penn Action)
- **Videos**: 1659-1889 (squat exercises)
- **Labels**: Binary classification (good_form/bad_form)
- **Fault Categories**: Posture, stability, depth faults
- **Annotations**: Keypoint sequences with temporal alignment

### Required Dataset Enhancements
1. **Multi-Exercise Expansion**: Add pushups, deadlifts, lunges
2. **Temporal Segmentation**: Rep-level annotations
3. **Fault Granularity**: Specific fault types per exercise
4. **Quality Diversity**: Range of skill levels and body types

## Integration Workflow

### Step 1: Model Development
1. Train models using your separate ML codebase
2. Validate against test sequences
3. Export models in required format
4. Create model metadata files

### Step 2: Backend Integration
1. Copy model files to `backend/app/ml_models/`
2. Update `ml_model_service.py` with new model loading
3. For squat models: Use existing `enhanced_feature_extraction_service.py`
4. For new exercises: Create exercise-specific feature extraction similar to squat's 23 features

### Step 3: Testing Integration
1. Run existing backend tests to ensure no regression
2. Add new tests for your models
3. Test with real video sequences
4. Validate WebSocket integration

### Step 4: Frontend Integration
1. Update UI components for new exercise types
2. Add visualization for new ML features
3. Test real-time feedback integration
4. Validate mobile app functionality

## Development Commands

### Backend Testing
```bash
# Run all tests
pytest backend/tests/

# Test specific ML integration
pytest backend/tests/services/test_ml_model_service.py

# Test AI pipeline
pytest backend/tests/services/test_ai_service.py

# Start backend with ML models
cd backend && uvicorn app.main:app --reload
```

### Frontend Testing
```bash
# Start frontend development
npm run dev

# Build for production
npm run build

# Test mobile app
npx cap run ios
npx cap run android
```

## Error Handling & Monitoring

### ML Model Error Handling
- Graceful fallback to rule-based analysis if ML fails
- Confidence thresholding for low-quality predictions
- Logging and monitoring of model performance
- Automatic retry logic for transient failures

### Performance Monitoring
- Track model inference time
- Monitor memory usage during analysis
- Log model confidence distributions
- Alert on accuracy degradation

## Security & Privacy

### Data Privacy
- All video processing on secure backend
- No video data stored permanently
- Pose data anonymization
- GDPR compliance for EU users

### Model Security
- Input validation for pose data
- Model versioning and rollback capability
- Secure model storage and access
- Regular security audits

## Future Roadmap

### Phase 1.2.1 (Current Priority)
- Complete squat analysis model integration with 23 squat-specific features
- Full temporal sequence analysis for squat movements
- Production-ready squat model deployment

### Phase 1.3 (Next Quarter)
- Multi-exercise classification
- Langflow/OpenAI feedback integration
- Advanced visual overlay system

### Phase 1.4 (Future)
- Real-time pose correction
- Personalized training plans
- Advanced analytics dashboard

## Contact & Support

### Key Files to Reference
- **Primary Planning**: `docs/planning/backend_ai_pipeline_integration_plan.md`
- **Technical Specs**: `docs/planning/formiq_ai_pipeline_description.md`
- **Testing Plan**: `backend/core_ai_pipeline_testing_and_completion_plan.md`
- **AI Service**: `backend/app/services/ai_service.py`
- **ML Infrastructure**: `backend/app/services/ml_model_service.py`

### Integration Checklist
- [ ] Exercise classification model trained and tested
- [ ] Squat analysis model with multi-output architecture
- [ ] Model files exported in required format
- [ ] Feature extraction compatibility verified
- [ ] Backend integration tested
- [ ] Frontend UI compatibility confirmed
- [ ] WebSocket real-time updates working
- [ ] Performance benchmarks met
- [ ] Error handling implemented
- [ ] Documentation updated

This comprehensive guide should provide your ML development codebase with all necessary information to create models that seamlessly integrate with the FormIQ backend AI pipeline and frontend user experience.