"""Base test class with common functionality."""
import pytest
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import settings
from app.db.base_class import Base
from app.main import app
from tests.factories import UserFactory, WorkoutFactory, ExerciseFactory, VideoFactory, FormCheckFactory

class BaseTest:
    """Base test class with common setup and teardown."""
    
    @pytest.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession) -> AsyncGenerator:
        """Setup test environment."""
        self.db = db_session
        self.app = app
        self.factories = {
            "user": UserFactory,
            "workout": WorkoutFactory,
            "exercise": ExerciseFactory,
            "video": VideoFactory,
            "form_check": FormCheckFactory
        }
        yield
        await self.cleanup()
    
    async def cleanup(self) -> None:
        """Cleanup test data."""
        for table in reversed(Base.metadata.sorted_tables):
            await self.db.execute(f"TRUNCATE TABLE {table.name} CASCADE")
        await self.db.commit()
    
    async def create_test_user(self, **kwargs) -> dict:
        """Create a test user."""
        user_data = self.factories["user"].create(**kwargs)
        user = await self.db.execute(
            "INSERT INTO users (email, hashed_password, full_name, is_active, is_superuser, subscription_tier, created_at) "
            "VALUES (:email, :hashed_password, :full_name, :is_active, :is_superuser, :subscription_tier, :created_at) "
            "RETURNING *",
            user_data
        )
        await self.db.commit()
        return user.first()
    
    async def create_test_workout(self, **kwargs) -> dict:
        """Create a test workout."""
        workout_data = self.factories["workout"].create(**kwargs)
        workout = await self.db.execute(
            "INSERT INTO workouts (name, description, user_id, created_at) "
            "VALUES (:name, :description, :user_id, :created_at) "
            "RETURNING *",
            workout_data
        )
        await self.db.commit()
        return workout.first()
    
    async def create_test_exercise(self, **kwargs) -> dict:
        """Create a test exercise."""
        exercise_data = self.factories["exercise"].create(**kwargs)
        exercise = await self.db.execute(
            "INSERT INTO exercises (name, description, sets, reps, workout_id, created_at) "
            "VALUES (:name, :description, :sets, :reps, :workout_id, :created_at) "
            "RETURNING *",
            exercise_data
        )
        await self.db.commit()
        return exercise.first()
    
    async def create_test_video(self, **kwargs) -> dict:
        """Create a test video."""
        video_data = self.factories["video"].create(**kwargs)
        video = await self.db.execute(
            "INSERT INTO videos (filename, exercise_type, user_id, status, created_at) "
            "VALUES (:filename, :exercise_type, :user_id, :status, :created_at) "
            "RETURNING *",
            video_data
        )
        await self.db.commit()
        return video.first()
    
    async def create_test_form_check(self, **kwargs) -> dict:
        """Create a test form check."""
        form_check_data = self.factories["form_check"].create(**kwargs)
        form_check = await self.db.execute(
            "INSERT INTO form_checks (video_id, feedback, score, joint_angles, spine_alignment, created_at) "
            "VALUES (:video_id, :feedback, :score, :joint_angles, :spine_alignment, :created_at) "
            "RETURNING *",
            form_check_data
        )
        await self.db.commit()
        return form_check.first() 