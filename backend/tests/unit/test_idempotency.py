"""Content-hash idempotency for form-check submission (G-10).

Key: (user_id, content_hash, model_version, spec_hash).

Same user + same bytes + same model + same feature spec means the pipeline would
compute the same answer, so returning the existing row is not a shortcut -- it is
the same result for none of the cost. A model or spec upgrade changes the key, so
the video is re-analysed under the new version with no explicit invalidation.
"""
import hashlib
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.models.enums import FormCheckStatus

pytestmark = pytest.mark.unit


def _upload(data: bytes, filename="clip.mp4") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(data))


@pytest.fixture
def service():
    from app.services.form_check_service import FormCheckService

    svc = FormCheckService.__new__(FormCheckService)  # skip __init__ wiring
    svc.db = AsyncMock()
    svc.settings = SimpleNamespace(MAX_VIDEO_SIZE_MB=100)
    return svc


class TestHashing:
    @pytest.mark.asyncio
    async def test_hash_matches_sha256_of_the_bytes(self, service):
        data = b"\x00\x01\x02" * 5000
        assert await service._hash_upload(_upload(data)) == hashlib.sha256(data).hexdigest()

    @pytest.mark.asyncio
    async def test_hash_rewinds_the_stream(self, service):
        """The single most breakable part of this.

        upload_file_and_get_key() reads the same UploadFile straight after. If
        _hash_upload leaves the cursor at EOF, a zero-byte video is uploaded and
        nothing downstream notices until inference produces garbage.
        """
        data = b"videobytes" * 1000
        upload = _upload(data)

        await service._hash_upload(upload)

        assert await upload.read() == data, "stream was not rewound after hashing"

    @pytest.mark.asyncio
    async def test_hash_spans_multiple_chunks(self, service):
        """Chunked reads must not hash only the first chunk."""
        data = b"x" * (service._HASH_CHUNK * 2 + 17)
        assert await service._hash_upload(_upload(data)) == hashlib.sha256(data).hexdigest()

    @pytest.mark.asyncio
    async def test_different_bytes_hash_differently(self, service):
        a = await service._hash_upload(_upload(b"a" * 1000))
        b = await service._hash_upload(_upload(b"b" * 1000))
        assert a != b

    @pytest.mark.asyncio
    async def test_hash_ignores_the_filename(self, service):
        """The key is the content, not the name.

        storage_service.py:159 hashes filename + timestamp and is deliberately
        unique per call -- reusing it here would mean the same video uploaded
        twice never deduped.
        """
        data = b"same bytes" * 500
        assert (
            await service._hash_upload(_upload(data, "a.mp4"))
            == await service._hash_upload(_upload(data, "b.mp4"))
        )


class TestDuplicateLookup:
    def _returns(self, service, row):
        result = MagicMock()
        result.scalars.return_value.first.return_value = row
        service.db.execute = AsyncMock(return_value=result)
        return service

    @pytest.mark.asyncio
    async def test_returns_the_existing_row(self, service):
        existing = MagicMock(id=uuid4())
        self._returns(service, existing)

        found = await service._find_duplicate_submission(
            user_id=uuid4(), content_hash="a" * 64,
            model_version="posture_v1:v1", spec_hash="truth_spec_151d_v1",
        )
        assert found is existing

    @pytest.mark.asyncio
    async def test_query_is_scoped_to_all_four_key_parts(self, service):
        self._returns(service, None)
        await service._find_duplicate_submission(
            user_id=uuid4(), content_hash="a" * 64,
            model_version="posture_v1:v1", spec_hash="truth_spec_151d_v1",
        )
        sql = str(service.db.execute.call_args.args[0])
        for column in ("user_id", "content_hash", "model_version", "spec_hash"):
            assert f"form_checks.{column}" in sql, f"{column} missing from the key"

    @pytest.mark.asyncio
    async def test_failed_rows_are_not_reused(self, service):
        """Otherwise one transient failure caches a failure forever and the user
        can never get that video analysed by resubmitting it."""
        self._returns(service, None)
        await service._find_duplicate_submission(
            user_id=uuid4(), content_hash="a" * 64,
            model_version="posture_v1:v1", spec_hash="truth_spec_151d_v1",
        )
        sql = str(service.db.execute.call_args.args[0])
        assert "!=" in sql or "IS NOT" in sql, sql

    @pytest.mark.asyncio
    async def test_no_dedupe_when_the_model_identity_is_unknown(self, service):
        """A broken manifest must not hand back a result from a different model."""
        with patch(
            "app.services.form_check_service.is_identity_known", return_value=False
        ):
            service.db.execute = AsyncMock(
                side_effect=AssertionError("must not query when identity is unknown")
            )
            found = await service._find_duplicate_submission(
                user_id=uuid4(), content_hash="a" * 64,
                model_version="unknown", spec_hash="unknown",
            )
        assert found is None


class TestModelIdentity:
    def test_identity_comes_from_the_manifest(self):
        from app.ml.model_identity import posture_v1_identity

        model_version, spec_hash = posture_v1_identity()
        assert model_version == "posture_v1:v1"
        assert spec_hash == "truth_spec_151d_v1"

    def test_identity_is_known(self):
        from app.ml.model_identity import is_identity_known

        assert is_identity_known() is True

    def test_identity_does_not_import_torch(self):
        """The submit path runs in the API process; loading the model to learn
        its version would put PyTorch on every upload request."""
        import subprocess
        import sys

        probe = (
            "import warnings; warnings.filterwarnings('ignore'); import sys; "
            "from app.ml.model_identity import posture_v1_identity; "
            "posture_v1_identity(); "
            "print('TORCH_LOADED' if 'torch' in sys.modules else 'NO_TORCH')"
        )
        out = subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, cwd="/app"
        )
        assert "NO_TORCH" in out.stdout, (
            f"stdout={out.stdout!r} stderr={out.stderr[-500:]!r}"
        )


class TestMigration:
    def test_revision_id_fits_the_alembic_version_column(self):
        """alembic_version.version_num is varchar(32). A longer id fails the
        final UPDATE *after* the DDL has run, which is a confusing half-state."""
        import importlib.util
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[2]
            / "migrations" / "versions" / "0009_content_hash_idempotency.py"
        )
        spec = importlib.util.spec_from_file_location("m0009", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert len(module.revision) <= 32, module.revision
        assert module.down_revision == "0008_seed_exercise_templates"
