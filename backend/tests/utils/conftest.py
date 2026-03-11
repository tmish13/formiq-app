"""Test configuration module."""
import os
from pathlib import Path
from dotenv import load_dotenv
import pytest
import asyncio
from typing import AsyncGenerator, Generator, Dict, List
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient
import pytest_asyncio
from sqlalchemy.pool import StaticPool
import shutil
from sqlalchemy import create_engine, text, inspect
import subprocess
import sys
import importlib
from sqlalchemy.schema import MetaData
from sqlalchemy import inspect as sqlalchemy_inspect
from alembic import command as alembic_command
import logging
from prometheus_client import REGISTRY
from sqlalchemy import event

from app.core.config import settings, get_settings
from app.db.base_class import Base
from app.core.security import create_access_token
from app.core.password import get_password_hash
from app.core.security import create_access_token, get_password_hash
from app.core.cache import cache_service
from app.db.session import get_async_db as app_get_async_db
from tests.utils.test_utils import MockRedis
from datetime import datetime, timedelta
from app.core import security
from tests.mocks.mock_lifespan import mock_lifespan

# Import models needed for fixture type hints
from app.models.user import User
from app.models.video import Video
from app.models.form_check import FormCheck
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.enums import VideoStatus

# Load test environment variables before importing other modules
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(test_env_path)

# Set test environment
os.environ["ENVIRONMENT"] = "test"

# Clear settings cache to reload with test environment
get_settings.cache_clear()

# Create test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for tests
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool
)

# Add event listener for PRAGMA foreign_keys=ON for SQLite for the test_engine
if test_engine.dialect.name == "sqlite":
    @event.listens_for(test_engine.sync_engine, "connect")
    def set_sqlite_pragma_test_engine(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            print("CONTEST.PY (test_engine event): Attempting to execute PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA foreign_keys=ON")
            dbapi_connection.commit()
            print("CONTEST.PY (test_engine event): PRAGMA foreign_keys=ON executed successfully.")
            cursor.execute("PRAGMA foreign_keys")
            fk_status = cursor.fetchone()
            print(f"CONTEST.PY (test_engine event): PRAGMA foreign_keys status: {fk_status}")
        except Exception as e:
            print(f"CONTEST.PY (test_engine event): FAILED to execute PRAGMA foreign_keys=ON. Error: {e}")
        finally:
            cursor.close()

# Create async session factory for tests
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

print(f"CONTEST.PY TOP LEVEL: sys.path = {sys.path}\n")

try:
    from alembic.config import Config as AlembicConfig
    print("CONTEST.PY: Successfully imported AlembicConfig\n")
except Exception as e:
    print(f"CONTEST.PY: FAILED to import AlembicConfig. Error: {e}\n")
    print(f"CONTEST.PY (on error): sys.path = {sys.path}\n")
    raise

def import_all_models():
    """
    Imports or reloads all SQLAlchemy model modules to ensure they register
    with the current Base.metadata. This is crucial after Base.metadata.clear()
    to handle cases where modules might have been imported earlier.
    """
    import importlib
    import sys
    from app.db.base_class import Base # Ensure we're talking about the same Base

    print(f"IMPORT_ALL_MODELS: Starting. id(Base.metadata) = {id(Base.metadata)}")
    print(f"IMPORT_ALL_MODELS: Tables before reload: {list(Base.metadata.tables.keys())}")

    # List of model modules to reload/import.
    # Derived from app.models.__init__.py
    model_module_names = [
        "app.models.base",  # Contains BaseModel
        "app.models.subscription",
        "app.models.user",
        "app.models.form_check",
        "app.models.workout",
        "app.models.user_settings",
        "app.models.user_session",
        "app.models.video",
        "app.models.exercise",      # Contains ExerciseTemplate
        "app.models.exercise_config",
        "app.models.progress",      # Contains ExerciseProgress, ProgressSnapshot
        # app.models.enums is not needed as it doesn't contain SQLAlchemy models
    ]

    # After models are reloaded, reload factories that depend on them
    factory_module_name = "tests.factories"

    for module_name in model_module_names:
        try:
            if module_name in sys.modules:
                print(f"IMPORT_ALL_MODELS: Reloading module: {module_name}")
                importlib.reload(sys.modules[module_name])
            else:
                print(f"IMPORT_ALL_MODELS: Importing module: {module_name}")
                importlib.import_module(module_name)
            # Optional: print id(Base.metadata) from within the reloaded module if it has a test print
        except Exception as e:
            print(f"IMPORT_ALL_MODELS: Error processing module {module_name}: {e}")
            # Depending on severity, you might want to raise e

    # Now reload the factory module
    try:
        if factory_module_name in sys.modules:
            print(f"IMPORT_ALL_MODELS: Reloading factory module: {factory_module_name}")
            importlib.reload(sys.modules[factory_module_name])
        else:
            print(f"IMPORT_ALL_MODELS: Importing factory module: {factory_module_name}")
            importlib.import_module(factory_module_name)
    except Exception as e:
        print(f"IMPORT_ALL_MODELS: Error processing factory module {factory_module_name}: {e}")

    print(f"IMPORT_ALL_MODELS: Finished. id(Base.metadata) = {id(Base.metadata)}")
    print(f"IMPORT_ALL_MODELS: Tables after reload: {list(Base.metadata.tables.keys())}")

logger = logging.getLogger(__name__)

# Load settings once
settings = get_settings()

# Configure logging for SQLAlchemy and Alembic to DEBUG
import logging
logging.basicConfig(level=logging.DEBUG) # Set default level for root logger
logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.dialects.sqlite').setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.orm').setLevel(logging.DEBUG)
logging.getLogger('alembic').setLevel(logging.DEBUG)

