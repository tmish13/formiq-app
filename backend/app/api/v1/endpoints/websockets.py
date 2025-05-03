"""WebSocket endpoints for real-time form analysis feedback."""
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.deps import get_current_active_user
from app.models.user import User
from app.services.feedback_service import FeedbackService
from app.core.monitoring import track_websocket_connection, track_websocket_error
from app.core.rate_limit import rate_limit

router = APIRouter()

@router.websocket("/ws/form-analysis/{analysis_id}")
async def form_analysis_websocket(
    websocket: WebSocket,
    analysis_id: str,
    db: AsyncSession = Depends(deps.get_async_db)
):
    """
    WebSocket endpoint for real-time form analysis feedback.
    
    Provides:
    * Real-time pose detection results
    * Form correction feedback
    * Exercise progress updates
    * Joint angle measurements
    * Rep counting
    """
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Get feedback service
        feedback_service = FeedbackService(db)
        
        # Track connection
        track_websocket_connection(analysis_id=analysis_id, is_connected=True)
        
        try:
            # Subscribe to feedback updates
            await feedback_service.subscribe_to_feedback(analysis_id, websocket)
            
            # Keep connection alive and handle messages
            while True:
                data = await websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message_type == "request_feedback":
                    # Get latest feedback for the analysis
                    feedback = await feedback_service.get_latest_feedback(analysis_id)
                    await websocket.send_json({
                        "type": "feedback_update",
                        "data": feedback
                    })
                
        except WebSocketDisconnect:
            # Handle normal disconnection
            await feedback_service.unsubscribe_from_feedback(analysis_id, websocket)
            track_websocket_connection(analysis_id=analysis_id, is_connected=False)
            
        except Exception as e:
            # Handle other errors
            track_websocket_error(error_type=str(type(e).__name__))
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            
    except Exception as e:
        # Handle connection errors
        track_websocket_error(error_type=str(type(e).__name__))
        if websocket.client_state.CONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

@router.websocket("/ws/exercise-session/{session_id}")
async def exercise_session_websocket(
    websocket: WebSocket,
    session_id: str,
    db: AsyncSession = Depends(deps.get_async_db)
):
    """
    WebSocket endpoint for real-time exercise session feedback.
    
    Provides:
    * Real-time form analysis
    * Exercise progress tracking
    * Set and rep counting
    * Rest period timing
    * Overall session statistics
    """
    try:
        # Accept the WebSocket connection
        await websocket.accept()
        
        # Get feedback service
        feedback_service = FeedbackService(db)
        
        # Track connection
        track_websocket_connection(session_id=session_id, is_connected=True)
        
        try:
            # Subscribe to session updates
            await feedback_service.subscribe_to_session(session_id, websocket)
            
            # Keep connection alive and handle messages
            while True:
                data = await websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif message_type == "start_exercise":
                    # Start tracking a new exercise
                    exercise_type = data.get("exercise_type")
                    await feedback_service.start_exercise_tracking(
                        session_id=session_id,
                        exercise_type=exercise_type,
                        websocket=websocket
                    )
                elif message_type == "end_exercise":
                    # End current exercise tracking
                    await feedback_service.end_exercise_tracking(
                        session_id=session_id,
                        websocket=websocket
                    )
                elif message_type == "update_pose":
                    # Process new pose data
                    pose_data = data.get("pose_data")
                    await feedback_service.process_pose_update(
                        session_id=session_id,
                        pose_data=pose_data,
                        websocket=websocket
                    )
                
        except WebSocketDisconnect:
            # Handle normal disconnection
            await feedback_service.unsubscribe_from_session(session_id, websocket)
            track_websocket_connection(session_id=session_id, is_connected=False)
            
        except Exception as e:
            # Handle other errors
            track_websocket_error(error_type=str(type(e).__name__))
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            
    except Exception as e:
        # Handle connection errors
        track_websocket_error(error_type=str(type(e).__name__))
        if websocket.client_state.CONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR) 