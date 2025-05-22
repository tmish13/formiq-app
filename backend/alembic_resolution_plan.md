# Alembic Sanity and Completion Plan

This document outlines the steps to resolve identified issues with the Alembic migration system and ensure it accurately reflects the complete database schema. This is a follow-up to Phase 1 cleanup.

## Issues Identified

1.  **Duplicate Revision ID:** The migration script `backend/alembic/versions/003_add_indexes.py` incorrectly declares `revision = '002'` and `down_revision = '001'`, conflicting with `backend/alembic/versions/002_add_indexes.py`.
2.  **Incomplete Schema Coverage:** The `videos` table (and potentially others if models were added after the initial migrations) is not created by any of the existing Alembic migration scripts (`001_initial.py`, `002_add_indexes.py`, `003_add_indexes.py`).
3.  **Alembic Version Table (User Confirmation):** The existence and current revision in the `alembic_version` table in the database needs to be noted by the user for context, although its existence is implied by recent `alembic current` command behavior.

## Resolution Plan

### Task 1: Correct Duplicate Alembic Revision ID

*   **Objective:** Ensure each Alembic migration script in `backend/alembic/versions/` has a unique revision ID and correct `down_revision` linkage.
*   **File to Modify:** `backend/alembic/versions/003_add_indexes.py`
*   **Actions:**
    1.  Change `revision = '002'` to `revision = '003'`. (Or a new unique ID if '003' is problematic for some reason, but '003' aligns with the filename prefix).
    2.  Change `down_revision = '001'` to `down_revision = '002'`. This correctly links it after `002_add_indexes.py`.
*   **Verification:** Run `alembic -c backend/config/alembic.ini history | cat`. The history should be linear and the "Revision 002 is present more than once" warning should be gone.

### Task 2: Ensure Full Schema Coverage with Alembic

*   **Objective:** Update Alembic migrations to include all necessary tables, particularly the `videos` table.
*   **Actions:**
    1.  **Verify Target Models:** Ensure all SQLAlchemy models defined in `backend/app/models/` (especially `backend/app/models/video.py` and any others potentially missed) are correctly imported directly or indirectly by `backend/alembic/env.py` in the `target_metadata` section.
    2.  **Generate New Migration:** Run the Alembic `autogenerate` command to detect differences between the current models and the database schema state as understood by the (corrected) migration history. This will create a new migration script for missing tables/columns/etc.
        ```bash
        alembic -c backend/config/alembic.ini revision -m "add_videos_table_and_other_missing_schema" --autogenerate
        ```
    3.  **Review Generated Script:** Carefully review the newly generated migration script. Ensure it correctly creates the `videos` table (including the `additional_metadata` column and other fields) and any other missing schema elements. Make manual adjustments if autogenerate missed something or did something unexpected.
    4.  **Test Migration (Optional but Recommended):** If possible, test applying this new migration on a development database that is up-to-date with the `003` revision to ensure it applies cleanly.
*   **Verification:** After applying the new migration (`alembic -c backend/config/alembic.ini upgrade head`), the `videos` table and all other application tables should exist in the database with the correct schema.

### Task 3: Database State Confirmation (Manual by User)

*   **Objective:** Understand the current state of the database in relation to Alembic migrations.
*   **Actions (Manual - To be performed by the user):
    1.  **Check `alembic_version` Table:** Connect to your primary development/staging database. Execute a query to check the `alembic_version` table. Note the `version_num` column value. This tells you which Alembic revision the database believes it is at.
        ```sql
        SELECT version_num FROM alembic_version;
        ```
    2.  **Compare with Alembic History:** Compare this `version_num` with the output of `alembic -c backend/config/alembic.ini history`. This helps understand if the database is aligned with the latest migration head or an older one.
*   **Note:** This information is crucial before applying new migrations, especially the one generated in Task 2.

## Final Verification for This Plan

*   The "Revision 002 is present more than once" warning is resolved.
*   A new Alembic migration successfully creates the `videos` table and any other missing schema elements.
*   The application's database schema can be fully created and managed by the Alembic migrations in `backend/alembic/versions/`.

This plan will ensure the Alembic migration system is healthy, complete, and reliable for future development. 