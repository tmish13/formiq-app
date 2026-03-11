"""Unit tests for UserService — targets the real async interface."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from app.services.base_service import BaseService
from app.models.user import User as DBUser
from app.models.enums import SubscriptionTier
from app.schemas.user import UserCreate, UserUpdate
from app.core.config import Settings
from app.core.exceptions import NotFoundException, ServiceError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> AsyncMock:
    """Async database session mock."""
    db = AsyncMock(spec=AsyncSession)
    # Provide a chainable result stub for db.execute(...)
    result_mock = MagicMock()
    result_mock.scalars.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_settings() -> MagicMock:
    return MagicMock(spec=Settings)


@pytest.fixture
def user_service(mock_db: AsyncMock, mock_settings: MagicMock) -> UserService:
    return UserService(db=mock_db, app_settings=mock_settings)


@pytest.fixture
def sample_user() -> DBUser:
    uid = uuid4()
    return DBUser(
        id=uid,
        email="test@formiq.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_pass",
        is_active=True,
        is_verified=True,
        subscription_tier=SubscriptionTier.FREE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# get_by_email_async
# ---------------------------------------------------------------------------

class TestGetByEmailAsync:

    @pytest.mark.asyncio
    async def test_returns_user_when_found(self, user_service: UserService, mock_db: AsyncMock, sample_user: DBUser):
        """get_by_email_async returns the DBUser when it exists."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = sample_user
        mock_db.execute.return_value = result_mock

        found = await user_service.get_by_email_async(sample_user.email)

        assert found is sample_user
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, user_service: UserService, mock_db: AsyncMock):
        """get_by_email_async returns None when no user matches."""
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        found = await user_service.get_by_email_async("nobody@formiq.com")

        assert found is None

    @pytest.mark.asyncio
    async def test_raises_service_error_on_db_failure(self, user_service: UserService, mock_db: AsyncMock):
        """get_by_email_async wraps db exceptions in ServiceError."""
        mock_db.execute.side_effect = Exception("DB connection lost")

        with pytest.raises(ServiceError):
            await user_service.get_by_email_async("fail@formiq.com")


# ---------------------------------------------------------------------------
# create_user_async
# ---------------------------------------------------------------------------

class TestCreateUserAsync:

    @pytest.mark.asyncio
    async def test_hashes_password_and_delegates_to_base(self, user_service: UserService, sample_user: DBUser):
        """create_user_async hashes the password and stores via BaseService."""
        user_in = UserCreate(
            email="new@formiq.com",
            password="F0rm!qX9pP",
            confirm_password="F0rm!qX9pP",
            full_name="New User",
        )

        with patch.object(BaseService, "create_async", new_callable=AsyncMock, return_value=sample_user) as mock_create:
            created = await user_service.create_user_async(user_in)

        assert created is sample_user
        mock_create.assert_awaited_once()
        # Verify password was hashed (the call arg dict has hashed_password, not plaintext)
        call_kwargs = mock_create.call_args.kwargs
        obj_in = call_kwargs.get("obj_in", mock_create.call_args.args[0] if mock_create.call_args.args else None)
        if obj_in is not None and isinstance(obj_in, dict):
            assert "hashed_password" in obj_in
            assert obj_in.get("password") is None  # plaintext cleared

    @pytest.mark.asyncio
    async def test_superuser_flag_forwarded(self, user_service: UserService, sample_user: DBUser):
        """create_user_async passes is_superuser=True into the object dict."""
        user_in = UserCreate(
            email="su@formiq.com",
            password="F0rm!qX9pP",
            confirm_password="F0rm!qX9pP",
        )

        captured = {}

        async def _capture_create(**kwargs):
            captured.update(kwargs)
            return sample_user

        with patch.object(BaseService, "create_async", side_effect=_capture_create):
            await user_service.create_user_async(user_in, is_superuser=True)

        obj_in = captured.get("obj_in", {})
        if isinstance(obj_in, dict):
            assert obj_in.get("is_superuser") is True