async def run_migrations():
    """Applies Alembic migrations to the test database."""
    print("RUN_MIGRATIONS: STARTING")
    alembic_cfg_path = Path(__file__).parent.parent / "alembic.ini"
    resolved_path = alembic_cfg_path.resolve()
    print(f"RUN_MIGRATIONS: Alembic config path: {resolved_path}")

    if not alembic_cfg_path.exists():
        print(f"RUN_MIGRATIONS: ERROR - Alembic config file not found at {resolved_path}")
        return False

    alembic_cfg = AlembicConfig(str(alembic_cfg_path))
    
    # Use the synchronous test DB URI for migrations
    # Ensure this is correctly pointing to your test SQLite DB file path
    sync_db_url = settings.SQLALCHEMY_DATABASE_URI
    if not sync_db_url:
        print("RUN_MIGRATIONS: ERROR - TEST_SQLALCHEMY_DATABASE_URI is not set.")
        return False
        
    print(f"RUN_MIGRATIONS: Setting Alembic 'sqlalchemy.url' to: {sync_db_url}")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_db_url)
    
    # Explicitly set script_location. 
    # The CWD of pytest execution is /Users/tarpanmishra/formiq-app-5 (project root)
    # The migrations directory is at backend/migrations/
    script_dir_path = "backend/migrations"
    print(f"RUN_MIGRATIONS: Explicitly setting Alembic 'script_location' to: {script_dir_path}")
    alembic_cfg.set_main_option("script_location", script_dir_path)
    
    try:
        print("RUN_MIGRATIONS: BEFORE ALEMBIC UPGRADE")
        # Ensure Alembic commands are logged
        # You might need to configure Alembic's logger if it doesn't print by default
        alembic_command.upgrade(alembic_cfg, "head")
        print("RUN_MIGRATIONS: ALEMBIC SUCCEEDED")
        print("RUN_MIGRATIONS: FINISHING")
        return True
    except Exception as e:
        print(f"RUN_MIGRATIONS: ALEMBIC FAILED: {e}")
        # For more detailed Alembic error, you might need to inspect 'e' further
        # or configure Alembic's logging to be more verbose.
        # import traceback
        # print(f"RUN_MIGRATIONS: Traceback: {traceback.format_exc()}")
        print("RUN_MIGRATIONS: FINISHING WITH FAILURE")
        return False

@pytest.fixture(scope="session")
async def test_app(initialize_test_db: None) -> FastAPI:
    """Create a FastAPI app instance for testing."""
    from app.main import app  # Import here to avoid issues with settings
    # TODO: Configure app for testing (e.g., override dependencies)
    # app.dependency_overrides[get_settings] = get_test_settings
    return app

