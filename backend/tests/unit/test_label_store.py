"""The label store: the key it joins on, and how disagreeing sources resolve.

The corpus makes both of these load-bearing rather than theoretical:
105 of 1,487 files are byte-identical duplicates filed under different names,
80 of them carrying conflicting labels (bench/corpus_duplicates.py).
"""
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.hashing import (
    HASH_CHUNK_BYTES, HASH_HEX_LENGTH, is_content_hash, sha256_bytes, sha256_file,
)
from app.db.base_class import Base
from app.eval.labels import TARGET_ALL, resolve, resolve_all, to_binary_arrays
from app.models.labels import (
    SOURCE_DATASET, SOURCE_EXPERT, SOURCE_TRUST, SOURCE_USER_CORRECTION, Label,
)

pytestmark = pytest.mark.unit

H1 = "a" * 64
H2 = "b" * 64


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[Label.__table__])
    with Session(engine) as s:
        yield s


def _lab(**kw):
    base = dict(content_hash=H1, target="depth_fault", value=1, usable=True,
                source=SOURCE_DATASET, source_ref="ref",
                trust=SOURCE_TRUST[SOURCE_DATASET], labeled_at=None)
    base.update(kw)
    return type("Row", (), base)()


# ------------------------------------------------------------- hashing --

class TestHashing:
    def test_the_upload_path_and_the_importer_share_one_chunk_size(self):
        """If these diverged, labels would join to nothing -- and that looks
        exactly like 'no labels imported yet'."""
        from app.services.form_check_service import FormCheckService
        assert FormCheckService._HASH_CHUNK == HASH_CHUNK_BYTES

    def test_chunking_does_not_change_the_digest(self, tmp_path):
        p = tmp_path / "v.bin"
        p.write_bytes(b"x" * (3 * 1024 * 1024 + 7))
        assert sha256_file(p, chunk=1024) == sha256_file(p, chunk=1024 * 1024)

    def test_file_and_bytes_agree(self, tmp_path):
        data = b"some video bytes"
        p = tmp_path / "v.bin"
        p.write_bytes(data)
        assert sha256_file(p) == sha256_bytes(data)

    @pytest.mark.parametrize("value,ok", [
        ("a" * 64, True),
        ("A" * 64, False),          # uppercase: not what hexdigest() emits
        ("a" * 63, False),
        ("37121_13.mp4", False),    # the failure this guards: a filename
        (None, False),
        (12345, False),
    ])
    def test_shape_check_rejects_non_hashes(self, value, ok):
        assert is_content_hash(value) is ok

    def test_hash_length_matches_the_column(self):
        assert HASH_HEX_LENGTH == Label.__table__.c.content_hash.type.length


# ---------------------------------------------------------- the schema --

class TestSchema:
    def test_labels_are_keyed_on_content_hash_not_form_check(self):
        """A label is a statement about BYTES. Keyed on a form check it would
        die the moment the video is re-analysed under a new model -- exactly
        when the old ground truth is most wanted."""
        cols = Label.__table__.c
        assert "content_hash" in cols
        assert "form_check_id" not in cols
        assert not list(Label.__table__.foreign_keys)

    def test_reimport_of_the_same_source_upserts(self, session):
        row = dict(id=uuid.uuid4(), content_hash=H1, target="depth_fault",
                   value=1, source=SOURCE_DATASET, source_ref="r", trust=0.6)
        session.add(Label(**row))
        session.commit()
        session.add(Label(**{**row, "id": uuid.uuid4()}))
        with pytest.raises(sa.exc.IntegrityError):
            session.commit()

    def test_two_sources_may_disagree_about_the_same_video(self, session):
        """The key includes source and source_ref precisely so an expert review
        never silently overwrites the dataset label it disagrees with."""
        for src, ref, val in ((SOURCE_DATASET, "d", 1), (SOURCE_EXPERT, "e", 0)):
            session.add(Label(id=uuid.uuid4(), content_hash=H1,
                              target="depth_fault", value=val, source=src,
                              source_ref=ref, trust=SOURCE_TRUST[src]))
        session.commit()
        assert session.query(Label).count() == 2

    def test_subject_id_is_stored_so_leakage_is_queryable(self):
        """The splits are user-level. Storing the subject makes 'is this
        evaluation leaking?' a query rather than a cross-reference against a
        JSON file on somebody's desktop.

        Subject-level grouping is necessary and NOT sufficient (G-44): 45
        byte-identical videos span splits under different user ids. That is why
        the table is keyed on content_hash and not on subject_id."""
        assert "subject_id" in Label.__table__.c

    def test_trust_defaults_rank_the_sources(self):
        assert (SOURCE_TRUST[SOURCE_EXPERT]
                > SOURCE_TRUST[SOURCE_DATASET]
                > SOURCE_TRUST[SOURCE_USER_CORRECTION])


# -------------------------------------------------------- resolution --

