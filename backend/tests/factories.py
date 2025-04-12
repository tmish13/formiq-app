"""Test data factories for creating consistent test data."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.models.user import User
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.video import Video
from app.models.form_check import FormCheck
from app.core.security import get_password_hash
import factory
from app.models.session import Session
from app.models.form_analysis import FormAnalysis

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    hashed_password = factory.LazyFunction(lambda: 'hashed_password_here')
    is_active = True
    is_superuser = False
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

class SessionFactory(factory.Factory):
    class Meta:
        model = Session

    id = factory.Sequence(lambda n: n)
    user_id = factory.SubFactory(UserFactory)
    token = factory.Sequence(lambda n: f'token_{n}')
    expires_at = factory.LazyFunction(lambda: datetime.utcnow() + timedelta(days=1))
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

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

class VideoFactory(factory.Factory):
    class Meta:
        model = Video

    id = factory.Sequence(lambda n: n)
    user_id = factory.SubFactory(UserFactory)
    filename = factory.Sequence(lambda n: f'video_{n}.mp4')
    s3_key = factory.Sequence(lambda n: f'uploads/video_{n}.mp4')
    status = 'pending'
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

class FormCheckFactory:
    @staticmethod
    def create(
        video_id: int = 1,
        feedback: list = None,
        score: float = 85.0,
        joint_angles: dict = None,
        spine_alignment: float = 0.95
    ) -> Dict[str, Any]:
        if feedback is None:
            feedback = ["Good depth", "Keep chest up"]
        if joint_angles is None:
            joint_angles = {"hip": 90, "knee": 90}
            
        return {
            "video_id": video_id,
            "feedback": feedback,
            "score": score,
            "joint_angles": joint_angles,
            "spine_alignment": spine_alignment,
            "created_at": datetime.utcnow()
        }

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