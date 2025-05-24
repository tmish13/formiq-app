import sys
import os
import pytest
import importlib
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.video_processing_service import VideoProcessingService

@pytest.fixture(autouse=True, scope="session")
def manipulate_sys_path_for_tests():
    original_sys_path = list(sys.path)
    original_modules = dict(sys.modules)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    print(f"[CONFLOG] Initial sys.path: {sys.path}")
    print(f"[CONFLOG] backend_dir: {backend_dir}")
    print(f"[CONFLOG] workspace_root: {workspace_root}")

    # Remove workspace root if it's there to avoid picking up top-level 'app/'
    if workspace_root in sys.path:
        sys.path.remove(workspace_root)
        print(f"[CONFLOG] Removed '{workspace_root}' from sys.path")
    
    # Ensure backend directory is at the start
    if backend_dir in sys.path:
        sys.path.remove(backend_dir) # Remove if it exists, to ensure it's at pos 0
        print(f"[CONFLOG] Removed '{backend_dir}' from sys.path to re-insert at 0")
    sys.path.insert(0, backend_dir)
    print(f"[CONFLOG] Inserted '{backend_dir}' at sys.path[0]")

    # Attempt to clear any potentially cached 'app' module that might be the wrong one
    if 'app' in sys.modules:
        app_module = sys.modules['app']
        app_file_path = getattr(app_module, '__file__', '')
        print(f"[CONFLOG] Found sys.modules['app']: {app_module} with path {app_file_path}")
        if app_file_path and app_file_path.startswith(os.path.join(workspace_root, 'app')):
            del sys.modules['app']
            print(f"[CONFLOG] Removed potentially conflicting sys.modules['app'] from {app_file_path}")

    print(f"[CONFLOG] sys.path before pre-imports: {sys.path}")
    # Pre-import backend.app and backend.app.tasks to ensure they are loaded correctly
    try:
        print(f"[CONFLOG] Attempting to import backend.app")
        backend_app_module = importlib.import_module('backend.app')
        print(f"[CONFLOG] Successfully imported backend.app: {backend_app_module} with __path__ {getattr(backend_app_module, '__path__', 'N/A')}")
        
        if hasattr(backend_app_module, 'tasks'):
            print("[CONFLOG] backend.app module HAS 'tasks' attribute before importing .tasks directly.")
        else:
            print("[CONFLOG] backend.app module does NOT have 'tasks' attribute before importing .tasks directly.")
        
        print("[CONFLOG] Attempting to import backend.app.tasks")
        backend_app_tasks_module = importlib.import_module('backend.app.tasks')
        print(f"[CONFLOG] Successfully imported backend.app.tasks: {backend_app_tasks_module}")
        
        if hasattr(backend_app_module, 'tasks'):
            print("[CONFLOG] After importing .tasks, backend.app module now HAS 'tasks' attribute.")
        else:
            print("[CONFLOG] After importing .tasks, backend.app module STILL does NOT have 'tasks' attribute.")

    except ImportError as e:
        print(f"[CONFLOG] Error pre-importing backend.app or backend.app.tasks: {e}")
        import traceback
        traceback.print_exc()

    print(f"[CONFLOG] Final sys.path for test session: {sys.path}")
    yield
    
    sys.path = original_sys_path
    sys.modules = original_modules
    print("[CONFLOG] Restored sys.path and sys.modules")

# Ensure no other sys.path manipulations from previous attempts remain.

    # And the tasks path
    backend_tasks_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app', 'tasks'))
    if backend_tasks_path not in sys.path:
        sys.path.insert(0, backend_tasks_path)

    # This is getting complicated. The pythonpath=. in backend/pytest.ini SHOULD be sufficient.
    # The error `AttributeError: module 'app' has no attribute 'tasks'` when patching `app.tasks...`
    # means `importlib.import_module('app')` worked, but that `app` module didn't have `tasks`.
    # This screams that the wrong `app` was imported.

    # Final attempt with sys.path manipulation: ensure `backend` dir is at the front.
    backend_root_for_imports = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # This is /Users/tarpanmishra/formiq-app-5/backend
    if backend_root_for_imports not in sys.path:
        sys.path.insert(0, backend_root_for_imports)
    # Now, `import app` should resolve to `backend/app`. 

@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)

    # Define the mock for the object that .first() will return
    mock_first_return = None # Default, tests can override by drilling down

    # Define the .first() method mock on the ScalarResult mock
    mock_first_method = MagicMock(return_value=mock_first_return)

    # Define the mock for the ScalarResult object
    mock_scalar_result = MagicMock() # This object will have a .first() method
    mock_scalar_result.first = mock_first_method

    # Define the .scalars() method mock on the Result mock
    mock_scalars_method = MagicMock(return_value=mock_scalar_result)

    # Define the mock for the Result object
    mock_result = MagicMock() # This object will have a .scalars() method
    mock_result.scalars = mock_scalars_method

    # session.execute is an async method. When awaited, it returns mock_result.
    session.execute = AsyncMock(return_value=mock_result)
    
    # Example for test configuration:
    # new_return_value_for_first = Video(...)
    # mock_db_session.execute.return_value.scalars.return_value.first.return_value = new_return_value_for_first

    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.close = AsyncMock()
    return session

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.MAX_VIDEO_DURATION = 300  # seconds
    settings.MIN_VIDEO_DURATION = 1    # seconds
    settings.MIN_VIDEO_FPS = 10
    settings.MIN_VIDEO_FRAMES = 50
    settings.TARGET_FPS = 30
    settings.TARGET_WIDTH = 640
    settings.TARGET_HEIGHT = 480
    settings.FFMPEG_PATH = "ffmpeg"
    settings.FFPROBE_PATH = "ffprobe"
    settings.FFMPEG_TIMEOUT = 60
    settings.AI_TARGET_FRAME_WIDTH = 256
    settings.AI_TARGET_FRAME_HEIGHT = 256
    settings.TMP_FILE_STORAGE_PATH = "/tmp/formiq_tests"
    return settings

@pytest.fixture
def video_processing_service(mock_settings: MagicMock) -> VideoProcessingService:
    # Ensure VideoProcessingService is imported here if not already globally for the conftest
    service = VideoProcessingService(app_settings=mock_settings)
    return service

@pytest.fixture
def mock_celery_task_module(monkeypatch):
    mock_module = MagicMock()
    mock_module.process_video_celery_task = MagicMock()
    mock_module.process_video_celery_task.delay = MagicMock() 
    
    monkeypatch.setitem(
        sys.modules, "app.tasks.video_tasks", mock_module
    )
    return mock_module

# You might want to add other common fixtures here, for example:
# - mock_app_settings
# - mock_storage_service
# - A fixture for a generic Video object instance 