class TestResolution:
    def test_highest_trust_wins(self):
        rows = [_lab(value=1, source=SOURCE_DATASET, trust=0.6, source_ref="d"),
                _lab(value=0, source=SOURCE_EXPERT, trust=1.0, source_ref="e")]
        r = resolve(rows, "depth_fault")
        assert r.value == 0 and r.source == SOURCE_EXPERT

    def test_a_tie_resolves_deterministically(self):
        """Equal trust, no timestamps. Without the source_ref tiebreak this
        resolves by whatever order the query returned -- stable until it is not."""
        a = [_lab(value=1, source_ref="zzz"), _lab(value=0, source_ref="aaa")]
        assert resolve(a, "depth_fault").value == resolve(list(reversed(a)),
                                                          "depth_fault").value

    def test_a_newer_label_wins_at_equal_trust(self):
        now = datetime.now(timezone.utc)
        rows = [_lab(value=1, source_ref="a", labeled_at=now - timedelta(days=1)),
                _lab(value=0, source_ref="b", labeled_at=now)]
        assert resolve(rows, "depth_fault").value == 0

    def test_disagreement_is_visible_not_just_resolved(self):
        """80 corpus videos carry conflicting labels on identical bytes. A
        reader that cannot see that will not ask why."""
        rows = [_lab(value=1, source_ref="a"), _lab(value=0, source_ref="b")]
        r = resolve(rows, "depth_fault")
        assert r.disputed is True
        assert len(r.contenders) == 2

    def test_agreement_is_not_reported_as_a_dispute(self):
        rows = [_lab(value=1, source_ref="a"), _lab(value=1, source_ref="b")]
        assert resolve(rows, "depth_fault").disputed is False

    def test_an_unusable_star_row_vetoes_every_target(self):
        """'This clip is unusable' is a statement about the clip, not about one
        question asked of it."""
        rows = [_lab(value=1, target="depth_fault"),
                _lab(target=TARGET_ALL, value=None, usable=False,
                     source=SOURCE_EXPERT, trust=1.0)]
        r = resolve(rows, "depth_fault")
        assert r.usable is False and r.value is None

    def test_a_target_nobody_answered_returns_none(self):
        assert resolve([_lab(target="posture_fault")], "depth_fault") is None

    def test_resolve_all_groups_by_video(self):
        rows = [_lab(content_hash=H1, value=1), _lab(content_hash=H2, value=0)]
        out = resolve_all(rows, "depth_fault")
        assert set(out) == {H1, H2}
        assert out[H2].value == 0


class TestAlignment:
    def test_only_videos_with_both_a_label_and_a_prediction_are_scored(self):
        resolved = resolve_all([_lab(content_hash=H1, value=1),
                                _lab(content_hash=H2, value=0)], "depth_fault")
        y, p, hashes = to_binary_arrays(resolved, {H1: 1})
        assert y == [1] and p == [1] and hashes == [H1]

    def test_unusable_labels_are_excluded(self):
        resolved = resolve_all(
            [_lab(content_hash=H1, target=TARGET_ALL, value=None, usable=False)],
            "depth_fault")
        y, _, _ = to_binary_arrays(resolved, {H1: 1})
        assert y == []

    def test_the_hashes_come_back_so_a_caller_can_say_which(self):
        """An evaluation that quietly drops the disagreements is how a coverage
        problem becomes an accuracy claim."""
        resolved = resolve_all([_lab(content_hash=H1, value=1)], "depth_fault")
        _, _, hashes = to_binary_arrays(resolved, {H1: 0})
        assert hashes == [H1]


class TestDisputeIsTrustTierAware:
    """A lower-trust source contradicting a higher-trust one is a RESOLVED
    question, not an open one.

    Treating it as open was badly wrong on this corpus: `category` (the folder
    a clip was collected into) and `multilabel_targets` (the class it was
    assigned) disagree on nearly every `depth_fault` video, because depth_fault
    is precisely the class that was reassigned from other folders. Counting
    those as disputes excluded 374 of 418 depth_fault videos (89.5%) while
    dropping 5.7% of posture_fault -- a filter that looks class-neutral and is
    not.
    """

    def test_equal_trust_disagreement_is_a_dispute(self):
        rows = [_lab(value=1, source_ref="a", trust=0.6),
                _lab(value=0, source_ref="b", trust=0.6)]
        assert resolve(rows, "depth_fault").disputed is True

    def test_a_lower_trust_contradiction_is_not_a_dispute(self):
        """The depth_fault case: provenance disagreeing with a judgement."""
        rows = [_lab(value=1, source_ref="targets", trust=0.6),
                _lab(value=0, source_ref="category", trust=0.3)]
        r = resolve(rows, "depth_fault")
        assert r.disputed is False
        assert r.value == 1, "the higher-trust source must still win"

    def test_the_losing_source_is_still_recorded(self):
        """Not a dispute is not the same as not visible."""
        rows = [_lab(value=1, source_ref="targets", trust=0.6),
                _lab(value=0, source_ref="category", trust=0.3)]
        assert len(resolve(rows, "depth_fault").contenders) == 2

    def test_three_tiers_only_compare_the_top(self):
        rows = [_lab(value=1, source_ref="expert", trust=1.0),
                _lab(value=0, source_ref="targets", trust=0.6),
                _lab(value=0, source_ref="category", trust=0.3)]
        assert resolve(rows, "depth_fault").disputed is False

    def test_a_single_source_is_never_disputed(self):
        assert resolve([_lab(value=1)], "depth_fault").disputed is False


def test_the_importer_gives_provenance_less_trust_than_judgement():
    """A folder is not a judgement. Pinned so a re-import cannot flatten them
    back to equal trust and silently re-disqualify 89.5% of depth_fault."""
    src = (Path(__file__).resolve().parents[2] / "scripts"
           / "import_labels.py").read_text()
    assert "category_trust" in src
    assert "A FOLDER IS NOT A JUDGEMENT" in src
