"""
Background task manager for handling asynchronous processing of form checks
and other tasks that need to run outside the request-response cycle.
"""
import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Callable, Awaitable, Optional
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.core.cache import cache_service

logger = get_logger(__name__)

class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class Task:
    """Background task representation."""
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        timeout_seconds: int = 300
    ):
        """Initialize task.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task
            payload: Task payload data
            priority: Task priority (higher numbers have higher priority)
            timeout_seconds: Timeout for task execution in seconds
        """
        self.id = task_id
        self.type = task_type
        self.payload = payload
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.timeout_seconds = timeout_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary.
        
        Returns:
            Dictionary representation of task
        """
        return {
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "timeout_seconds": self.timeout_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary.
        
        Args:
            data: Dictionary with task data
            
        Returns:
            Task instance
        """
        task = cls(
            task_id=data["id"],
            task_type=data["type"],
            payload=data["payload"],
            priority=data.get("priority", 0),
            timeout_seconds=data.get("timeout_seconds", 300)
        )
        task.status = data.get("status", TaskStatus.PENDING)
        task.result = data.get("result")
        task.error = data.get("error")
        task.created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        task.started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        task.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        return task

class BackgroundTaskManager:
    """Manager for handling background tasks."""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        """Initialize background task manager.
        
        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.handlers: Dict[str, Callable[[Task], Awaitable[Any]]] = {}
        self.task_queue: asyncio.PriorityQueue = None
        self.active_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, Task] = {}
        self.worker_tasks: List[asyncio.Task] = []
        self._running = False
        self._shutdown_event = None
        self._lock = None
    
    async def start(self):
        """Start the background task manager."""
        if self._running:
            logger.warning("Background task manager already running")
            return
        
        self._running = True
        self.task_queue = asyncio.PriorityQueue()
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        # Start worker tasks
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(i))
            self.worker_tasks.append(worker)
        
        # Start monitor task
        monitor = asyncio.create_task(self._monitor())
        self.worker_tasks.append(monitor)
        
        # Load any persisted tasks from cache
        await self._load_persisted_tasks()
        
        logger.info(f"Background task manager started with {self.max_concurrent_tasks} workers")
    
    async def stop(self):
        """Stop the background task manager."""
        if not self._running:
            logger.warning("Background task manager not running")
            return
        
        logger.info("Shutting down background task manager...")
        self._running = False
        self._shutdown_event.set()
        
        # Wait for all worker tasks to complete
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        # Clear tasks
        self.worker_tasks = []
        
        # Persist any remaining tasks
        await self._persist_tasks()
        
        logger.info("Background task manager stopped")
    
    async def _worker(self, worker_id: int):
        """Worker task for processing background tasks.
        
        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Get task from queue with timeout
                try:
                    # Priority queue returns (priority, task_id, task)
                    priority, _, task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # Check if shutdown requested
                    if self._shutdown_event.is_set():
                        break
                    continue
                
                if task is None or self._shutdown_event.is_set():
                    self.task_queue.task_done()
                    break
                
                # Process task
                await self._process_task(worker_id, task)
                
                # Mark task as done in queue
                self.task_queue.task_done()
                
                # Check if shutdown requested
                if self._shutdown_event.is_set():
                    break
                    
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.exception(f"Worker {worker_id} error: {str(e)}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_task(self, worker_id: int, task: Task):
        """Process a task.
        
        Args:
            worker_id: Worker identifier
            task: Task to process
        """
        logger.info(f"Worker {worker_id} processing task {task.id} of type {task.type}")
        
        # Skip completed tasks
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            logger.info(f"Task {task.id} already processed, skipping")
            return
        
        # Track active task
        async with self._lock:
            self.active_tasks[task.id] = task
        
        # Mark task as running
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        # Save task state
        await self._save_task_state(task)
        
        # Get handler for task type
        handler = self.handlers.get(task.type)
        if not handler:
            logger.error(f"No handler registered for task type {task.type}")
            task.status = TaskStatus.FAILED
            task.error = f"No handler registered for task type {task.type}"
            task.completed_at = datetime.now()
            
            # Update active tasks
            async with self._lock:
                self.active_tasks.pop(task.id, None)
                self.task_results[task.id] = task
            
            # Save task state
            await self._save_task_state(task)
            return
        
        try:
            # Execute task with timeout
            task_timeout = task.timeout_seconds or 300  # Default 5 minutes
            
            result = await asyncio.wait_for(
                handler(task),
                timeout=task_timeout
            )
            
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            
            logger.info(f"Task {task.id} completed successfully")
            
        except asyncio.TimeoutError:
            # Task timed out
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task execution timed out after {task_timeout} seconds"
            task.completed_at = datetime.now()
            
            logger.error(f"Task {task.id} timed out after {task_timeout} seconds")
            
        except Exception as e:
            # Task failed
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            
            logger.exception(f"Task {task.id} failed: {str(e)}")
        
        # Update active tasks
        async with self._lock:
            self.active_tasks.pop(task.id, None)
            self.task_results[task.id] = task
        
        # Save task state
        await self._save_task_state(task)
    
    async def _monitor(self):
        """Monitor task for checking task timeouts and cleaning up results."""
        logger.info("Task monitor started")
        
        while self._running:
            try:
                # Sleep for a short time
                await asyncio.sleep(10)
                
                # Check if shutdown requested
                if self._shutdown_event.is_set():
                    break
                
                # Check for timed-out tasks
                now = datetime.now()
                timed_out_tasks = []
                
                async with self._lock:
                    for task_id, task in list(self.active_tasks.items()):
                        if task.started_at:
                            elapsed = (now - task.started_at).total_seconds()
                            if elapsed > task.timeout_seconds:
                                timed_out_tasks.append(task_id)
                                
                                # Mark task as timed out
                                task.status = TaskStatus.TIMEOUT
                                task.error = f"Task execution timed out after {task.timeout_seconds} seconds"
                                task.completed_at = now
                                
                                # Move to results
                                self.active_tasks.pop(task_id, None)
                                self.task_results[task_id] = task
                                
                                # Save task state
                                await self._save_task_state(task)
                
                if timed_out_tasks:
                    logger.warning(f"Detected {len(timed_out_tasks)} timed out tasks: {timed_out_tasks}")
                
                # Clean up old results (older than 1 hour)
                cleanup_time = now - timedelta(hours=1)
                
                async with self._lock:
                    for task_id, task in list(self.task_results.items()):
                        if task.completed_at and task.completed_at < cleanup_time:
                            self.task_results.pop(task_id, None)
                            
                            # Delete task state from cache
                            if cache_service.available:
                                await cache_service.delete(f"task:{task_id}")
                
            except asyncio.CancelledError:
                logger.info("Task monitor cancelled")
                break
            except Exception as e:
                logger.exception(f"Task monitor error: {str(e)}")
        
        logger.info("Task monitor stopped")
    
    async def enqueue_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
        priority: int = 0,
        timeout_seconds: int = 300
    ) -> str:
        """Enqueue a new task.
        
        Args:
            task_type: Type of task
            payload: Task payload data
            task_id: Optional task identifier (generated if not provided)
            priority: Task priority (higher numbers have higher priority)
            timeout_seconds: Timeout for task execution in seconds
            
        Returns:
            Task identifier
        """
        if not self._running:
            raise RuntimeError("Background task manager not running")
        
        # Generate task ID if not provided
        task_id = task_id or str(uuid.uuid4())
        
        # Create task
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        # Save task state
        await self._save_task_state(task)
        
        # Priority queue inverts priority (lower numbers are higher priority)
        await self.task_queue.put((-priority, task_id, task))
        
        logger.info(f"Task {task_id} of type {task_type} enqueued with priority {priority}")
        
        return task_id
    
    def register_handler(self, task_type: str, handler: Callable[[Task], Awaitable[Any]]):
        """Register a handler for a task type.
        
        Args:
            task_type: Type of task
            handler: Async function to handle the task
        """
        self.handlers[task_type] = handler
        logger.info(f"Handler registered for task type {task_type}")
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status or None if task not found
        """
        # Check active tasks
        async with self._lock:
            task = self.active_tasks.get(task_id)
            if task:
                return task.to_dict()
        
        # Check task results
        async with self._lock:
            task = self.task_results.get(task_id)
            if task:
                return task.to_dict()
        
        # Check cache
        if cache_service.available:
            task_data = await cache_service.get(f"task:{task_id}")
            if task_data:
                task = Task.from_dict(task_data)
                return task.to_dict()
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False otherwise
        """
        # Currently only supports cancelling tasks that haven't started
        # For running tasks, would need task-specific cancellation logic
        
        # Check if task is in active tasks
        async with self._lock:
            if task_id in self.active_tasks:
                # Can't cancel active tasks directly
                return False
        
        # Get task from cache
        if cache_service.available:
            task_data = await cache_service.get(f"task:{task_id}")
            if task_data:
                task = Task.from_dict(task_data)
                
                # Only cancel pending tasks
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now()
                    
                    # Save updated state
                    await self._save_task_state(task)
                    
                    logger.info(f"Task {task_id} cancelled")
                    return True
        
        return False
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the task queue.
        
        Returns:
            Queue statistics
        """
        pending_count = self.task_queue.qsize()
        
        async with self._lock:
            active_count = len(self.active_tasks)
            completed_count = len([t for t in self.task_results.values() 
                                 if t.status == TaskStatus.COMPLETED])
            failed_count = len([t for t in self.task_results.values() 
                              if t.status in [TaskStatus.FAILED, TaskStatus.TIMEOUT]])
        
        return {
            "pending": pending_count,
            "active": active_count,
            "completed": completed_count,
            "failed": failed_count,
            "workers": self.max_concurrent_tasks,
            "running": self._running
        }
    
    async def _save_task_state(self, task: Task):
        """Save task state to cache.
        
        Args:
            task: Task to save
        """
        if cache_service.available:
            task_data = task.to_dict()
            await cache_service.set(f"task:{task.id}", task_data, expire=3600)  # 1 hour TTL
    
    async def _load_persisted_tasks(self):
        """Load persisted tasks from cache."""
        if not cache_service.available:
            return
        
        try:
            # Get all task keys
            keys = await cache_service.keys("task:*")
            
            if not keys:
                return
            
            logger.info(f"Loading {len(keys)} persisted tasks")
            
            # Load tasks
            for key in keys:
                task_data = await cache_service.get(key)
                if task_data:
                    task = Task.from_dict(task_data)
                    
                    # Only requeue pending tasks
                    if task.status == TaskStatus.PENDING:
                        # Priority queue inverts priority
                        await self.task_queue.put((-task.priority, task.id, task))
                        logger.info(f"Requeued persisted task {task.id}")
                    
                    # Add completed/failed tasks to results
                    elif task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
                        async with self._lock:
                            self.task_results[task.id] = task
        
        except Exception as e:
            logger.exception(f"Error loading persisted tasks: {str(e)}")
    
    async def _persist_tasks(self):
        """Persist all tasks to cache."""
        if not cache_service.available:
            return
        
        try:
            # Persist active tasks
            async with self._lock:
                for task in self.active_tasks.values():
                    await self._save_task_state(task)
            
            # Get all pending tasks from queue
            pending_tasks = []
            while not self.task_queue.empty():
                try:
                    _, _, task = self.task_queue.get_nowait()
                    pending_tasks.append(task)
                    self.task_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            
            # Persist pending tasks
            for task in pending_tasks:
                await self._save_task_state(task)
            
            logger.info(f"Persisted {len(self.active_tasks)} active and {len(pending_tasks)} pending tasks")
            
        except Exception as e:
            logger.exception(f"Error persisting tasks: {str(e)}")

# Task type constants
class TaskTypes:
    """Task type constants."""
    FORM_CHECK_ANALYSIS = "form_check_analysis"
    VIDEO_PROCESSING = "video_processing"
    EMAIL_NOTIFICATION = "email_notification"

# Initialize handlers for form check analysis
async def form_check_handler(task: Task) -> Dict[str, Any]:
    """Handler for form check analysis tasks.
    
    Args:
        task: Task data
        
    Returns:
        Analysis results
    """
    # This would contain the actual form check analysis logic
    # For now, just a placeholder
    
    form_check_id = task.payload.get("form_check_id")
    logger.info(f"Processing form check analysis for {form_check_id}")
    
    # Simulate processing time
    await asyncio.sleep(2)
    
    # Return mock results
    return {
        "form_check_id": form_check_id,
        "completed": True,
        "score": 85,
        "issues_detected": 2,
        "processing_time_sec": 2
    }

# Function for enqueueing a form check analysis
async def enqueue_form_check_analysis(
    form_check_id: str,
    priority: int = 0,
    background_task_manager: Optional[BackgroundTaskManager] = None
) -> str:
    """Enqueue a form check for analysis.
    
    Args:
        form_check_id: Form check identifier
        priority: Task priority
        background_task_manager: Optional task manager instance
        
    Returns:
        Task identifier
    """
    # Lazy import to avoid circular imports
    from app.main import background_task_manager as default_manager
    
    manager = background_task_manager or default_manager
    
    # Enqueue task
    task_id = await manager.enqueue_task(
        task_type=TaskTypes.FORM_CHECK_ANALYSIS,
        payload={"form_check_id": form_check_id},
        priority=priority,
        timeout_seconds=300  # 5 minutes
    )
    
    logger.info(f"Form check {form_check_id} enqueued for analysis as task {task_id}")
    
    return task_id

# Register handlers
def register_task_handlers(manager: BackgroundTaskManager):
    """Register task handlers with the manager.
    
    Args:
        manager: Background task manager
    """
    manager.register_handler(TaskTypes.FORM_CHECK_ANALYSIS, form_check_handler) 