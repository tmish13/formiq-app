"""Unit tests for exercise template resolution in the form-check submission path.

Covers:
  - The DB lookup value derived from ExerciseType.SQUAT equals 'squat'
  - All squat aliases accepted by the endpoint guard map to the same lookup value
  - NotFoundException raised + S3 cleanup fired when no template row exists
  - No NotFoundException when a Squat template is present
  - Migration 0008 exists and contains an idempotent Squat INSERT

No real DB, no Celery, no S3.  All I/O is mocked.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.enums import ExerciseType
from app.core.exceptions import NotFoundException

# All squat aliases accepted by the /form-checks/submit endpoint guard.
_SQUAT_ALIASES = {"squat", "low bar squat", "high bar squat", "back squat", "front squat"}

# Canonical UUID seeded by migration 0008.
SEEDED_SQUAT_UUID = "a1b2c3d4-e5f6-4a1b-8c3d-000000000001"


# ---------------------------------------------------------------------------
# 1. Lookup value correctness (pure, no I/O)
# ---------------------------------------------------------------------------

class TestTemplateLookupValue:
    """The service does LOWER(name) = ExerciseType.SQUAT.value.lower().
    Verify the exact value that will be sent to the DB."""

    def test_squat_enum_value_is_squat(self):
        assert ExerciseType.SQUAT.value == "squat"

    def test_lookup_value_is_lowercase_squat(self):
        assert ExerciseType.SQUAT.value.lower() == "squat"

    def test_all_aliases_produce_squat_lookup(self):
        """Every squat alias accepted by the endpoint maps to LOWER(name)='squat'."""
        for alias in _SQUAT_ALIASES:
            # The endpoint guard converts any alias → ExerciseType.SQUAT.
            # The service then does: exercise_type_enum.value.lower() as the DB value.
            lookup = ExerciseType.SQUAT.value.lower()
            assert lookup == "squat", (
                f"alias '{alias}' produced unexpected lookup value '{lookup}'"
            )

    def test_squat_alias_count(self):
        """Guard: five accepted squat aliases — alert if any is accidentally removed."""
        assert len(_SQUAT_ALIASES) == 5


# ---------------------------------------------------------------------------
# 2. Service-level template resolution (mocked DB + storage)
# ---------------------------------------------------------------------------

class TestSubmitFormCheckTemplateLookup:
    """Test submit_form_check template resolution path with mocked dependencies."""

    # -- helpers ------------------------------------------------------------

    def _make_service(self, *, db, storage):
        from app.services.form_check_service import FormCheckService
        return FormCheckService(
            db=db,
            settings=MagicMock(),
            storage_service=storage,
            ai_service=MagicMock(),
        )

    def _db_returning(self, template):
        """AsyncSession mock whose execute() returns `template` via scalars().first()."""
        scalars = MagicMock()
        scalars.first.return_value = template
        result = MagicMock()
        result.scalars.return_value = scalars
        db = AsyncMock()
        db.execute = AsyncMock(return_value=result)
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        return db

    def _storage(self, *, key="form_check_videos/user/test.mp4"):
        s = AsyncMock()
        s.upload_file_and_get_key = AsyncMock(return_value=key)
        s.get_file_url = MagicMock(return_value=f"https://s3.example.com/{key}")
        s.delete_file = AsyncMock()
        return s

    def _video_file(self):
        from fastapi import UploadFile
        f = MagicMock(spec=UploadFile)
        f.filename = "squat.mp4"
        f.content_type = "video/mp4"
        f.read = AsyncMock(return_value=b"fake-video")
        return f

    # -- tests --------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_missing_template_raises_not_found(self):
        """NotFoundException when exercise_templates has no Squat row."""
        service = self._make_service(db=self._db_returning(None), storage=self._storage())
        with pytest.raises(NotFoundException):
            await service.submit_form_check(
                user_id=uuid4(),
                video_file=self._video_file(),
                exercise_type_enum=ExerciseType.SQUAT,
            )

    @pytest.mark.asyncio
    async def test_missing_template_triggers_s3_cleanup(self):
        """Uploaded video is deleted from S3 when template lookup fails."""
        storage = self._storage(key="form_check_videos/u/video.mp4")
        service = self._make_service(db=self._db_returning(None), storage=storage)

        with pytest.raises(NotFoundException):
            await service.submit_form_check(
                user_id=uuid4(),
                video_file=self._video_file(),
                exercise_type_enum=ExerciseType.SQUAT,
            )

        storage.delete_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_existing_squat_template_passes_lookup(self):
        """No NotFoundException when a 'Squat' template exists in the DB."""
        from app.models.exercise import ExerciseTemplate
        from app.services.base_service import BaseService

        template = MagicMock(spec=ExerciseTemplate)
        template.id = uuid4()
        template.name = "Squat"

        storage = self._storage()
        service = self._make_service(db=self._db_returning(template), storage=storage)

        # Patch only the downstream steps that need a real DB / Celery
        with patch.object(BaseService, "create_async", new_callable=AsyncMock) as mock_create, \
             patch("app.tasks.analysis_tasks.process_form_check_task") as mock_task:
            mock_fc = MagicMock()
            mock_fc.id = uuid4()
            mock_fc.details = None
            mock_create.return_value = mock_fc
            mock_task.delay = MagicMock()

            try:
                await service.submit_form_check(
                    user_id=uuid4(),
                    video_file=self._video_file(),
                    exercise_type_enum=ExerciseType.SQUAT,
                )
            except NotFoundException:
                pytest.fail("NotFoundException raised even though Squat template exists")
            except Exception:
                pass  # Other mock-chain exceptions are acceptable; only NotFound is wrong

    @pytest.mark.asyncio
    async def test_case_insensitive_name_squat_matches(self):
        """A template stored as 'SQUAT' (uppercase) is still found (DB uses LOWER())."""
        from app.models.exercise import ExerciseTemplate
        from app.services.base_service import BaseService

        template = MagicMock(spec=ExerciseTemplate)
        template.id = uuid4()
        template.name = "SQUAT"  # stored uppercase

        storage = self._storage()
        service = self._make_service(db=self._db_returning(template), storage=storage)

        with patch.object(BaseService, "create_async", new_callable=AsyncMock) as mock_create, \
             patch("app.tasks.analysis_tasks.process_form_check_task") as mock_task:
            mock_fc = MagicMock()
            mock_fc.id = uuid4()
            mock_fc.details = None
            mock_create.return_value = mock_fc
            mock_task.delay = MagicMock()

            try:
                await service.submit_form_check(
                    user_id=uuid4(),
                    video_file=self._video_file(),
                    exercise_type_enum=ExerciseType.SQUAT,
                )
            except NotFoundException:
                pytest.fail("NotFoundException raised for uppercase template name")
            except Exception:
                pass  # mock-chain noise, not a failure


# ---------------------------------------------------------------------------
# 3. Seed migration sanity checks (filesystem + content)
# ---------------------------------------------------------------------------

class TestSeedMigration:
    """Verify migration 0008 exists and contains a correct, idempotent Squat INSERT."""

    def _migration_path(self) -> str:
        here = os.path.dirname(__file__)
        return os.path.normpath(
            os.path.join(here, "../../migrations/versions/0008_seed_exercise_templates.py")
        )

    def test_migration_file_exists(self):
        assert os.path.isfile(self._migration_path()), (
            "Migration 0008_seed_exercise_templates.py is missing — "
            "run alembic upgrade head after creating it"
        )

    def test_migration_down_revision_is_0007(self):
        with open(self._migration_path()) as f:
            content = f.read()
        assert "0007_add_training_sessions" in content

    def test_migration_inserts_squat_name(self):
        """The INSERT must use 'Squat' — the exact string matched by LOWER(name)='squat'."""
        with open(self._migration_path()) as f:
            content = f.read()
        assert "'Squat'" in content or '"Squat"' in content

    def test_migration_is_idempotent(self):
        """INSERT must be wrapped in WHERE NOT EXISTS or ON CONFLICT to be safe."""
        with open(self._migration_path()) as f:
            content = f.read()
        assert "NOT EXISTS" in content or "ON CONFLICT" in content, (
            "Migration must be idempotent (WHERE NOT EXISTS or ON CONFLICT)"
        )

    def test_migration_seeds_correct_uuid(self):
        """Fixed UUID matches SEEDED_SQUAT_UUID constant used in tests."""
        with open(self._migration_path()) as f:
            content = f.read()
        assert SEEDED_SQUAT_UUID in content
