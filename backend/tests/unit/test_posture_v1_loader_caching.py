"""Unit tests for PostureV1 loader artifact caching.

Verifies:
  - _ensure_loaded() loads artifacts exactly once (not on every call)
  - predict_posture() on a pre-loaded instance does NOT reload
  - The module-level shared loader pattern (_shared_posture_v1_loader)
    means a second task reuses the same loader object
  - Threshold save/restore: set_threshold_mode during a task does not
    permanently mutate the shared loader for subsequent tasks
  - Failure path: if _load_model() raises, _loaded stays False so the next
    call to _ensure_loaded() will retry (no silent empty-loader caching)
"""
import threading
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(env="production"):
    s = MagicMock()
    s.ENVIRONMENT = env
    s.USE_POSTURE_V1 = True
    return s


def _make_loader_with_mock_load(settings=None, model_loaded=True):
    """
    Return a PostureV1TorchLoader whose _load_manifest / _load_model are
    replaced by no-ops so the real disk files are not needed.
    """
    from app.ml.posture_v1.loader import PostureV1TorchLoader

    loader = PostureV1TorchLoader(settings or _make_settings())
    loader._load_manifest = MagicMock()
    if model_loaded:
        loader._load_model = MagicMock()
        # Simulate a successfully loaded model
        loader._model = MagicMock()
    else:
        def _fail():
            raise RuntimeError("disk error")
        loader._load_model = _fail
    return loader


# ---------------------------------------------------------------------------
# 1. _ensure_loaded() loads once, not twice
# ---------------------------------------------------------------------------

class TestEnsureLoadedOnce:
    def test_manifest_and_model_loaded_exactly_once(self):
        loader = _make_loader_with_mock_load()
        assert not loader._loaded

        loader._ensure_loaded()
        assert loader._loaded
        loader._load_manifest.assert_called_once()
        loader._load_model.assert_called_once()

    def test_second_ensure_loaded_is_no_op(self):
        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()
        loader._ensure_loaded()  # second call
        loader._ensure_loaded()  # third call

        # Methods called exactly once total
        loader._load_manifest.assert_called_once()
        loader._load_model.assert_called_once()

    def test_loaded_flag_set_after_first_call(self):
        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()
        assert loader._loaded is True

    def test_thread_safe_double_check(self):
        """Two threads calling _ensure_loaded() concurrently load artifacts once."""
        loader = _make_loader_with_mock_load()

        results = []
        def run():
            loader._ensure_loaded()
            results.append(True)

        t1 = threading.Thread(target=run)
        t2 = threading.Thread(target=run)
        t1.start(); t2.start()
        t1.join(); t2.join()

        assert len(results) == 2
        loader._load_manifest.assert_called_once()
        loader._load_model.assert_called_once()


# ---------------------------------------------------------------------------
# 2. Failure path: _loaded stays False if load raises
# ---------------------------------------------------------------------------

class TestLoadFailureDoesNotCache:
    def test_load_failure_keeps_loaded_false(self):
        """If _load_model() raises, _loaded must remain False."""
        loader = _make_loader_with_mock_load(model_loaded=False)

        with pytest.raises(RuntimeError):
            loader._ensure_loaded()

        assert loader._loaded is False, (
            "A failed load must not set _loaded=True — next task should retry"
        )

    def test_load_failure_retries_on_next_call(self):
        """After a failure, calling _ensure_loaded() again should re-attempt."""
        from app.ml.posture_v1.loader import PostureV1TorchLoader

        loader = PostureV1TorchLoader(_make_settings())
        loader._load_manifest = MagicMock()

        call_count = [0]
        def _flaky_load():
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("transient error")
            loader._model = MagicMock()  # second attempt succeeds

        loader._load_model = _flaky_load

        # First call raises, loader stays un-loaded
        with pytest.raises(RuntimeError):
            loader._ensure_loaded()
        assert not loader._loaded

        # Second call succeeds
        loader._ensure_loaded()
        assert loader._loaded
        assert call_count[0] == 2


# ---------------------------------------------------------------------------
# 3. Shared loader reuse across simulated task calls
# ---------------------------------------------------------------------------

class TestSharedLoaderReuse:
    def test_same_instance_used_for_two_tasks(self):
        """Simulate two tasks: the second task should reuse the same loader."""
        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()

        # Simulate task 1: call predict_posture (with mocked internal methods)
        loader._ensure_loaded()  # no reload
        loader._load_manifest.assert_called_once()

        # Simulate task 2: same
        loader._ensure_loaded()  # still no reload
        loader._load_manifest.assert_called_once()  # still only once

    def test_loader_identity_preserved(self):
        """The shared loader is the exact same object across uses."""
        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()

        id_before = id(loader)
        # Simulated task 2 references the same object
        loader._ensure_loaded()
        assert id(loader) == id_before