@pytest.fixture(scope="session")
def initialize_test_db():
    """
    Initializes the test database by running Alembic migrations.
    This fixture has session scope, so it runs once per test session.
    It ensures that all tables are created before any tests run.
    It now calls the synchronous run_migrations function.
    AND it deletes the old test.db file first.
    """
    print("INITIALIZE_TEST_DB: STARTING")

    # Dispose of previous mapper configurations and clear metadata
    print("INITIALIZE_TEST_DB: Disposing of Base.registry")
    try:
        Base.registry.dispose()
        print("INITIALIZE_TEST_DB: Base.registry.dispose() called successfully.")
    except Exception as e:
        print(f"INITIALIZE_TEST_DB: Error during Base.registry.dispose(): {e}")
        # Continue anyway, as clear() might still be useful

    print("INITIALIZE_TEST_DB: Clearing Base.metadata")
    Base.metadata.clear()
    print("INITIALIZE_TEST_DB: Calling import_all_models() to register models")
    import_all_models() # Ensure all models are known to the cleared Base.metadata

    # Delete the old test database file if it exists to ensure a clean slate
    # The synchronous DB URL is used by Alembic, so that's the one to derive the path from.
    # settings.SQLALCHEMY_DATABASE_URI is like "sqlite:///./test.db"
    # settings.TEST_SQLALCHEMY_DATABASE_URI is like "sqlite+aiosqlite:///./test.db"
    sync_db_url_for_path = settings.SQLALCHEMY_DATABASE_URI 
    if sync_db_url_for_path.startswith("sqlite:///./"):
        test_db_filename = sync_db_url_for_path[len("sqlite:///./"):]
        # Assuming conftest.py is in backend/tests/, and test.db is in backend/
        # So, the path from conftest.py would be ../test.db
        # However, pytest usually runs from the project root (backend/ in this case)
        # and paths like "./test.db" are relative to where pytest is run.
        # Let's assume test.db is in the CWD of pytest (backend/)
        test_db_path = Path(test_db_filename).resolve()
        print(f"INITIALIZE_TEST_DB: Attempting to locate test database at: {test_db_path}")
        if test_db_path.exists():
            print(f"INITIALIZE_TEST_DB: Removing existing test database file: {test_db_path}")
            try:
                test_db_path.unlink()
                print(f"INITIALIZE_TEST_DB: Successfully removed {test_db_path}")
            except OSError as e:
                print(f"INITIALIZE_TEST_DB: FAILED to remove {test_db_path}. Error: {e}")
                pytest.fail(f"INITIALIZE_TEST_DB: Could not remove existing test.db. Error: {e}", pytrace=False)
        else:
            print(f"INITIALIZE_TEST_DB: No existing test database file found at {test_db_path}. Proceeding.")
    else:
        print(f"INITIALIZE_TEST_DB: Could not determine test_db_path fromSQLALCHEMY_DATABASE_URI: {sync_db_url_for_path}")

    # print(f"INITIALIZE_TEST_DB: Using settings: SQLALCHEMY_DATABASE_URI={settings.SQLALCHEMY_DATABASE_URI}, TEST_SQLALCHEMY_DATABASE_URI={settings.TEST_SQLALCHEMY_DATABASE_URI}") # DEBUG

    # We need a synchronous function to be called by asyncio.run() if run_migrations itself is async
    # Or, if run_migrations can be made fully synchronous, call it directly.
    # For now, assuming run_migrations is async as previously designed for potential async DB operations
    print("INITIALIZE_TEST_DB: BEFORE ASYNCIO.RUN(RUN_MIGRATIONS)")
    success = asyncio.run(run_migrations())
    print(f"INITIALIZE_TEST_DB: AFTER ASYNCIO.RUN(RUN_MIGRATIONS) - Success: {success}")
    
    if not success:
        pytest.fail("INITIALIZE_TEST_DB: Migrations failed. Aborting test session.", pytrace=False)

    print("INITIALIZE_TEST_DB: YIELDING")
    yield
    
    # Optional: Teardown - for example, deleting the test database file
    # test_db_path_str = settings.TEST_SQLALCHEMY_DATABASE_URI.replace("sqlite+aiosqlite:///", "")
    # test_db_path = Path(test_db_path_str)
    # if test_db_path.exists():
    #     print(f"INITIALIZE_TEST_DB: Removing test database file: {test_db_path}")
    #     test_db_path.unlink()
    # else:
    #     print(f"INITIALIZE_TEST_DB: Test database file not found for removal: {test_db_path}")
    print("INITIALIZE_TEST_DB: TEARDOWN COMPLETE (if any)")

