"""Base test class with common functionality."""
import pytest
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import settings
from app.db.base_class import Base
from app.main import app
from tests.utils.factories import UserFactory, WorkoutFactory, ExerciseFactory, VideoFactory, FormCheckFactory

class BaseTest:
    """Base test class with common setup and teardown."""
    
    @pytest.fixture(autouse=True)
    async def setup(self, db_session: AsyncSession) -> AsyncGenerator:
        """Setup test environment.
        
        Args:
            db_session: Async database session
            
        Yields:
            None
        """
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
        """Cleanup test data by truncating all tables."""
        for table in reversed(Base.metadata.sorted_tables):
            await self.db.execute(f"DELETE FROM {table.name}")
        await self.db.commit()
    
    async def create_test_user(self, **kwargs) -> Dict[str, Any]:
        """Create a test user.
        
        Args:
            **kwargs: User attributes to override defaults
            
        Returns:
            Dict[str, Any]: Created user data
        """
        user_data = self.factories["user"].create(**kwargs)
        query = """
            INSERT INTO users (
                email, hashed_password, full_name, is_active,
                is_superuser, subscription_tier, created_at
            )
            VALUES (
                :email, :hashed_password, :full_name, :is_active,
                :is_superuser, :subscription_tier, :created_at
            )
            RETURNING *
        """
        result = await self.db.execute(query, user_data)
        await self.db.commit()
        return dict(result.first()._mapping)
    
    async def create_test_workout(self, **kwargs) -> Dict[str, Any]:
        """Create a test workout.
        
        Args:
            **kwargs: Workout attributes to override defaults
            
        Returns:
            Dict[str, Any]: Created workout data
        """
        workout_data = self.factories["workout"].create(**kwargs)
        query = """
            INSERT INTO workouts (
                name, description, user_id, created_at
            )
            VALUES (
                :name, :description, :user_id, :created_at
            )
            RETURNING *
        """
        result = await self.db.execute(query, workout_data)
        await self.db.commit()
        return dict(result.first()._mapping)
    
    async def create_test_exercise(self, **kwargs) -> Dict[str, Any]:
        """Create a test exercise.
        
        Args:
            **kwargs: Exercise attributes to override defaults
            
        Returns:
            Dict[str, Any]: Created exercise data
        """
        exercise_data = self.factories["exercise"].create(**kwargs)
        query = """
            INSERT INTO exercises (
                name, description, sets, reps, workout_id, created_at
            )
            VALUES (
                :name, :description, :sets, :reps, :workout_id, :created_at
            )
            RETURNING *
        """
        result = await self.db.execute(query, exercise_data)
        await self.db.commit()
        return dict(result.first()._mapping)
    
    async def create_test_video(self, **kwargs) -> Dict[str, Any]:
        """Create a test video.
        
        Args:
            **kwargs: Video attributes to override defaults
            
        Returns:
            Dict[str, Any]: Created video data
        """
        video_data = self.factories["video"].create(**kwargs)
        query = """
            INSERT INTO videos (
                filename, exercise_type, user_id, status, created_at
            )
            VALUES (
                :filename, :exercise_type, :user_id, :status, :created_at
            )
            RETURNING *
        """
        result = await self.db.execute(query, video_data)
        await self.db.commit()
        return dict(result.first()._mapping)
    
    async def create_test_form_check(self, **kwargs) -> Dict[str, Any]:
        """Create a test form check.
        
        Args:
            **kwargs: Form check attributes to override defaults
            
        Returns:
            Dict[str, Any]: Created form check data
        """
        form_check_data = self.factories["form_check"].create(**kwargs)
        query = """
            INSERT INTO form_checks (
                video_id, feedback, score, joint_angles,
                spine_alignment, created_at
            )
            VALUES (
                :video_id, :feedback, :score, :joint_angles,
                :spine_alignment, :created_at
            )
            RETURNING *
        """
        result = await self.db.execute(query, form_check_data)
        await self.db.commit()
        return dict(result.first()._mapping) 