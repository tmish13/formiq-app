"""Real-time feedback service."""
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends
# from sqlalchemy.orm import Session # No longer needed
import asyncio
import json
from datetime import datetime

from app.core.monitoring import (
    track_feedback_sent,
    track_websocket_connection,
    track_websocket_error,
    track_model_inference
)
from app.models.enums import ExerciseType, FeedbackType, FeedbackSeverity
# from app.services.pose_analysis import PoseAnalysisService # Does not seem to exist in backend/app/services
from app.core.config import settings
# Assuming logger might be useful
from app.core.logging import logger

class FeedbackService:
    """Service for managing real-time exercise feedback."""
    
    # def __init__(self, db: Session): # Old constructor taking db
    def __init__(self, video_processing_service: 'VideoProcessingService'):
        """Initialize the feedback service.
        VideoProcessingService is injected.
        PoseAnalysisService integration needs review as the service doesn't seem to exist in backend/app/services.
        """
        # self.db = db # db was not used by this service's methods
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.feedback_history: Dict[str, List[Dict[str, Any]]] = {}
        # self.pose_analysis = pose_analysis_service # TODO: Resolve PoseAnalysisService dependency
        self.video_processing = video_processing_service
        # settings can be passed via app_settings if needed by this service directly
        # self.settings = app_settings 

    async def subscribe_to_feedback(self, analysis_id: str, websocket: WebSocket) -> None:
        """Subscribe a WebSocket connection to feedback updates for an analysis."""
        if analysis_id not in self.active_connections:
            self.active_connections[analysis_id] = []
        self.active_connections[analysis_id].append(websocket)
        
        # Initialize feedback history if not exists
        if analysis_id not in self.feedback_history:
            self.feedback_history[analysis_id] = []
            
        # Send initial feedback history
        await websocket.send_json({
            "type": "feedback_history",
            "data": self.feedback_history[analysis_id]
        })
    
    async def unsubscribe_from_feedback(self, analysis_id: str, websocket: WebSocket) -> None:
        """Unsubscribe a WebSocket connection from feedback updates."""
        if analysis_id in self.active_connections:
            self.active_connections[analysis_id].remove(websocket)
            if not self.active_connections[analysis_id]:
                del self.active_connections[analysis_id]
    
    async def get_latest_feedback(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest feedback for an analysis."""
        if analysis_id in self.feedback_history and self.feedback_history[analysis_id]:
            return self.feedback_history[analysis_id][-1]
        return None
    
    async def send_feedback(
        self,
        analysis_id: str,
        feedback_type: FeedbackType,
        message: str,
        severity: FeedbackSeverity,
        timestamp: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send feedback to all subscribed WebSocket connections."""
        if analysis_id not in self.active_connections:
            return
            
        feedback = {
            "type": feedback_type.value,
            "message": message,
            "severity": severity.value,
            "timestamp": timestamp or datetime.now().timestamp(),
            "metrics": metrics or {}
        }
        
        # Store in history
        if analysis_id not in self.feedback_history:
            self.feedback_history[analysis_id] = []
        self.feedback_history[analysis_id].append(feedback)
        
        # Send to all active connections
        for websocket in self.active_connections[analysis_id]:
            try:
                await websocket.send_json({
                    "type": "feedback",
                    "data": feedback
                })
                track_feedback_sent(analysis_id, 1)
            except Exception as e:
                track_websocket_error(str(type(e).__name__))
                await self.unsubscribe_from_feedback(analysis_id, websocket)
    
    async def subscribe_to_session(self, session_id: str, websocket: WebSocket) -> None:
        """Subscribe a WebSocket connection to exercise session updates."""
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        
        # Initialize session state
        if session_id not in self.feedback_history:
            self.feedback_history[session_id] = []
    
    async def unsubscribe_from_session(self, session_id: str, websocket: WebSocket) -> None:
        """Unsubscribe a WebSocket connection from session updates."""
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def start_exercise_tracking(
        self,
        session_id: str,
        exercise_type: ExerciseType,
        websocket: WebSocket
    ) -> None:
        """Start tracking a new exercise in the session."""
        try:
            # Initialize exercise tracking
            await websocket.send_json({
                "type": "exercise_started",
                "data": {
                    "exercise_type": exercise_type.value,
                    "start_time": datetime.now().timestamp()
                }
            })
            
            # Send initial form guidance
            await self.send_feedback(
                analysis_id=session_id,
                feedback_type=FeedbackType.GUIDANCE,
                message=f"Starting {exercise_type.value} tracking. Please maintain proper form.",
                severity=FeedbackSeverity.INFO
            )
            
        except Exception as e:
            track_websocket_error(str(type(e).__name__))
            await websocket.close(code=1011)
    
    async def end_exercise_tracking(
        self,
        session_id: str,
        websocket: WebSocket
    ) -> None:
        """End the current exercise tracking."""
        try:
            # Send exercise summary
            if session_id in self.feedback_history:
                summary = self._generate_exercise_summary(session_id)
                await websocket.send_json({
                    "type": "exercise_ended",
                    "data": summary
                })
                
        except Exception as e:
            track_websocket_error(str(type(e).__name__))
            await websocket.close(code=1011)
    
    async def process_pose_update(
        self,
        session_id: str,
        pose_data: Dict[str, Any],
        websocket: WebSocket
    ) -> None:
        """Process new pose data and provide real-time feedback."""
        try:
            start_time = datetime.now().timestamp()
            
            # TODO: Replace with actual pose analysis call once PoseAnalysisService is resolved/implemented
            # analysis_result = await self.pose_analysis.analyze_pose(pose_data)
            # For now, let's create a placeholder or skip this part
            logger.warning("PoseAnalysisService not available. Skipping pose analysis in FeedbackService.process_pose_update.")
            # Placeholder analysis result if needed for downstream logic to not break immediately
            analysis_result = {
                "exercise_type": "unknown", 
                "feedback": "Pose analysis currently unavailable.", 
                "errors": [], 
                "metrics": {},
                "confidence": 0.0
            }

            # Track model inference (even if placeholder)
            track_model_inference(
                exercise_type=analysis_result["exercise_type"],
                frame_count=1,
                has_errors=bool(analysis_result.get("errors")),
                model_type="pose_analysis_placeholder", # Indicate placeholder
                duration=datetime.now().timestamp() - start_time,
                confidence=analysis_result.get("confidence", 0.0),
                error_type=None if not analysis_result.get("errors") else "form_error"
            )
            
            # Send feedback based on analysis
            if analysis_result["feedback"]:
                await self.send_feedback(
                    analysis_id=session_id,
                    feedback_type=FeedbackType.FORM_CORRECTION,
                    message=analysis_result["feedback"],
                    severity=FeedbackSeverity.INFO, # Default to INFO for placeholder
                    metrics=analysis_result.get("metrics")
                )
            
            # Send pose analysis results (placeholder)
            await websocket.send_json({
                "type": "pose_analysis",
                "data": analysis_result
            })
            
        except Exception as e:
            logger.error(f"Error in process_pose_update: {e}", exc_info=True) # Log the actual error
            track_websocket_error(str(type(e).__name__))
            # Avoid closing websocket on all errors, client might want to retry or get error message
            # await websocket.close(code=1011) 
            try:
                await websocket.send_json({"type": "error", "message": "Error processing pose update."})
            except WebSocketDisconnect:
                pass # Client already disconnected
            except Exception as send_e:
                logger.error(f"Failed to send error to websocket: {send_e}", exc_info=True)
    
    def _generate_exercise_summary(self, session_id: str) -> Dict[str, Any]:
        """Generate a summary of the exercise session."""
        feedback_items = self.feedback_history.get(session_id, [])
        
        # Count feedback by type and severity
        feedback_counts = {
            "total": len(feedback_items),
            "by_type": {},
            "by_severity": {}
        }
        
        for item in feedback_items:
            # Count by type
            feedback_type = item["type"]
            feedback_counts["by_type"][feedback_type] = feedback_counts["by_type"].get(feedback_type, 0) + 1
            
            # Count by severity
            severity = item["severity"]
            feedback_counts["by_severity"][severity] = feedback_counts["by_severity"].get(severity, 0) + 1
        
        return {
            "feedback_counts": feedback_counts,
            "duration": feedback_items[-1]["timestamp"] - feedback_items[0]["timestamp"] if feedback_items else 0,
            "end_time": datetime.now().timestamp()
        } 

# Dependency Injector for FeedbackService
async def get_async_feedback_service(
    # video_processing_service: VideoProcessingService = Depends(get_async_video_processing_service) # Original problematic Depends
) -> FeedbackService:
    from app.services.video_processing_service import get_async_video_processing_service, VideoProcessingService # ADDING LOCAL IMPORTS
    from fastapi import Depends as FastAPI_Depends # Alias for clarity

    video_processing_service_instance: VideoProcessingService = FastAPI_Depends(get_async_video_processing_service)
    return FeedbackService(video_processing_service=video_processing_service_instance) 