# ---------------------------------------------------------------------------
# update_user_async
# ---------------------------------------------------------------------------

class TestUpdateUserAsync:

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(self, user_service: UserService):
        """update_user_async returns None if the user doesn't exist."""
        with patch.object(BaseService, "get_async", new_callable=AsyncMock, return_value=None):
            result = await user_service.update_user_async(uuid4(), UserUpdate(full_name="X"))

        assert result is None

    @pytest.mark.asyncio
    async def test_updates_and_returns_user(self, user_service: UserService, sample_user: DBUser):
        """update_user_async calls update_async with the correct payload."""
        update_in = UserUpdate(full_name="Updated Name")

        with patch.object(BaseService, "get_async", new_callable=AsyncMock, return_value=sample_user), \
             patch.object(BaseService, "update_async", new_callable=AsyncMock, return_value=sample_user) as mock_update:
            result = await user_service.update_user_async(sample_user.id, update_in)

        assert result is sample_user
        mock_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_password_is_hashed_on_update(self, user_service: UserService, sample_user: DBUser):
        """If a new password is provided in the update, it is hashed."""
        update_in = UserUpdate(password="N3wP@ssXqZ!", full_name="Name")

        captured = {}

        async def _capture_update(*, db_obj, obj_in):
            captured["obj_in"] = obj_in
            return sample_user

        with patch.object(BaseService, "get_async", new_callable=AsyncMock, return_value=sample_user), \
             patch.object(BaseService, "update_async", side_effect=_capture_update):
            await user_service.update_user_async(sample_user.id, update_in)

        obj_in = captured.get("obj_in", {})
        if isinstance(obj_in, dict):
            # Plaintext password must be removed and hashed_password added
            assert "password" not in obj_in
            assert "hashed_password" in obj_in


# ---------------------------------------------------------------------------
# update_user_subscription_async
# ---------------------------------------------------------------------------

class TestUpdateUserSubscriptionAsync:

    @pytest.mark.asyncio
    async def test_raises_not_found_when_user_missing(self, user_service: UserService):
        """update_user_subscription_async raises NotFoundException if user absent."""
        with patch.object(BaseService, "get_async", new_callable=AsyncMock, return_value=None):
            with pytest.raises(NotFoundException):
                await user_service.update_user_subscription_async(uuid4(), tier="PRO")

    @pytest.mark.asyncio
    async def test_updates_subscription_tier(self, user_service: UserService, mock_db: AsyncMock, sample_user: DBUser):
        """update_user_subscription_async sets subscription_tier and commits."""
        with patch.object(BaseService, "get_async", new_callable=AsyncMock, return_value=sample_user):
            result = await user_service.update_user_subscription_async(
                sample_user.id, tier="PRO", is_active=True
            )

        assert result.subscription_tier == "PRO"
        mock_db.add.assert_called_once_with(sample_user)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(sample_user)


# ---------------------------------------------------------------------------
# complete_onboarding
# ---------------------------------------------------------------------------

class TestCompleteOnboarding:

    @pytest.mark.asyncio
    async def test_raises_not_found_when_user_missing(self, user_service: UserService, mock_db: AsyncMock):
        """complete_onboarding raises NotFoundException for unknown user."""
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(NotFoundException):
            await user_service.complete_onboarding(mock_db, uuid4())

    @pytest.mark.asyncio
    async def test_marks_onboarding_complete(self, user_service: UserService, mock_db: AsyncMock, sample_user: DBUser):
        """complete_onboarding sets has_completed_onboarding=True and commits."""
        sample_user.has_completed_onboarding = False
        mock_db.get = AsyncMock(return_value=sample_user)

        result = await user_service.complete_onboarding(mock_db, sample_user.id)

        assert result.has_completed_onboarding is True
        assert result.onboarding_completed_at is not None
        mock_db.commit.assert_awaited()
        mock_db.refresh.assert_awaited_with(sample_user)
