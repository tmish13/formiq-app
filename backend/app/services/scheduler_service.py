"""Scheduler service for running periodic tasks."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Awaitable
import time

from app.core.logging import get_logger
from app.db.session import get_db
# from app.services.tasks import process_training_data_submissions, run_model_training # REMOVED - Tasks not found

logger = get_logger(__name__)

class SchedulerService:
    """Service for scheduling and running periodic tasks."""
    
    def __init__(self):
        """Initialize scheduler service."""
        self.tasks = {}
        self.is_running = False
        self.last_runs = {}
        
    async def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        self.is_running = True
        logger.info("Starting scheduler service")
        
        # Register default tasks
        # self.register_task("process_training_data", process_training_data_submissions, hours=1) # REMOVED - Task not found
        # self.register_task("run_model_training", run_model_training, days=7) # REMOVED - Task not found
        
        # Start the scheduler loop
        asyncio.create_task(self._scheduler_loop())
        
    async def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler service")
        self.is_running = False
        
    def register_task(
        self, 
        name: str, 
        task_func: Callable[[], Awaitable[Dict[str, Any]]], 
        **interval
    ):
        """
        Register a task to be run periodically.
        
        Args:
            name: Name of the task
            task_func: Async function to run
            interval: Keyword arguments specifying the interval (seconds, minutes, hours, days)
        """
        seconds = (
            interval.get("seconds", 0) +
            interval.get("minutes", 0) * 60 +
            interval.get("hours", 0) * 3600 +
            interval.get("days", 0) * 86400
        )
        
        if seconds < 1:
            logger.error(f"Invalid interval for task {name}: {interval}")
            return
            
        self.tasks[name] = {
            "func": task_func,
            "interval": seconds,
            "last_run": None
        }
        
        logger.info(f"Registered task '{name}' to run every {seconds} seconds")
        
    async def run_task(self, name: str) -> Dict[str, Any]:
        """
        Run a task immediately.
        
        Args:
            name: Name of the task to run
            
        Returns:
            Task result
        """
        if name not in self.tasks:
            logger.error(f"Task '{name}' not found")
            return {"status": "error", "error": f"Task '{name}' not found"}
            
        task = self.tasks[name]
        logger.info(f"Running task '{name}' immediately")
        
        try:
            result = await task["func"]()
            task["last_run"] = datetime.utcnow()
            
            return {
                "status": "success",
                "task": name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error running task '{name}': {str(e)}")
            return {
                "status": "error",
                "task": name,
                "error": str(e)
            }
            
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("Scheduler loop started")
        
        while self.is_running:
            now = datetime.utcnow()
            
            for name, task in self.tasks.items():
                # Skip if task has never run and is not due yet
                if task["last_run"] is None:
                    task["last_run"] = now
                    continue
                    
                # Check if task is due
                time_since_last_run = (now - task["last_run"]).total_seconds()
                
                if time_since_last_run >= task["interval"]:
                    logger.info(f"Task '{name}' is due, running now")
                    
                    try:
                        await task["func"]()
                        task["last_run"] = now
                        
                    except Exception as e:
                        logger.error(f"Error in scheduled task '{name}': {str(e)}")
                        
            # Sleep for a minute before checking again
            await asyncio.sleep(60)
            
# Singleton instance
scheduler = SchedulerService() 