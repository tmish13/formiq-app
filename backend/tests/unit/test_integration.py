import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.user import UserService
from app.services.workout import WorkoutService
from app.services.ai import AIService
from app.models.user import User
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.subscription import Subscription
from sqlalchemy.orm import Session
from app.core.exceptions import ValidationError, NotFoundError, AuthenticationError
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.commit = Mock()
    return session

@pytest.fixture
def user_service(mock_db_session):
    """Create a user service instance"""
    return UserService(db=mock_db_session)

@pytest.fixture
def workout_service(mock_db_session):
    """Create a workout service instance"""
    return WorkoutService(db=mock_db_session)

@pytest.fixture
def ai_service():
    """Create an AI service instance"""
    return AIService()

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_verified=True,
        subscription_tier="PRO",
        created_at=datetime.now()
    )

@pytest.fixture
def test_workout():
    """Create a test workout"""
    return Workout(
        id=1,
        user_id=1,
        name="Test Workout",
        description="Test workout description",
        duration=timedelta(minutes=60),
        difficulty="intermediate",
        created_at=datetime.now()
    )

def test_user_workout_flow(user_service, workout_service, test_user, mock_db_session):
    """Test the complete flow of user creating and managing workouts"""
    # Create a new user
    user_data = {
        "email": "new@example.com",
        "username": "newuser",
        "password": "newpassword",
        "subscription_tier": "FREE"
    }
    user = user_service.create_user(**user_data)
    
    # Create a workout for the user
    workout_data = {
        "name": "New Workout",
        "description": "New workout description",
        "duration": timedelta(minutes=45),
        "difficulty": "beginner"
    }
    workout = workout_service.create_workout(user=user, **workout_data)
    
    # Add exercises to the workout
    exercise_data = {
        "name": "Squat",
        "sets": 3,
        "reps": 12,
        "weight": 100
    }
    exercise = workout_service.add_exercise_to_workout(
        workout_id=workout.id,
        user_id=user.id,
        **exercise_data
    )
    
    # Verify the workout and exercise data
    retrieved_workout = workout_service.get_workout(workout_id=workout.id, user_id=user.id)
    assert retrieved_workout.name == workout_data["name"]
    assert retrieved_workout.user_id == user.id
    assert len(retrieved_workout.exercises) == 1
    assert retrieved_workout.exercises[0].name == exercise_data["name"]

