from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from app.core.cache import cache_service
from app.services.form_analysis import FormAnalysisService
from app.schemas.form_analysis import FormAnalysisRequest, FormAnalysisResult, FormAnalysisHistory

router = APIRouter()

@router.post("/analyze", response_model=FormAnalysisResult)
async def analyze_form(
    video: UploadFile = File(...),
    form_analysis_service: FormAnalysisService = Depends()
):
    """Analyze exercise form from video."""
    result = await form_analysis_service.analyze_form(video)
    
    # Cache the analysis result
    cache_key = f"form_analysis:result:{result.id}"
    await cache_service.set(cache_key, result, expires_in=3600)  # Cache for 1 hour
    
    return result

@router.get("/history", response_model=List[FormAnalysisHistory])
async def get_analysis_history(
    skip: int = 0,
    limit: int = 100,
    form_analysis_service: FormAnalysisService = Depends()
):
    """Get form analysis history with caching."""
    cache_key = f"form_analysis:history:{skip}:{limit}"
    
    # Try to get from cache first
    cached_history = await cache_service.get(cache_key)
    if cached_history:
        return cached_history
    
    # If not in cache, get from database
    history = await form_analysis_service.get_history(skip=skip, limit=limit)
    
    # Cache the results
    await cache_service.set(cache_key, history, expires_in=1800)  # Cache for 30 minutes
    
    return history

@router.get("/{analysis_id}", response_model=FormAnalysisResult)
async def get_analysis(
    analysis_id: str,
    form_analysis_service: FormAnalysisService = Depends()
):
    """Get a specific form analysis with caching."""
    cache_key = f"form_analysis:result:{analysis_id}"
    
    # Try to get from cache first
    cached_analysis = await cache_service.get(cache_key)
    if cached_analysis:
        return cached_analysis
    
    # If not in cache, get from database
    analysis = await form_analysis_service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Cache the result
    await cache_service.set(cache_key, analysis, expires_in=3600)  # Cache for 1 hour
    
    return analysis

@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    form_analysis_service: FormAnalysisService = Depends()
):
    """Delete a form analysis and invalidate relevant caches."""
    deleted = await form_analysis_service.delete_analysis(analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Invalidate both list and detail caches
    await cache_service.delete("form_analysis:history:*")
    await cache_service.delete(f"form_analysis:result:{analysis_id}")
    
    return {"message": "Analysis deleted successfully"} 