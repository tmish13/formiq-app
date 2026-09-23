"""What a human said about a video, keyed so it survives re-analysis.

KEYED ON content_hash, NEVER form_check_id
------------------------------------------
A label is a statement about BYTES. A form check is one attempt at scoring
those bytes under one model version. Key the label on the form check and it
dies the moment the video is re-analysed under a new model -- which is exactly
when you most want to compare the new answer against the old ground truth.

`subject_id` is carried explicitly rather than derived. The splits are
user-level (1625 videos = 1625 users), so no SUBJECT spans splits. Storing the
subject makes "is this evaluation leaking?" a query rather than a
cross-reference against a JSON file on someone's desktop.

Subject-level is necessary and NOT sufficient. This docstring used to claim
leakage had been ruled out entirely, which was wrong (G-44). 105 corpus videos are
byte-identical duplicates under different names, 45 spanning splits and 104
filed under different USER IDS -- so the user-level partition is clean and the
content-level one is not. That is exactly why labels are keyed on
`content_hash`: the hash is the identifier that would have caught it, and a
subject id cannot.

TRUST IS A NUMBER, NOT A HIERARCHY
----------------------------------
Three sources disagree about the same video and all three are kept. The
importer never overwrites one source with another; the unique key includes
`source` and `source_ref` so a re-import upserts its OWN rows and leaves the
others alone. Resolution is the reader's job, which is the only place that can
know what it is resolving for.
"""
import uuid

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.db.base_class import Base
from app.models.base import SQLiteUUID

# Where a label came from. `dataset` is the corpus as shipped; `expert` is a
# hand review; `user_correction` is the person in the video disagreeing.
SOURCE_DATASET = "dataset"
SOURCE_EXPERT = "expert"
SOURCE_USER_CORRECTION = "user_correction"
LABEL_SOURCES = (SOURCE_DATASET, SOURCE_EXPERT, SOURCE_USER_CORRECTION)

#: Default trust per source. A hand review outranks the corpus; the subject's
#: own correction is the least reliable about FORM even though it is the most
#: reliable about intent. These are defaults written at import time, not a
#: hierarchy enforced by the schema -- a specific row can carry its own.
SOURCE_TRUST = {
    SOURCE_DATASET: 0.6,
    SOURCE_EXPERT: 1.0,
    SOURCE_USER_CORRECTION: 0.4,
}

#: Targets the corpus actually carries. `*` means "this clip is unusable for
#: every target", which is how `messy` is represented -- a real statement, and
#: different from having no row.
TARGET_ALL = "*"


class Label(Base):
    """One (video, target, source) judgement."""

    __tablename__ = "labels"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                        nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    # --- identity ---
    content_hash = Column(String(64), nullable=False, index=True)
    video_name = Column(String(255), nullable=True, index=True)
    subject_id = Column(String(64), nullable=True, index=True)
    split = Column(String(16), nullable=True, index=True)

    # --- the judgement ---
    target = Column(String(32), nullable=False)
    value = Column(Integer, nullable=True)      # 0/1; NULL when only `usable` is meant
    usable = Column(Boolean, nullable=False, default=True)

    # --- provenance ---
    source = Column(String(32), nullable=False)
    source_ref = Column(String(255), nullable=False, default="")
    trust = Column(Float, nullable=False, default=SOURCE_TRUST[SOURCE_DATASET])
    labeled_by = Column(String(128), nullable=True)
    labeled_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        # Re-import upserts its own rows. `source` and `source_ref` are IN the
        # key so an expert review never silently overwrites the dataset label
        # it disagrees with -- both are kept and the reader resolves them.
        UniqueConstraint("content_hash", "target", "source", "source_ref",
                         name="uq_labels_hash_target_source_ref"),
        # The evaluation join: every label for a target, filtered by split.
        Index("ix_labels_target_split", "target", "split"),
    )

    def __repr__(self) -> str:
        return (f"<Label {self.video_name or self.content_hash[:8]} "
                f"{self.target}={self.value} via {self.source}>")
