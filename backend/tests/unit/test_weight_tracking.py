"""Tests for weight_kg and reps storage and schema round-trip."""
import pytest
from uuid import uuid4
from datetime import datetime


class TestFormCheckSchemaWeightReps:
    """Schema validation for the new weight_kg and reps fields."""

    def test_form_check_create_accepts_weight_and_reps(self):
        from app.schemas.form_check import FormCheckCreate
        from app.models.enums import FormCheckStatus

        schema = FormCheckCreate(
            user_id=uuid4(),
            exercise_id=uuid4(),
            video_url="https://s3.amazonaws.com/bucket/video.mp4",
            status=FormCheckStatus.PENDING,
            weight_kg=100.0,
            reps=5,
        )
        assert schema.weight_kg == 100.0
        assert schema.reps == 5

    def test_form_check_create_weight_optional(self):
        from app.schemas.form_check import FormCheckCreate
        from app.models.enums import FormCheckStatus

        schema = FormCheckCreate(
            user_id=uuid4(),
            exercise_id=uuid4(),
            video_url="https://s3.amazonaws.com/bucket/video.mp4",
            status=FormCheckStatus.PENDING,
        )
        assert schema.weight_kg is None
        assert schema.reps is None

    def test_form_check_response_includes_weight_and_reps(self):
        from app.schemas.form_check import FormCheckResponse

        schema = FormCheckResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            exercise_id=str(uuid4()),
            video_url="https://s3.amazonaws.com/bucket/video.mp4",
            status="pending",
            created_at=datetime.utcnow(),
            weight_kg=80.5,
            reps=3,
        )
        assert schema.weight_kg == 80.5
        assert schema.reps == 3

    def test_form_check_response_video_url_optional(self):
        """video_url is now Optional in FormCheckResponse for s3:// stored URLs."""
        from app.schemas.form_check import FormCheckResponse

        schema = FormCheckResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            exercise_id=str(uuid4()),
            video_url=None,
            status="pending",
            created_at=datetime.utcnow(),
        )
        assert schema.video_url is None

    def test_form_check_response_video_key(self):
        from app.schemas.form_check import FormCheckResponse

        key = "form_check_videos/user123/1234_abc_video.mp4"
        schema = FormCheckResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            exercise_id=str(uuid4()),
            video_url="s3://bucket/" + key,
            status="pending",
            created_at=datetime.utcnow(),
            video_key=key,
        )
        assert schema.video_key == key


class TestFormCheckModelWeightRepsColumns:
    """FormCheck ORM model has weight_kg, reps, exercise_type, video_key columns."""

    def test_form_check_has_weight_kg_column(self):
        from app.models.form_check import FormCheck
        assert hasattr(FormCheck, 'weight_kg')

    def test_form_check_has_reps_column(self):
        from app.models.form_check import FormCheck
        assert hasattr(FormCheck, 'reps')

    def test_form_check_has_exercise_type_column(self):
        from app.models.form_check import FormCheck
        assert hasattr(FormCheck, 'exercise_type')

    def test_form_check_has_video_key_column(self):
        from app.models.form_check import FormCheck
        assert hasattr(FormCheck, 'video_key')