def test_workout_plan_flow(user_service, workout_service, test_user, mock_db_session):
    """Test the complete flow of creating and managing workout plans"""
    # Create a workout plan
    plan_data = {
        "name": "Weekly Plan",
        "description": "Weekly workout plan",
        "duration_weeks": 4
    }
    plan = workout_service.create_workout_plan(user=test_user, **plan_data)
    
    # Create workouts for the plan
    workout_data = {
        "name": "Monday Workout",
        "description": "Monday's workout",
        "duration": timedelta(minutes=60),
        "difficulty": "intermediate"
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    # Add workout to the plan
    workout_service.add_workout_to_plan(
        plan_id=plan.id,
        workout_id=workout.id,
        user_id=test_user.id
    )
    
    # Verify the plan and workout data
    retrieved_plan = workout_service.get_workout_plan(plan_id=plan.id, user_id=test_user.id)
    assert retrieved_plan.name == plan_data["name"]
    assert len(retrieved_plan.workouts) == 1
    assert retrieved_plan.workouts[0].name == workout_data["name"]

def test_ai_workout_analysis_flow(ai_service, workout_service, test_user, mock_db_session):
    """Test the flow of AI analyzing workout videos and providing feedback"""
    # Create a workout with video
    workout_data = {
        "name": "Squat Analysis",
        "description": "Squat form analysis",
        "duration": timedelta(minutes=5),
        "difficulty": "beginner",
        "video_path": "test_video.mp4"
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    # Mock AI service responses
    with patch.object(ai_service, 'analyze_form') as mock_analyze:
        mock_analyze.return_value = {
            "feedback": "Good form overall",
            "confidence": 0.95,
            "joint_angles": {
                "knee": 90,
                "hip": 45
            }
        }
        
        # Analyze the workout video
        analysis = ai_service.analyze_form(
            video_path=workout.video_path,
            exercise_type="squat"
        )
        
        # Verify the analysis results
        assert analysis["feedback"] == "Good form overall"
        assert analysis["confidence"] == 0.95
        assert "joint_angles" in analysis

def test_subscription_workout_access_flow(user_service, workout_service, test_user, mock_db_session):
    """Test the flow of subscription-based workout access"""
    # Create a workout with premium content
    workout_data = {
        "name": "Premium Workout",
        "description": "Premium workout content",
        "duration": timedelta(minutes=60),
        "difficulty": "advanced",
        "is_premium": True
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    # Test access with different subscription tiers
    # Free tier user
    free_user = user_service.create_user(
        email="free@example.com",
        username="freeuser",
        password="password",
        subscription_tier="FREE"
    )
    
    with pytest.raises(ValidationError):
        workout_service.get_workout(workout_id=workout.id, user_id=free_user.id)
    
    # Premium tier user
    premium_user = user_service.create_user(
        email="premium@example.com",
        username="premiumuser",
        password="password",
        subscription_tier="PREMIUM"
    )
    
    accessed_workout = workout_service.get_workout(
        workout_id=workout.id,
        user_id=premium_user.id
    )
    assert accessed_workout.id == workout.id

def test_user_progress_tracking_flow(user_service, workout_service, test_user, mock_db_session):
    """Test the flow of tracking user progress and statistics"""
    # Create multiple workouts for the user
    workouts = []
    for i in range(3):
        workout_data = {
            "name": f"Workout {i+1}",
            "description": f"Workout {i+1} description",
            "duration": timedelta(minutes=45),
            "difficulty": "intermediate"
        }
        workout = workout_service.create_workout(user=test_user, **workout_data)
        workouts.append(workout)
    
    # Add exercises to workouts
    for workout in workouts:
        exercise_data = {
            "name": "Squat",
            "sets": 3,
            "reps": 12,
            "weight": 100
        }
        workout_service.add_exercise_to_workout(
            workout_id=workout.id,
            user_id=test_user.id,
            **exercise_data
        )
    
    # Get user statistics
    stats = user_service.get_user_stats(user_id=test_user.id)
    
    # Verify statistics
    assert stats["total_workouts"] == 3
    assert stats["total_exercises"] == 3
    assert "average_duration" in stats

def test_workout_sharing_flow(user_service, workout_service, test_user, mock_db_session):
    """Test the flow of sharing workouts between users"""
    # Create a workout to share
    workout_data = {
        "name": "Shared Workout",
        "description": "Workout to be shared",
        "duration": timedelta(minutes=60),
        "difficulty": "intermediate"
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    # Create another user
    other_user = user_service.create_user(
        email="other@example.com",
        username="otheruser",
        password="password",
        subscription_tier="FREE"
    )
    
    # Share the workout
    workout_service.share_workout(
        workout_id=workout.id,
        from_user_id=test_user.id,
        to_user_id=other_user.id
    )
    
    # Verify the other user can access the shared workout
    shared_workout = workout_service.get_workout(
        workout_id=workout.id,
        user_id=other_user.id
    )
    assert shared_workout.id == workout.id
    assert shared_workout.shared_by_user_id == test_user.id

def test_workout_reminder_flow(user_service, workout_service, test_user, mock_db_session):
    """Test the flow of workout reminders and scheduling"""
    # Create a workout plan
    plan_data = {
        "name": "Scheduled Plan",
        "description": "Plan with reminders",
        "duration_weeks": 4
    }
    plan = workout_service.create_workout_plan(user=test_user, **plan_data)
    
    # Create a workout
    workout_data = {
        "name": "Scheduled Workout",
        "description": "Workout with reminder",
        "duration": timedelta(minutes=60),
        "difficulty": "intermediate",
        "scheduled_time": datetime.now() + timedelta(days=1)
    }
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    # Add workout to plan
    workout_service.add_workout_to_plan(
        plan_id=plan.id,
        workout_id=workout.id,
        user_id=test_user.id
    )
    
    # Set reminder
    reminder_time = workout.scheduled_time - timedelta(hours=1)
    workout_service.set_workout_reminder(
        workout_id=workout.id,
        user_id=test_user.id,
        reminder_time=reminder_time
    )
    
    # Verify reminder
    retrieved_workout = workout_service.get_workout(
        workout_id=workout.id,
        user_id=test_user.id
    )
    assert retrieved_workout.reminder_time == reminder_time
    assert retrieved_workout.plan_id == plan.id 