@pytest.fixture(autouse=True)
async def setup_database(initialize_test_db: None):
    """Set up the test database for each test."""
    print(f"SETUP_DATABASE for test entered at {datetime.utcnow()}")
    # import_all_models() # Ensure models are registered. This is now primarily done by initialize_test_db
    # Let's ensure models are imported for mapper configuration, but rely on Alembic for schema.
    from app.models.user import User
    from app.models.user_session import UserSession
    # Other models can be imported here if needed by tests directly, but schema should exist.
    print(f"SETUP_DATABASE: User imported: {User}, UserSession imported: {UserSession}")

    async with test_engine.connect() as conn:
        print(f"SETUP_DATABASE: Connection acquired: {conn}")
        print("SETUP_DATABASE: Transaction management will be handled by specific operations or implicitly.")
        print("SETUP_DATABASE: Relying on Alembic migrations from initialize_test_db for table creation.")

        # Explicit table creation calls removed.
        # print("Attempting to create User table explicitly via run_sync.")
        # try:
        #     await conn.run_sync(User.__table__.create, checkfirst=True)
        #     print("SETUP_DATABASE: User table CREATION SUCCEEDED (or already existed) via run_sync.")
        # except Exception as e:
        #     print(f"SETUP_DATABASE: User table CREATION FAILED via run_sync: {e}")

        # print("Attempting to create UserSession table explicitly via run_sync.")
        # try:
        #     await conn.run_sync(UserSession.__table__.create, checkfirst=True)
        #     print("SETUP_DATABASE: UserSession table CREATION SUCCEEDED (or already existed) via run_sync.")
        # except Exception as e:
        #     print(f"SETUP_DATABASE: UserSession table CREATION FAILED via run_sync: {e}")
        
        # Base.metadata.create_all call removed.
        # print("SETUP_DATABASE: BEFORE Base.metadata.create_all(conn)")
        # try:
        #     await conn.run_sync(Base.metadata.create_all)
        #     print("SETUP_DATABASE: Base.metadata.create_all(conn) SUCCEEDED.")
        # except Exception as e:
        #     print(f"SETUP_DATABASE: Base.metadata.create_all(conn) FAILED: {e}")
        
        # Diagnostic: Inspect tables (optional, can be kept for now)
        try:
            print("SETUP_DATABASE: Attempting to inspect tables in metadata...")
            # Correct way to use inspect with run_sync for an AsyncConnection
            # Get table names directly within the run_sync lambda
            tables_in_db = await conn.run_sync(
                lambda sync_conn: sqlalchemy_inspect(sync_conn).get_table_names()
            )
            print(f"SETUP_DATABASE: Tables reported by inspector: {tables_in_db}")
            print(f"SETUP_DATABASE: Tables in Base.metadata.tables (after imports): {list(Base.metadata.tables.keys())}")

            # Accessing sorted_tables might still be useful for diagnostics if needed
            # print("SETUP_DATABASE: Accessing Base.metadata.sorted_tables...")
            # sorted_tables = Base.metadata.sorted_tables
            # print(f"SETUP_DATABASE: Successfully accessed Base.metadata.sorted_tables. Count: {len(sorted_tables)}")
            # for table in sorted_tables:
            #     print(f"SETUP_DATABASE: Sorted table: {table.name}")

        except Exception as e:
            print(f"SETUP_DATABASE: ERROR during metadata inspection: {e}")

        print("SETUP_DATABASE: Yielding to test execution.")
        yield
        print("SETUP_DATABASE: Test execution finished. Dropping tables.")

        try:
            print("SETUP_DATABASE: BEFORE Base.metadata.drop_all(conn)")
            # We might still want to drop all to clean up data inserted by tests, 
            # even if schema creation is by Alembic.
            await conn.run_sync(Base.metadata.drop_all) 
            print("SETUP_DATABASE: Base.metadata.drop_all(conn) SUCCEEDED.")
        except Exception as e:
            print(f"SETUP_DATABASE: Base.metadata.drop_all(conn) FAILED: {e}")
        
    print(f"SETUP_DATABASE for test finished at {datetime.utcnow()}")

@pytest.fixture
async def db_session(initialize_test_db: None) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for a test."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def client(db_session: AsyncSession, test_app: FastAPI) -> Generator:
    """Create a test client with a fresh database session."""
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[app_get_async_db] = override_get_db
    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()

