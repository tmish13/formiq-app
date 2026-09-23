"""Schema properties of the decision trail that are load-bearing, not cosmetic.

Each of these is something a plausible future edit could undo silently:
adding a convenience FK to analysis_runs, dropping the unique constraint
because a retry hit it, switching the models to BaseModel for consistency.
"""
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base_class import Base
from app.models.audit import (
    RUN_STATUSES,
    RUN_STATUS_ABANDONED,
    RUN_STATUS_RUNNING,
    AnalysisRun,
    CheckerDecision,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    tables = [AnalysisRun.__table__, CheckerDecision.__table__]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as s:
        s.execute(sa.text("PRAGMA foreign_keys=ON"))
        yield s


# --------------------------------------------------------------- structure --

def test_analysis_runs_has_no_foreign_keys():
    """An audit row must not change when its subject is deleted.
    posture_v1_inference_logs uses ON DELETE SET NULL and therefore keeps rows
    that can no longer be joined to anything -- the worst of both outcomes."""
    assert list(AnalysisRun.__table__.foreign_keys) == []


def test_checker_decisions_cascades_from_its_run():
    """The opposite call: a decision is a PART of a run and has no meaning
    without it."""
    fks = list(CheckerDecision.__table__.c.run_id.foreign_keys)
    assert len(fks) == 1
    assert fks[0].column.table.name == "analysis_runs"
    assert fks[0].ondelete == "CASCADE"


def test_the_five_identity_columns_exist():
    """A verdict is explicable only against all five. pose_pass_id is the one
    that is easy to think optional: two MediaPipe passes moved 33 of 221
    PostureV1 verdicts (14.9%) with no change visible in aggregate F1."""
    cols = AnalysisRun.__table__.c
    for name in ("content_hash", "model_version", "spec_hash",
                 "rules_spec_hash", "pose_pass_id"):
        assert name in cols, name


def test_models_do_not_inherit_the_kwarg_filtering_base():
    """BaseModel.__init__ silently drops unknown kwargs -- the same bug class
    as the phantom `summary` and `error_details` columns. An audit table is the
    last place a typo should become a dropped field."""
    from app.models.base import BaseModel
    assert not issubclass(AnalysisRun, BaseModel)
    assert not issubclass(CheckerDecision, BaseModel)


def test_unknown_field_raises_rather_than_being_dropped():
    with pytest.raises(TypeError):
        AnalysisRun(not_a_column="x")


def test_reaper_index_exists():
    """The sweep for unclosed runs scans (status, started_at) every minute."""
    names = {i.name for i in AnalysisRun.__table__.indexes}
    assert "ix_analysis_runs_status_started_at" in names


# ------------------------------------------------------------------ behaviour --

def test_duplicate_checker_write_is_rejected(session):
    """A task that dies after writing its checker rows and is redelivered must
    not double-insert them."""
    run = AnalysisRun(id=uuid.uuid4(), status=RUN_STATUS_RUNNING)
    session.add(run)
    session.commit()

    def _row():
        return CheckerDecision(id=uuid.uuid4(), run_id=run.id,
                               checker_name="depth_parallel_v0",
                               target="depth", decision="at_depth")

    session.add(_row())
    session.commit()
    session.add(_row())
    with pytest.raises(sa.exc.IntegrityError):
        session.commit()


def test_same_checker_may_answer_different_targets(session):
    """The uniqueness is per (run, checker, TARGET) -- one checker producing a
    depth verdict and a posture verdict is legitimate."""
    run = AnalysisRun(id=uuid.uuid4(), status=RUN_STATUS_RUNNING)
    session.add(run)
    session.commit()
    for target in ("depth", "posture"):
        session.add(CheckerDecision(id=uuid.uuid4(), run_id=run.id,
                                    checker_name="c", target=target,
                                    decision="uncertain"))
    session.commit()
    assert session.query(CheckerDecision).count() == 2


def test_deleting_a_run_deletes_its_decisions(session):
    run = AnalysisRun(id=uuid.uuid4(), status=RUN_STATUS_RUNNING)
    session.add(run)
    session.commit()
    session.add(CheckerDecision(id=uuid.uuid4(), run_id=run.id,
                                checker_name="c", target="depth",
                                decision="shallow"))
    session.commit()
    session.delete(run)
    session.commit()
    assert session.query(CheckerDecision).count() == 0


def test_fitted_and_advisory_default_to_the_safe_value(session):
    """Defaulting `fitted` to True would let an unfitted checker's verdict be
    read as calibrated by anything querying the table directly."""
    run = AnalysisRun(id=uuid.uuid4(), status=RUN_STATUS_RUNNING)
    session.add(run)
    session.commit()
    d = CheckerDecision(id=uuid.uuid4(), run_id=run.id, checker_name="c",
                        target="depth", decision="uncertain")
    session.add(d)
    session.commit()
    session.refresh(d)
    assert d.fitted is False
    assert d.abstained is False
    assert d.advisory is False


def test_a_run_starts_unclosed(session):
    """A killed worker leaves status='running' AND finished_at IS NULL. That
    pair is what the reaper sweeps, so both halves must hold on insert."""
    run = AnalysisRun(id=uuid.uuid4())
    session.add(run)
    session.commit()
    session.refresh(run)
    assert run.status == RUN_STATUS_RUNNING
    assert run.finished_at is None
    assert run.started_at is not None


def test_run_statuses_are_short_enough_for_the_column():
    limit = AnalysisRun.__table__.c.status.type.length
    assert all(len(s) <= limit for s in RUN_STATUSES)
    assert RUN_STATUS_ABANDONED in RUN_STATUSES


class TestDecisionWritesAreNotBatched:
    """Regression: three decisions in one transaction used to fail entirely.

    SQLAlchemy 2.0 batches same-table INSERTs through insertmanyvalues and
    matches the returned rows back using the primary key as a sentinel.
    `SQLiteUUID` BINDS a str and RETURNS a uuid.UUID, so the sentinel never
    matched:

        Can't match sentinel values in result set to parameter sets

    Measured on 8 live analyses: every run opened, every run closed, and every
    single decision row was lost -- with only a warning, because the recorder
    is best-effort by design. `posture_v1_inference_logs` uses the same type
    and never hit it, because a task adds exactly one telemetry row.
    """

    @pytest.mark.asyncio
    async def test_each_decision_is_flushed_on_its_own(self):
        from unittest.mock import AsyncMock, MagicMock

        from app.services.decisions.recorder import record_decisions
        from app.services.decisions.types import CheckerOutcome

        session = AsyncMock()
        session.add = MagicMock()
        outcomes = [
            CheckerOutcome(checker_name=f"c{i}", target=f"t{i}", decision="X")
            for i in range(3)
        ]
        written = await record_decisions(session, run_id=uuid.uuid4(),
                                         outcomes=outcomes)
        assert written == 3
        assert session.add.call_count == 3
        # One flush per row: three separate INSERTs, never one batch.
        assert session.flush.await_count == 3

    def test_three_decisions_commit_together(self, session):
        """The shape that broke. SQLite does not reproduce the sentinel bug, so
        this pins the intent rather than the driver behaviour; the live proof is
        bench/stage_a_decision_trail.sh assertion A2."""
        run = AnalysisRun(id=uuid.uuid4(), status=RUN_STATUS_RUNNING)
        session.add(run)
        session.commit()
        for name in ("posture_v1", "depth_parallel_v0", "knees_forward_v0"):
            session.add(CheckerDecision(id=uuid.uuid4(), run_id=run.id,
                                        checker_name=name, target=name,
                                        decision="UNCERTAIN"))
        session.commit()
        assert session.query(CheckerDecision).count() == 3
