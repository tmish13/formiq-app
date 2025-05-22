"""Test data factories for creating consistent test data."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.models.user import User
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.video import Video
from app.models.form_check import FormCheck
from app.core.security import get_password_hash
import factory
from factory import alchemy, Faker, LazyAttribute, SubFactory, Maybe
from app.models.user_session import UserSession as Session
from app.models.form_analysis import FormAnalysis
import uuid
from app.models.enums import FormCheckStatus, Difficulty, MuscleGroup
from app.core.database import async_session_factory
from app.models.exercise import ExerciseTemplate
import random

class UserFactory(alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = async_session_factory
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    hashed_password = factory.LazyFunction(lambda: "$2b$12$3toMYVVrWzSxsYOPT9bBL.JFXf2zOnw6bYQZ18HbrWhYFRAlEDL7q")
    username = factory.Faker('user_name')
    full_name = factory.Faker('name')
    is_active = True
    is_superuser = False
    subscription_tier = "free"
    is_email_verified = False
    is_verified = False
    created_at = factory.LazyFunction(lambda: datetime.utcnow())
    updated_at = factory.LazyFunction(lambda: datetime.utcnow())

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        print(f"UserFactory._create called with model_class: {model_class}, args: {args}, kwargs: {kwargs}")
        return super()._create(model_class, *args, **kwargs)

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        print(f"UserFactory._build called with model_class: {model_class}, args: {args}, kwargs: {kwargs}")
        return super()._build(model_class, *args, **kwargs)

class SessionFactory(factory.Factory):
    class Meta:
        model = Session

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.SubFactory(UserFactory)
    session_id = factory.LazyFunction(uuid.uuid4)
    user_agent = factory.Faker('user_agent')
    ip_address = factory.Faker('ipv4')
    auth_method = factory.Iterator(["password", "oauth"])
    device_token = factory.LazyFunction(lambda: str(uuid.uuid4()) if random.choice([True, False]) else None)
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=7))
    last_active = factory.LazyFunction(datetime.utcnow)

class WorkoutFactory:
    @staticmethod
    def create(
        name: str = "Test Workout",
        description: str = "Test workout description",
        user_id: int = 1
    ) -> Dict[str, Any]:
        return {
            "name": name,
            "description": description,
            "user_id": user_id,
            "created_at": datetime.utcnow()
        }

class ExerciseFactory:
    @staticmethod
    def create(
        name: str = "Test Exercise",
        description: str = "Test exercise description",
        sets: int = 3,
        reps: int = 10,
        workout_id: int = 1
    ) -> Dict[str, Any]:
        return {
            "name": name,
            "description": description,
            "sets": sets,
            "reps": reps,
            "workout_id": workout_id,
            "created_at": datetime.utcnow()
        }

class VideoFactory(alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Video
        sqlalchemy_session = async_session_factory
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.SubFactory(UserFactory)
    filename = factory.Sequence(lambda n: f'video_{n}.mp4')
    object_key = factory.Sequence(lambda n: f'uploads/video_{n}.mp4')
    mime_type = 'video/mp4'
    status = 'pending'
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

class ExerciseTemplateFactory(alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ExerciseTemplate
        sqlalchemy_session = async_session_factory
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker('word')
    description = factory.Faker('sentence')
    video_url = factory.Faker('url')
    difficulty = factory.LazyFunction(lambda: Difficulty.BEGINNER)
    muscle_group = factory.LazyFunction(lambda: MuscleGroup.FULL_BODY)
    equipment = "None"

class FormCheckFactory(alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = FormCheck
        sqlalchemy_session = async_session_factory
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid.uuid4)
    video_url = factory.Faker('url')
    exercise = factory.Maybe(
        'exercise_id',
        None,
        SubFactory(ExerciseTemplateFactory)
    )
    exercise_id = factory.Maybe(
        'exercise_id',
        factory.LazyAttribute(lambda obj: obj.exercise.id if obj.exercise else None),
        factory.SelfAttribute('exercise_id')
    )
    user = SubFactory(UserFactory)
    user_id = factory.LazyAttribute(lambda obj: obj.user.id)
    feedback = "Good form. Keep your back straight."
    score = factory.LazyFunction(lambda: random.uniform(0, 100))
    keypoints = factory.LazyFunction(lambda: {"key": "value"})
    status = FormCheckStatus.PENDING
    analysis_url = factory.Faker('url')
    overall_feedback = factory.Faker('sentence')
    issues = factory.LazyFunction(lambda: {"issue": "description"})
    processing_time = factory.LazyFunction(lambda: random.uniform(0, 10))
    confidence_score = factory.LazyFunction(lambda: random.uniform(0, 1))
    form_metadata = factory.LazyFunction(lambda: {"metadata": "value"})
    results = factory.LazyFunction(lambda: {"results": "value"})

class FormAnalysisFactory(factory.Factory):
    class Meta:
        model = FormAnalysis

    id = factory.Sequence(lambda n: n)
    video_id = factory.SubFactory(VideoFactory)
    user_id = factory.SubFactory(UserFactory)
    status = 'pending'
    feedback = factory.Faker('text')
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow) 