@pytest.fixture
async def test_user(async_session: AsyncSession):
    """Create a test user."""
    # Check if user already exists to prevent unique constraint errors if tests run in a way that doesn't fully isolate
    existing_user_stmt = select(User).where(User.email == "test@example.com")
    existing_user_result = await async_session.execute(existing_user_stmt)
    existing_user = existing_user_result.scalars().first()
    if existing_user:
        return existing_user

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_superuser=False,
        is_verified=True
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user

@pytest.fixture
async def test_superuser(async_session: AsyncSession):
    """Create a test superuser."""
    existing_user_stmt = select(User).where(User.email == "admin@example.com")
    existing_user_result = await async_session.execute(existing_user_stmt)
    existing_user = existing_user_result.scalars().first()
    if existing_user:
        return existing_user
        
    user = User(
        email="admin@example.com",
        username="superadmin",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_superuser=True,
        is_verified=True
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user

@pytest.fixture
async def test_user_token(test_user: User) -> str:
    """Generate an access token for the test_user."""
    return create_access_token(subject=str(test_user.id))

@pytest.fixture
async def current_user_headers(test_user_token: str) -> Dict[str, str]:
    """Create authorization headers for the test_user."""
    return {"Authorization": f"Bearer {test_user_token}"}

@pytest.fixture
async def test_video(async_session: AsyncSession, test_user: User) -> Video:
    """Create a test video."""
    video = Video(
        user_id=test_user.id,
        filename="test_video.mp4",
        status=VideoStatus.PENDING,
        url="https://example.com/test_video.mp4",
        mime_type="video/mp4"
    )
    async_session.add(video)
    await async_session.commit()
    await async_session.refresh(video)
    return video

@pytest.fixture
async def test_form_check(async_session: AsyncSession, test_video: Video) -> FormCheck:
    """Create a test form check."""
    form_check = FormCheck(
        video_id=test_video.id,
        score=85,
        feedback="Good form",
        joint_angles={"hip": 90, "knee": 90},
        spine_alignment=0.95,
        symmetry_score=0.85
    )
    async_session.add(form_check)
    await async_session.commit()
    await async_session.refresh(form_check)
    return form_check

@pytest.fixture
def test_video_file(tmp_path) -> str:
    """Create a test video file."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_bytes(b"fake video data")
    return str(video_path)

@pytest.fixture
def mock_video_processor():
    """Create a mock video processor."""
    class MockVideoProcessor:
        async def process_video(self, video_path: str) -> dict:
            return {
                "status": "completed",
                "poses": [{"keypoints": [{"x": 100, "y": 100, "score": 0.9}]}]
            }

        async def extract_frames(self, video_path: str) -> list:
            return ["frame1", "frame2"]

        async def analyze_form(self, frames: list) -> dict:
            return {
                "score": 85,
                "feedback": "Good form",
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85
            }

    return MockVideoProcessor()

@pytest.fixture
def mock_storage_service():
    """Create a mock storage service."""
    class MockStorageService:
        async def upload_file(self, file_path: str, destination: str) -> str:
            return f"https://example.com/{destination}"

        async def download_file(self, file_path: str, destination: str) -> str:
            return destination

        async def delete_file(self, file_path: str) -> None:
            pass

    return MockStorageService()

@pytest.fixture
def mock_email_service():
    """Create a mock email service."""
    class MockEmailService:
        async def send_email(self, to_email: str, subject: str, body: str) -> None:
            pass

        async def send_verification_email(self, to_email: str, token: str) -> None:
            pass

        async def send_password_reset_email(self, to_email: str, token: str) -> None:
            pass

    return MockEmailService()

@pytest.fixture
def mock_cache_service():
    """Create a mock cache service."""
    class MockCacheService:
        _cache = {}

        async def get(self, key: str) -> str:
            return self._cache.get(key)

        async def set(self, key: str, value: str, expire: int = 0) -> None:
            self._cache[key] = value

        async def delete(self, key: str) -> None:
            self._cache.pop(key, None)

        async def clear(self) -> None:
            self._cache.clear()

    return MockCacheService()

@pytest.fixture
def mock_form_analyzer():
    """Create a mock form analyzer."""
    class MockFormAnalyzer:
        async def analyze_exercise(self, exercise_type: str, form_data: dict) -> dict:
            return {
                "score": 85,
                "feedback": "Good form",
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85,
                "confidence_score": 0.9
            }

        async def get_exercise_metrics(self, exercise_type: str) -> dict:
            return {
                "joint_angles": {"hip": 90, "knee": 90},
                "spine_alignment": 0.95,
                "symmetry_score": 0.85
            }

    return MockFormAnalyzer()

@pytest.fixture(scope="session")
def mock_redis():
    """Create a mock Redis instance."""
    return MockRedis()

@pytest.fixture(scope="function")
async def test_admin(async_session: AsyncSession) -> User:
    """Create a test admin user."""
    # This fixture seems to duplicate test_superuser. Consolidate if appropriate later.
    # For now, just aligning the session name.
    # Check if user already exists
    existing_user_stmt = select(User).where(User.email == "admin@example.com")
    existing_user_result = await async_session.execute(existing_user_stmt)
    existing_user = existing_user_result.scalars().first()
    if existing_user:
        # Ensure it's a superuser if we are to return it.
        if not existing_user.is_superuser:
            existing_user.is_superuser = True
            await async_session.commit()
            await async_session.refresh(existing_user)
        return existing_user

    admin = User(
        email="admin@example.com",
        username="testadminuser",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_superuser=True,
        is_verified=True
    )
    async_session.add(admin)
    await async_session.commit()
    await async_session.refresh(admin)
    return admin

@pytest.fixture(scope="function")
async def test_admin_token(test_admin: User) -> str:
    """Create a token for the test admin user."""
    return create_access_token(data={"sub": test_admin.email})

@pytest.fixture(scope="function")
async def test_admin_headers(test_admin_token: str) -> Dict[str, str]:
    """Create authentication headers for the test admin user."""
    return {"Authorization": f"Bearer {test_admin_token}"}

@pytest.fixture(scope="function")
async def test_workout(async_session: AsyncSession, test_user: User) -> Workout:
    """Create a test workout."""
    workout = Workout(
        user_id=test_user.id,
        name="Test Workout",
        description="A test workout",
        duration_minutes=30
    )
    async_session.add(workout)
    await async_session.commit()
    await async_session.refresh(workout)
    return workout

@pytest.fixture(scope="function")
async def test_exercise(async_session: AsyncSession, test_workout: Workout) -> Exercise:
    """Create a test exercise."""
    # Ensure Exercise model is imported if not already
    # from app.models.exercise import Exercise # (already imported via __init__ or directly)
    # from app.models.exercise_config import ExerciseTemplate # Assuming an ExerciseTemplate is needed
    
    # First, ensure an ExerciseTemplate exists or create one.
    # This part is complex as Exercise links to ExerciseTemplate via name/id.
    # For simplicity, let's assume an ExerciseTemplate with name "Test Squat" must exist.
    # Or, we create one if it doesn't. This requires ExerciseTemplate model access.
    
    # Simplified: assumes exercise_template_id can be a new UUID for test purposes if no FK enforcement in test.
    # Or, that the test_user has access to a default exercise template.
    # For robust testing, an actual ExerciseTemplate should be created and linked.
    
    exercise_template_id_for_test = uuid.uuid4() # Placeholder

    exercise = Exercise(
        name="Test Squat", 
        description="Test Squat Description",
        workout_id=test_workout.id,
        sets=3,
        reps=10
    )
    async_session.add(exercise)
    await async_session.commit()
    await async_session.refresh(exercise)
    return exercise

@pytest.fixture(scope="function")
async def test_workout_plan(async_session: AsyncSession, test_user: User) -> WorkoutPlan:
    """Create a test workout plan."""
    workout_plan = WorkoutPlan(
        user_id=test_user.id,
        name="Test Plan",
        description="A test workout plan",
        duration_weeks=4
    )
    async_session.add(workout_plan)
    await async_session.commit()
    await async_session.refresh(workout_plan)
    return workout_plan

@pytest.fixture(scope="function")
async def setup_test_db():
    """Set up the test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing."""
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def async_client(setup_test_db, async_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async client for testing, ensuring DB override uses the correct get_async_db from app.api.deps."""
    
    # Ensure 'app' is accessible. If the global import isn't working for this fixture's scope,
    # a local import can be a workaround, though it's unusual for conftest.
    from app.main import app 
    # Ensure the correct get_async_db (from app.api.deps) is used for the override key.
    # This relies on the module-level import: from app.api.deps import get_async_db as app_api_deps_get_async_db
    # If that import isn't present or working, this next line would also need a local import for app_api_deps_get_async_db
    from app.api.deps import get_async_db as app_api_deps_get_async_db_local # Local alias for clarity

    original_override = app.dependency_overrides.get(app_api_deps_get_async_db_local)

    async def override_get_db_for_test() -> AsyncSession:
        yield async_session

    app.dependency_overrides[app_api_deps_get_async_db_local] = override_get_db_for_test
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Restore original dependency override state
    if original_override:
        app.dependency_overrides[app_api_deps_get_async_db_local] = original_override
    else:
        app.dependency_overrides.pop(app_api_deps_get_async_db_local, None)  # FIXED: safe pop to avoid KeyError

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "security: mark test as security test")
    config.addinivalue_line("markers", "performance: mark test as performance test")