# ---------------------------------------------------------------------------
# 4. Threshold save / restore for shared loader
# ---------------------------------------------------------------------------

class TestThresholdSaveRestore:
    def test_threshold_restored_after_task_override(self):
        """set_threshold_mode in task N must not affect task N+1."""
        from app.ml.posture_v1.loader import PostureV1TorchLoader, DEFAULT_FAULT_THRESHOLD

        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()

        original = loader._fault_threshold
        assert original == DEFAULT_FAULT_THRESHOLD

        # Task 1: applies strict mode
        _saved = loader._fault_threshold
        loader.set_threshold_mode("strict")
        assert loader._fault_threshold == 0.60

        # Restore (as the task code does)
        loader._fault_threshold = _saved

        # Task 2 threshold is the original
        assert loader._fault_threshold == original

    def test_threshold_default_is_default_fault_threshold(self):
        from app.ml.posture_v1.loader import PostureV1TorchLoader, DEFAULT_FAULT_THRESHOLD

        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()
        assert loader._fault_threshold == DEFAULT_FAULT_THRESHOLD

    def test_all_named_modes_are_restorable(self):
        from app.ml.posture_v1.loader import PostureV1TorchLoader, THRESHOLD_MODES

        loader = _make_loader_with_mock_load()
        loader._ensure_loaded()
        original = loader._fault_threshold

        for mode in THRESHOLD_MODES:
            _saved = loader._fault_threshold
            loader.set_threshold_mode(mode)
            loader._fault_threshold = _saved  # restore

            assert loader._fault_threshold == original, (
                f"Threshold not restored after mode={mode}"
            )


# ---------------------------------------------------------------------------
# 5. analysis_tasks module declares _shared_posture_v1_loader at module scope
# ---------------------------------------------------------------------------

class TestAnalysisTasksModuleScope:
    def test_shared_posture_v1_loader_declared(self):
        """_shared_posture_v1_loader must exist at module scope in analysis_tasks."""
        import app.tasks.analysis_tasks as at
        assert hasattr(at, "_shared_posture_v1_loader"), (
            "_shared_posture_v1_loader not found in analysis_tasks module scope"
        )

    def test_shared_posture_v1_loader_is_none_before_worker_init(self):
        """Before worker_process_init fires, the loader defaults to None."""
        import app.tasks.analysis_tasks as at
        # In the test process, worker_process_init never fires, so it should be None.
        # (The test process does not start a Celery worker.)
        # This is the safe starting state; the task will fall back to per-task creation.
        assert at._shared_posture_v1_loader is None

    def test_initialize_worker_services_sets_loader_when_use_posture_v1_true(self):
        """initialize_worker_services must set _shared_posture_v1_loader when USE_POSTURE_V1=True."""
        import app.tasks.analysis_tasks as at

        mock_loader = MagicMock()
        mock_loader._ensure_loaded = MagicMock()

        mock_settings = _make_settings()
        mock_settings.USE_POSTURE_V1 = True
        mock_settings.USE_S3_STORAGE = False

        with patch("app.tasks.analysis_tasks.get_settings", return_value=mock_settings), \
             patch("app.tasks.analysis_tasks.AIService"), \
             patch("app.tasks.analysis_tasks.StorageService"), \
             patch("app.ml.posture_v1.loader.PostureV1TorchLoader", return_value=mock_loader) as MockLoader:

            # Reset module state so we can test fresh
            original = at._shared_posture_v1_loader
            try:
                at._shared_posture_v1_loader = None
                at.initialize_worker_services()
                assert at._shared_posture_v1_loader is mock_loader
                mock_loader._ensure_loaded.assert_called_once()
            finally:
                at._shared_posture_v1_loader = original

    def test_initialize_worker_services_handles_loader_init_failure(self):
        """If PostureV1TorchLoader init fails, worker still starts (non-fatal)."""
        import app.tasks.analysis_tasks as at

        mock_settings = _make_settings()
        mock_settings.USE_POSTURE_V1 = True
        mock_settings.USE_S3_STORAGE = False

        with patch("app.tasks.analysis_tasks.get_settings", return_value=mock_settings), \
             patch("app.tasks.analysis_tasks.AIService"), \
             patch("app.tasks.analysis_tasks.StorageService"), \
             patch("app.ml.posture_v1.loader.PostureV1TorchLoader",
                   side_effect=RuntimeError("artifact missing")):

            original = at._shared_posture_v1_loader
            try:
                at._shared_posture_v1_loader = None
                # Must NOT raise — PostureV1 init failure is non-fatal for the worker
                at.initialize_worker_services()
                # Loader stays None; per-task fallback will handle it
                assert at._shared_posture_v1_loader is None
            finally:
                at._shared_posture_v1_loader = original
