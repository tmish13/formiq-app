"""G-23: one owner for the schema. The app creates tables from the models only for the SQLite unit
tests; every other environment gets its schema from `alembic upgrade head` (deployment/entrypoint.sh)."""
import pathlib
import re

import pytest

from app.core.lifespan import schema_owner_is_alembic

pytestmark = pytest.mark.unit
BACKEND = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("env,expected", [("test", False), ("development", True), ("staging", True), ("production", True)])
def test_only_the_test_environment_creates_tables_itself(env, expected):
    assert schema_owner_is_alembic(env) is expected


def test_the_api_image_starts_through_the_migrating_entrypoint():
    dockerfile = (BACKEND / "Dockerfile").read_text()
    assert re.search(r'^CMD \["/app/deployment/entrypoint.sh"\]', dockerfile, re.M)
    script = (BACKEND / "deployment" / "entrypoint.sh").read_text()
    assert "alembic upgrade head" in script and "exec gunicorn" in script
    assert script.index("alembic upgrade head") < script.index("exec gunicorn")
