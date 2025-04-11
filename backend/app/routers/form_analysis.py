from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Dict, Any
import json
from ..services.form_analysis import FormAnalysisService
from ..models.form_analysis import FormAnalysisResult, FormAnalysisRequest
from ..core.auth import get_current_user

router = APIRouter(prefix="/form-analysis", tags=["form-analysis"])
form_analysis_service = FormAnalysisService()

@router.post("/analyze", response_model=FormAnalysisResult)
async def analyze_form(
    video: UploadFile = File(...),
    keypoints: str = Form(...),
    duration: float = Form(...),
    exercise_id: str = Form(None),
    current_user = Depends(get_current_user)
):
    try:
        # Parse keypoints from JSON string
        keypoints_data = json.loads(keypoints)
        
        # Create analysis request
        request = FormAnalysisRequest(
            video=video,
            keypoints=keypoints_data,
            duration=duration,
            exercise_id=exercise_id,
            user_id=current_user.id
        )
        
        # Process the analysis
        result = await form_analysis_service.analyze_form(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[FormAnalysisResult])
async def get_analysis_history(current_user = Depends(get_current_user)):
    try:
        history = await form_analysis_service.get_user_history(current_user.id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{analysis_id}", response_model=FormAnalysisResult)
async def get_analysis(
    analysis_id: str,
    current_user = Depends(get_current_user)
):
    try:
        result = await form_analysis_service.get_analysis(analysis_id, current_user.id)
        if not result:
            raise HTTPException(status_code=404, detail="Analysis not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save", response_model=FormAnalysisResult)
async def save_analysis(
    result: FormAnalysisResult,
    current_user = Depends(get_current_user)
):
    try:
        saved_result = await form_analysis_service.save_analysis(result, current_user.id)
        return saved_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 