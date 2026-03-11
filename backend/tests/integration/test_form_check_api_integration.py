"""
FormCheck API — integration tests.

The actual integration tests live in the sub-package:

    tests/integration/form_checks/test_api.py

That sub-package has its own conftest.py that:
  - Boots a real PostgreSQL engine against the docker-compose test service
    (localhost:5434)
  - Seeds a User and ExerciseTemplate once per session
  - Mocks StorageService.upload_file and process_form_check_task.delay
  - Provides auth_client / anon_client fixtures via AsyncClient + dep-overrides

To run the full integration gate:
    docker compose -f tests/docker-compose.test.yml up -d
    cd backend
    pytest -q -m integration tests/integration/form_checks/ \\
        --override-ini="addopts=-q --asyncio-mode=auto --cov=app --cov-report=term-missing --cov-branch --no-cov-on-fail"
"""
import pytest

pytestmark = pytest.mark.integration