@pytest.fixture(scope="session")
def test_files_cleanup() -> Generator[List[Path], None, None]:
    """Track and clean up test files.
    
    This fixture maintains a list of files created during tests
    and ensures they are cleaned up after the test session.
    
    Yields:
        List[Path]: List to track files that need cleanup
    """
    files_to_cleanup: List[Path] = []
    yield files_to_cleanup
    
    # Clean up all tracked files
    for file_path in files_to_cleanup:
        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            shutil.rmtree(file_path)

@pytest.fixture
def test_file_tracker(test_files_cleanup: List[Path]) -> Generator[List[Path], None, None]:
    """Track test files for a single test.
    
    Args:
        test_files_cleanup: Session-wide list of files to clean up
        
    Yields:
        List[Path]: List to track files for this test
    """
    test_files: List[Path] = []
    yield test_files
    test_files_cleanup.extend(test_files)

@pytest.fixture
def create_test_file(tmp_path: Path, test_file_tracker: List[Path]) -> callable:
    """Create a test file and track it for cleanup.
    
    Args:
        tmp_path: Temporary directory for the test
        test_file_tracker: List to track files for cleanup
        
    Returns:
        callable: Function to create and track test files
    """
    def _create_file(
        filename: str,
        content: bytes = b"test content",
        track: bool = True
    ) -> Path:
        """Create a test file.
        
        Args:
            filename: Name of the file to create
            content: Content to write to the file
            track: Whether to track the file for cleanup
            
        Returns:
            Path: Path to the created file
        """
        file_path = tmp_path / filename
        file_path.write_bytes(content)
        if track:
            test_file_tracker.append(file_path)
        return file_path
    
    return _create_file

