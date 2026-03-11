import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.exercise_config_service import ExerciseConfigService
from app.models.exercise_config import ExerciseConfig
from app.models.exercise import ExerciseTemplate
from app.core.config import Settings

@pytest.fixture
def mock_db_session() -> AsyncMock:
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_settings() -> Settings:
    return Settings()

@pytest.fixture
def exercise_config_service(mock_db_session: AsyncMock, mock_settings: Settings) -> ExerciseConfigService:
    return ExerciseConfigService(db=mock_db_session, settings=mock_settings)

@pytest.fixture
def sample_exercise_template_factory():
    def _factory(slug: str, id: uuid.UUID = uuid.uuid4()) -> ExerciseTemplate:
        return ExerciseTemplate(id=id, slug=slug, name=slug.capitalize(), description="Test Template")
    return _factory

@pytest.fixture
def sample_exercise_config_factory():
    def _factory(exercise_id: uuid.UUID, version: int = 1, is_active: bool = True, id: uuid.UUID = uuid.uuid4()) -> ExerciseConfig:
        return ExerciseConfig(
            id=id,
            exercise_id=exercise_id,
            name=f"Test Config v{version}",
            version=version,
            is_active=is_active,
            # Add other minimal required fields with default valid values
            joint_angle_rules={"phases": {}, "joints": []},
            movement_phases={},
            feedback_templates={}
        )
    return _factory

@pytest.mark.asyncio
async def test_get_active_config_by_template_slug_valid_slug_returns_config(
    exercise_config_service: ExerciseConfigService,
    mock_db_session: AsyncMock,
    sample_exercise_template_factory,
    sample_exercise_config_factory
):
    """Test that a valid slug returns the active ExerciseConfig."""
    test_slug = "test-squat"
    template_id = uuid.uuid4()
    mock_template = sample_exercise_template_factory(slug=test_slug, id=template_id)
    mock_active_config = sample_exercise_config_factory(exercise_id=template_id, is_active=True)

    # Mock the database execution flow
    # 1. Query for ExerciseTemplate by slug
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_template
    
    # 2. Query for active ExerciseConfig by exercise_id (called by get_active_config_for_exercise_async)
    # We need to chain AsyncMocks for the second execute call
    active_config_execute_mock = AsyncMock()
    active_config_execute_mock.scalars.return_value.first.return_value = mock_active_config
    
    # Set up side_effect for db.execute to handle multiple calls
    mock_db_session.execute.side_effect = [
        AsyncMock(scalars=AsyncMock(first=AsyncMock(return_value=mock_template))),
        active_config_execute_mock
    ]

    result = await exercise_config_service.get_active_config_by_template_slug_async(slug=test_slug)

    assert result is not None
    assert result == mock_active_config
    assert result.is_active
    assert mock_db_session.execute.call_count == 2

@pytest.mark.asyncio
async def test_get_active_config_by_template_slug_unknown_slug_returns_none(
    exercise_config_service: ExerciseConfigService,
    mock_db_session: AsyncMock
):
    """Test that an unknown slug returns None."""
    test_slug = "unknown-exercise"

    # Mock query for ExerciseTemplate by slug to return None
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None

    result = await exercise_config_service.get_active_config_by_template_slug_async(slug=test_slug)

    assert result is None
    mock_db_session.execute.assert_called_once() # Only one call to find template

@pytest.mark.asyncio
async def test_get_active_config_by_template_slug_valid_slug_no_active_config_returns_none(
    exercise_config_service: ExerciseConfigService,
    mock_db_session: AsyncMock,
    sample_exercise_template_factory,
    sample_exercise_config_factory # Not strictly needed here as config is None, but good for consistency
):
    """Test that a valid slug with no active ExerciseConfig returns None."""
    test_slug = "test-lunge"
    template_id = uuid.uuid4()
    mock_template = sample_exercise_template_factory(slug=test_slug, id=template_id)

    # Mock the database execution flow
    # 1. Query for ExerciseTemplate by slug - found
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_template
    
    # 2. Query for active ExerciseConfig by exercise_id (called by get_active_config_for_exercise_async) - returns None
    active_config_execute_mock = AsyncMock()
    active_config_execute_mock.scalars.return_value.first.return_value = None
    
    mock_db_session.execute.side_effect = [
        AsyncMock(scalars=AsyncMock(first=AsyncMock(return_value=mock_template))),
        active_config_execute_mock
    ]

    result = await exercise_config_service.get_active_config_by_template_slug_async(slug=test_slug)

    assert result is None
    assert mock_db_session.execute.call_count == 2
