# Backend File-by-File Audit & Recommendations

This document lists every file and directory in the backend, grouped by directory, with a clear recommendation for each (keep, consolidate, or delete) and a brief rationale. Use this as a working document for backend cleanup and alignment to the AI pipeline integration plan.

---

## Root of `backend/`

| File/Directory | Recommendation | Rationale |
|---|---|---|
| config/ | Keep | Contains configuration/logging structure. |
| app/ | Keep | Main application code. |
| tests/ | Keep | All automated tests. |
| scripts/ | Keep | Useful for DB, migration, and data scripts. |
| logs/ | Delete (add to .gitignore) | Log files should not be versioned. |
| migrations/ | Keep | Alembic migration scripts. |
| .pytest_cache/ | Delete (add to .gitignore) | Pytest cache, not needed in VCS. |
| .benchmarks/ | Delete (add to .gitignore) | Benchmark artifacts, not needed in VCS. |
| formiq.egg-info/ | Delete (add to .gitignore) | Build artifact. |
| uploads/ | Keep | Likely used for uploaded files. |
| deployment/ | Keep | Deployment configs (docker-compose, etc). |
| docs/ | Keep | Project documentation. |
| alembic.ini | Keep | Alembic config. |
| requirements.txt | Keep | Main dependencies. |
| requirements-test.txt | Keep | Test dependencies. |
| requirements-dev.txt | Keep | Dev dependencies. |
| pyproject.toml | Keep | Build/config file. |
| Dockerfile | Keep | Containerization. |
| .dockerignore | Keep | Docker build hygiene. |
| .env | Delete (if secrets) or add to .gitignore | Should not be versioned. |
| .env.example | Keep | Example env file. |
| .env.test | Delete (if secrets) or add to .gitignore | Should not be versioned. |
| LICENSE | Keep | Legal. |
| Makefile | Keep | Build/utility commands. |
| README.md | Keep | Project overview. |
| start_formiq.sh | Keep | Startup script. |
| dev.db | Delete (add to .gitignore) | Local DB, not for VCS. |
| test.db | Delete (add to .gitignore) | Local DB, not for VCS. |
| backend_review_and_alignment.md | Keep | Planning/audit doc. |
| core_ai_pipeline_testing_and_completion_plan.md | Keep | Planning doc. |
| phase_2_task_1_2_service_standardization.md | Keep | Planning doc. |
| phase_2_completion_plan.md | Keep | Planning doc. |
| phase_1_completion_plan.md | Keep | Planning doc. |
| alembic_resolution_plan.md | Keep | Planning doc. |
| pytest.ini | Keep | Pytest config. |
| pytest_debug_phase2_tasks.log | Delete (add to .gitignore) | Debug log. |
| pytestdebug_ai.log | Delete (add to .gitignore) | Debug log. |
| pytestdebug.log | Delete (add to .gitignore) | Debug log. |
| reset_migrations.py | Keep | Migration utility. |
| setup.py | Keep | Build script. |
| consolidate_migrations.py | Keep | Migration utility. |
| docker-entrypoint.sh | Keep | Docker entrypoint. |

---

## `backend/config/`

| File/Directory | Recommendation | Rationale |
|---|---|---|
| logs/ | Delete (if only runtime logs) | Should not be versioned. |

---

## `backend/app/`

| File/Directory | Recommendation | Rationale |
|---|---|---|
| core/ | Keep | Core app logic, config, celery, etc. |
| utils/ | Keep | Utility functions. |
| repositories/ | Keep | DB access layer. |
| main.py | Keep | FastAPI entrypoint. |
| services/ | Keep | Main business logic/services. |
| tasks/ | Keep | Celery and async task logic. |
| schemas/ | Keep | Pydantic schemas. |
| api/ | Keep | API endpoints. |
| models/ | Keep | SQLAlchemy models. |
| db/ | Keep | DB session/base. |
| middleware/ | Keep | Custom middleware. |
| templates/ | Keep | Jinja/email templates. |
| email-templates/ | Keep | Email templates. |
| docs/ | Keep | API and internal docs. |
| __init__.py | Keep | Module marker. |

---

## `backend/app/core/` (and subdirs)

| File/Directory | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | Core config, celery, security, etc. |
| utils/ | Keep | Pose/keypoint utils. |
| db/ | Keep | (Empty, but keep for structure.) |
| middleware/ | Keep | Core middleware. |
| stripe/ | Keep | Stripe integration. |
| storage/ | Keep | S3 and storage logic. |
| schemas/ | Keep | Error schemas. |
| analysis/ | Keep | Form analysis logic. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/services/`

| File | Recommendation | Rationale |
|---|---|---|
| All *_service.py | Keep | Core business logic. |
| ai_service.py | Keep | Core AI logic. |
| video_processing_service.py | Keep | Video processing. |
| dynamic_form_analysis_service.py | Keep | Rule-based analysis. |
| biomechanics_service.py | Keep | Geometry/biomechanics. |
| feedback_service.py | Keep | Feedback delivery. |
| personalized_feedback_service.py | Keep | LLM feedback. |
| tasks.py | Consolidate into tasks/ | Move Celery tasks to tasks/ dir. |
| base_service.py | Keep | CRUD base. |
| __init__.py | Keep | Module marker. |
| ai/ | Keep (if used) | Subdir for AI logic. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/tasks/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | Celery and async task logic. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/utils/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | Utility functions. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/repositories/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | DB access layer. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/schemas/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | Pydantic schemas. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/api/` (and subdirs)

| File/Directory | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | API endpoints. |
| v1/ | Keep | Versioned API. |
| endpoints/ | Keep | Endpoint grouping. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/models/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | SQLAlchemy models. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/db/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | DB session/base. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/app/middleware/`

| File | Recommendation | Rationale |
|---|---|---|
| All .py files | Keep | Custom middleware. |

---

## `backend/app/templates/` and `backend/app/email-templates/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Keep | Email/Jinja templates. |

---

## `backend/app/docs/` (and subdirs)

| File | Recommendation | Rationale |
|---|---|---|
| All files | Keep | API/internal docs. |

---

## `backend/tests/` (and subdirs)

| File/Directory | Recommendation | Rationale |
|---|---|---|
| All files | Keep | Automated tests. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/scripts/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Keep | DB/data/migration scripts. |

---

## `backend/logs/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Delete (add to .gitignore) | Log files should not be versioned. |

---

## `backend/migrations/` (and subdirs)

| File/Directory | Recommendation | Rationale |
|---|---|---|
| All files | Keep | Alembic migration scripts. |
| __pycache__/ | Delete (add to .gitignore) | Python cache. |

---

## `backend/deployment/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Keep | Deployment configs. |

---

## `backend/docs/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Keep | Project documentation. |

---

## `backend/formiq.egg-info/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Delete (add to .gitignore) | Build artifact. |

---

## `backend/uploads/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Keep | Uploaded files. |

---

## `backend/.pytest_cache/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Delete (add to .gitignore) | Pytest cache. |

---

## `backend/.benchmarks/`

| File | Recommendation | Rationale |
|---|---|---|
| All files | Delete (add to .gitignore) | Benchmark artifacts. |

---

# Notes
- For all `__pycache__/`, `.pytest_cache/`, `.benchmarks/`, `logs/`, `formiq.egg-info/`, and DB/log files: add to `.gitignore` and remove from VCS.
- For any secrets in `.env`, `.env.test`, etc., ensure they are not versioned.
- For planning/markdown docs: keep if useful for ongoing work, otherwise archive.
- For any "consolidate" recommendations, move logic to the recommended location and remove the old file.

---

_Edit this file as you make changes to keep your audit up to date._ 