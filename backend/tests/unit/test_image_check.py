"""G-43: the image must match requirements.txt, and the check must say so without crashing."""
from importlib import metadata
from pathlib import Path

import pytest

from app.core import image_check as ic

pytestmark = pytest.mark.unit


def _req(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "requirements.txt"
    p.write_text(text)
    return p


def _versions(table):
    def lookup(name):
        try:
            return table[name]
        except KeyError:
            raise metadata.PackageNotFoundError(name)
    return lookup


def test_matching_pins_are_ok(tmp_path):
    req = _req(tmp_path, "fastapi==0.110.0\npython-jose[cryptography]==3.3.0\nlz4>=4.0.0\n# comment\n")
    res = ic.check_image(req, _versions({"fastapi": "0.110.0", "python-jose": "3.3.0"}))
    assert res.ok and res.checked == 2
    assert res.unpinned == ["lz4"]          # floors are listed, not checked


def test_a_mismatch_and_a_missing_pin_are_named(tmp_path):
    req = _req(tmp_path, "celery==5.5.2\npytest-timeout==2.3.1\n")
    res = ic.check_image(req, _versions({"celery": "5.4.0"}))
    assert not res.ok
    assert res.mismatches == ["celery: pinned 5.5.2, installed 5.4.0"]
    assert res.missing == ["pytest-timeout: pinned 2.3.1, not installed"]


def test_name_normalisation_matches_pep503(tmp_path):
    req = _req(tmp_path, "Opentelemetry_API==1.21.0\n")
    res = ic.check_image(req, _versions({"opentelemetry-api": "1.21.0"}))
    assert res.ok, res


def test_environment_markers_and_inline_comments_do_not_break_the_pin(tmp_path):
    req = _req(tmp_path, "uvloop==0.19.0; sys_platform != 'win32'\nredis==5.0.1  # broker\n")
    res = ic.check_image(req, _versions({"uvloop": "0.19.0", "redis": "5.0.1"}))
    assert res.ok and res.checked == 2


def test_the_cli_exits_nonzero_on_drift(tmp_path, capsys):
    req = _req(tmp_path, "numpy==0.0.0\n")
    assert ic.main([str(req)]) == 1
    assert "MISMATCH" in capsys.readouterr().out


def test_run_and_log_never_raises(monkeypatch):
    monkeypatch.setattr(ic, "check_image", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    res = ic.run_and_log("test")
    assert not res.ok and ic.LAST is res


def test_the_real_requirements_file_parses_and_reports(capsys):
    """Against the real file, in whatever process runs the tests: the point is that it
    runs, prints, and returns the same verdict it will give /health."""
    res = ic.check_image()
    assert res.checked > 40, res.summary()
    print(res.summary())
