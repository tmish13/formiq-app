"""Admin router for system administration tasks."""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.models.user import User
from app.core.auth import get_current_admin_user
from app.db.session import get_db
from app.services.scheduler_service import scheduler
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/tasks/run/{task_name}")
async def run_task(
    task_name: str,
    admin_user: User = Depends(get_current_admin_user),
):
    """
    Run a scheduled task immediately.
    
    Args:
        task_name: Name of the task to run
        
    Returns:
        Task result
    """
    logger.info(f"Admin user {admin_user.id} requested to run task '{task_name}'")
    
    # Check if task exists
    if task_name not in scheduler.tasks:
        available_tasks = list(scheduler.tasks.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_name}' not found. Available tasks: {available_tasks}"
        )
        
    # Run the task
    result = await scheduler.run_task(task_name)
    return result

@router.get("/tasks")
async def list_tasks(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    List all registered tasks.
    
    Returns:
        List of tasks with their status
    """
    tasks = []
    now = datetime.utcnow()
    
    for name, task in scheduler.tasks.items():
        # Calculate next run time
        next_run = None
        if task["last_run"]:
            next_run = task["last_run"] + timedelta(seconds=task["interval"])
            
        tasks.append({
            "name": name,
            "interval_seconds": task["interval"],
            "last_run": task["last_run"],
            "next_run": next_run,
            "status": "active" if scheduler.is_running else "paused"
        })
        
    return {"tasks": tasks}

@router.post("/tasks/schedule/{task_name}")
async def schedule_task(
    task_name: str,
    interval: Dict[str, int] = Body(...),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Reschedule a task with a new interval.
    
    Args:
        task_name: Name of the task to reschedule
        interval: Dictionary with interval parameters (seconds, minutes, hours, days)
        
    Returns:
        Updated task information
    """
    # Check if task exists
    if task_name not in scheduler.tasks:
        raise HTTPException(
            status_code=404, 
            detail=f"Task '{task_name}' not found"
        )
        
    # Update the task interval
    scheduler.register_task(
        task_name, 
        scheduler.tasks[task_name]["func"],
        **interval
    )
    
    return {
        "status": "success",
        "task": task_name,
        "interval": interval
    }

@router.post("/scheduler/start")
async def start_scheduler(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Start the scheduler if it's not already running.
    
    Returns:
        Status message
    """
    if scheduler.is_running:
        return {"status": "already_running"}
        
    await scheduler.start()
    return {"status": "started"}

@router.post("/scheduler/stop")
async def stop_scheduler(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Stop the scheduler if it's running.
    
    Returns:
        Status message
    """
    if not scheduler.is_running:
        return {"status": "not_running"}
        
    await scheduler.stop()
    return {"status": "stopped"} 