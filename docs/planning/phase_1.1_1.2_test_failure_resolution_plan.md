# AI Pipeline Steps 1.1 & 1.2 - Test Failure Resolution Plan

**Goal:** Systematically identify, address, and resolve all errors and warnings preventing the successful execution of unit and integration tests for AI Pipeline Steps 1.1 (Video Processing) and 1.2 (Pose Detection), as defined in `phase_1.1_1.2_finalization_and_testing_plan.md`.

---

## Phase 1: Core Test Environment Setup Issues

**Goal:** Resolve fundamental configuration and database setup errors within the pytest environment.

### Task 1: Resolve `AttributeError` for `TEST_DATABASE_URL` in `conftest.py`

*   **Problem Description:** Tests are failing during setup with `AttributeError: 'Settings' object has no attribute 'TEST_DATABASE_URL'`. This occurs in `backend/tests/conftest.py` within the `initialize_test_db` fixture when trying to access `settings.TEST_DATABASE_URL`.
*   **File(s) Involved:**
    *   `backend/tests/conftest.py`
    *   `backend/app/core/config.py`
*   **Analysis:** The `Settings` class in `backend/app/core/config.py` does not define `TEST_DATABASE_URL`. For the test environment, `SQLALCHEMY_DATABASE_URI` is dynamically set to `sqlite:///./test.db` by the `assemble_db_connection` validator. This URI should be used for creating the synchronous engine for Alembic migrations and initial table creation in tests.
*   **Proposed Solution/Action:**
    1.  Modify `backend/tests/conftest.py` in the `initialize_test_db` fixture.
    2.  Change the line using `settings.TEST_DATABASE_URL` to use `settings.SQLALCHEMY_DATABASE_URI` for the synchronous database operations (Alembic, `create_all`).
*   **Status:** Done (Changed `settings.TEST_DATABASE_URL` to `settings.SQLALCHEMY_DATABASE_URI` in `backend/tests/conftest.py`)
*   **Verification:**
    *   The `AttributeError: 'Settings' object has no attribute 'TEST_DATABASE_URL'` no longer appears in the pytest output.
    *   The debug print `Using SQLALCHEMY_DATABASE_URI: sqlite:///./test.db` (or the actual URI used) appears in the `initialize_test_db` fixture output.
    *   Subsequent debug prints from `initialize_test_db` (e.g., regarding AlembicConfig import, database initialization start) appear.

### Task 2: Investigate `initialize_test_db` Fixture Execution

*   **Problem Description:** Debug print statements from the `initialize_test_db` session-scoped autouse fixture in `backend/tests/conftest.py` are not appearing in the pytest output. This strongly suggests the fixture is not running, or is failing before any output. This leads to tables (e.g., `videos`) not being created, causing `sqlite3.OperationalError: no such table`.
*   **File(s) Involved:**
    *   `backend/tests/conftest.py`
*   **Analysis:** If `initialize_test_db` doesn't run, the database schema is not set up for the test session. The `autouse=True` and `scope="session"` decorators should ensure its execution.
*   **Proposed Solution/Action:**
    1.  Temporarily simplify the `initialize_test_db` fixture in `backend/tests/conftest.py` to its bare minimum to confirm entry:
        ```python
        @pytest.fixture(scope="session", autouse=True)
        async def initialize_test_db():
            print("MINIMAL INITIALIZE_TEST_DB FIXTURE ENTERED")
            yield
            print("MINIMAL INITIALIZE_TEST_DB FIXTURE EXITED")
        ```
    2.  Run tests again and check if "MINIMAL INITIALIZE_TEST_DB FIXTURE ENTERED" appears.
    3.  If it appears, gradually reintroduce parts of the original fixture's logic, interspersed with print statements, to pinpoint where it might be failing or why further prints are suppressed.
    4.  If it *doesn't* appear, investigate pytest collection for `backend/tests/conftest.py` or potential shadowing by other conftest files or configurations.
*   **Status:** To Do
*   **Verification:**
    *   The "MINIMAL INITIALIZE_TEST_DB FIXTURE ENTERED" print statement appears in the pytest output.
    *   Further investigation based on this outcome leads to understanding and resolving why the full fixture wasn't running or logging.
--- 