@pytest.fixture
def create_test_dir(tmp_path: Path, test_file_tracker: List[Path]) -> callable:
    """Create a test directory and track it for cleanup.
    
    Args:
        tmp_path: Temporary directory for the test
        test_file_tracker: List to track directories for cleanup
        
    Returns:
        callable: Function to create and track test directories
    """
    def _create_dir(dirname: str, track: bool = True) -> Path:
        """Create a test directory.
        
        Args:
            dirname: Name of the directory to create
            track: Whether to track the directory for cleanup
            
        Returns:
            Path: Path to the created directory
        """
        dir_path = tmp_path / dirname
        dir_path.mkdir(parents=True, exist_ok=True)
        if track:
            test_file_tracker.append(dir_path)
        return dir_path
    
    return _create_dir

# New directory structure
# backend/tests/
# ├── unit/
# │   ├── services/
# │   ├── models/
# │   └── utils/
# ├── integration/
# │   ├── api/
# │   └── database/
# ├── e2e/
# └── performance/ 

@pytest.fixture(scope="session", autouse=True)
def clear_prometheus_registry_session_scoped():
    """Clear default Prometheus registry before the test session."""
    # Get a list of current collectors. Iterate over a copy of keys as we are unregistering.
    collector_keys = list(REGISTRY._collector_to_names.keys()) # Use .keys() for direct collector objects
    for collector in collector_keys:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            # This can happen if another thread/process modified the registry during iteration
            # Or if a collector was already unregistered by another (less likely here)
            pass # Ignore if already unregistered
    # As an extra precaution, though unregistering collectors should suffice:
    # REGISTRY._metrics.clear() # This is not a public API, avoid if unregister works. 