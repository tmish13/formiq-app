import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.workout import WorkoutService, WorkoutError
from app.models.workout import Workout, Exercise, WorkoutPlan
from app.models.user import User
from sqlalchemy.orm import Session
from app.core.exceptions import NotFoundError, ValidationError
from app.core.config import settings
from app.core.security import create_access_token

@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    session = Mock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    return session

@pytest.fixture
def workout_service(mock_db_session):
    """Create a workout service instance"""
    return WorkoutService(db=mock_db_session)

@pytest.fixture
def test_user():
    """Create a test user"""
    return User(
        id=1,
        email="test@example.com",
        username="testuser",
        subscription_tier="PRO"
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

@pytest.fixture
def test_exercise():
    """Create a test exercise"""
    return Exercise(
        id=1,
        name="Squat",
        description="Basic squat exercise",
        muscle_groups=["legs", "core"],
        equipment_needed=["barbell", "squat rack"],
        difficulty="intermediate",
        video_url="https://example.com/squat.mp4"
    )

def test_create_workout(workout_service, test_user, mock_db_session):
    """Test creating a new workout"""
    workout_data = {
        "name": "New Workout",
        "description": "New workout description",
        "duration": timedelta(minutes=45),
        "difficulty": "beginner"
    }
    
    workout = workout_service.create_workout(user=test_user, **workout_data)
    
    assert workout.name == workout_data["name"]
    assert workout.user_id == test_user.id
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_get_workout(workout_service, test_workout, mock_db_session):
    """Test retrieving a workout"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_workout
    
    workout = workout_service.get_workout(workout_id=1, user_id=1)
    
    assert workout.id == test_workout.id
    assert workout.name == test_workout.name

def test_get_workout_not_found(workout_service, mock_db_session):
    """Test retrieving a non-existent workout"""
    with pytest.raises(NotFoundError):
        workout_service.get_workout(workout_id=999, user_id=1)

def test_update_workout(workout_service, test_workout, mock_db_session):
    """Test updating a workout"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_workout
    
    update_data = {
        "name": "Updated Workout",
        "description": "Updated description"
    }
    
    updated_workout = workout_service.update_workout(
        workout_id=1,
        user_id=1,
        **update_data
    )
    
    assert updated_workout.name == update_data["name"]
    assert updated_workout.description == update_data["description"]
    mock_db_session.commit.assert_called_once()

def test_delete_workout(workout_service, test_workout, mock_db_session):
    """Test deleting a workout"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_workout
    
    workout_service.delete_workout(workout_id=1, user_id=1)
    
    mock_db_session.delete.assert_called_once_with(test_workout)
    mock_db_session.commit.assert_called_once()

def test_get_user_workouts(workout_service, test_user, mock_db_session):
    """Test retrieving all workouts for a user"""
    mock_workouts = [
        Workout(id=1, user_id=test_user.id, name="Workout 1"),
        Workout(id=2, user_id=test_user.id, name="Workout 2")
    ]
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_workouts
    
    workouts = workout_service.get_user_workouts(user_id=test_user.id)
    
    assert len(workouts) == 2
    assert all(w.user_id == test_user.id for w in workouts)

def test_add_exercise_to_workout(workout_service, test_workout, mock_db_session):
    """Test adding an exercise to a workout"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_workout
    
    exercise_data = {
        "name": "Squat",
        "sets": 3,
        "reps": 12,
        "weight": 100
    }
    
    exercise = workout_service.add_exercise_to_workout(
        workout_id=1,
        user_id=1,
        **exercise_data
    )
    
    assert exercise.name == exercise_data["name"]
    assert exercise.workout_id == test_workout.id
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_remove_exercise_from_workout(workout_service, test_workout, mock_db_session):
    """Test removing an exercise from a workout"""
    exercise = Exercise(
        id=1,
        workout_id=test_workout.id,
        name="Squat"
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = exercise
    
    workout_service.remove_exercise_from_workout(
        workout_id=1,
        exercise_id=1,
        user_id=1
    )
    
    mock_db_session.delete.assert_called_once_with(exercise)
    mock_db_session.commit.assert_called_once()

def test_create_workout_plan(workout_service, test_user, mock_db_session):
    """Test creating a workout plan"""
    plan_data = {
        "name": "Weekly Plan",
        "description": "Weekly workout plan",
        "duration_weeks": 4
    }
    
    plan = workout_service.create_workout_plan(user=test_user, **plan_data)
    
    assert plan.name == plan_data["name"]
    assert plan.user_id == test_user.id
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_get_workout_plan(workout_service, test_user, mock_db_session):
    """Test retrieving a workout plan"""
    plan = WorkoutPlan(
        id=1,
        user_id=test_user.id,
        name="Test Plan"
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = plan
    
    retrieved_plan = workout_service.get_workout_plan(plan_id=1, user_id=test_user.id)
    
    assert retrieved_plan.id == plan.id
    assert retrieved_plan.name == plan.name

def test_update_workout_plan(workout_service, test_user, mock_db_session):
    """Test updating a workout plan"""
    plan = WorkoutPlan(
        id=1,
        user_id=test_user.id,
        name="Test Plan"
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = plan
    
    update_data = {
        "name": "Updated Plan",
        "description": "Updated description"
    }
    
    updated_plan = workout_service.update_workout_plan(
        plan_id=1,
        user_id=test_user.id,
        **update_data
    )
    
    assert updated_plan.name == update_data["name"]
    assert updated_plan.description == update_data["description"]
    mock_db_session.commit.assert_called_once()

def test_delete_workout_plan(workout_service, test_user, mock_db_session):
    """Test deleting a workout plan"""
    plan = WorkoutPlan(
        id=1,
        user_id=test_user.id,
        name="Test Plan"
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = plan
    
    workout_service.delete_workout_plan(plan_id=1, user_id=test_user.id)
    
    mock_db_session.delete.assert_called_once_with(plan)
    mock_db_session.commit.assert_called_once()

def test_get_user_workout_plans(workout_service, test_user, mock_db_session):
    """Test retrieving all workout plans for a user"""
    mock_plans = [
        WorkoutPlan(id=1, user_id=test_user.id, name="Plan 1"),
        WorkoutPlan(id=2, user_id=test_user.id, name="Plan 2")
    ]
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_plans
    
    plans = workout_service.get_user_workout_plans(user_id=test_user.id)
    
    assert len(plans) == 2
    assert all(p.user_id == test_user.id for p in plans)

def test_add_workout_to_plan(workout_service, test_user, mock_db_session):
    """Test adding a workout to a workout plan"""
    test_plan = WorkoutPlan(
        id=1,
        user_id=1,
        name="Test Plan",
        duration_weeks=4
    )
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_plan
    
    plan = workout_service.add_workout_to_plan(
        plan_id=1,
        user_id=1,
        workout_id=1,
        day_of_week=1
    )
    
    assert len(plan.workouts) == 1
    assert plan.workouts[0].workout_id == 1
    mock_db_session.commit.assert_called_once()

def test_remove_workout_from_plan(workout_service, test_user, mock_db_session):
    """Test removing a workout from a workout plan"""
    test_plan = WorkoutPlan(
        id=1,
        user_id=1,
        name="Test Plan",
        duration_weeks=4
    )
    test_plan.workouts = [{"workout_id": 1, "day_of_week": 1}]
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_plan
    
    plan = workout_service.remove_workout_from_plan(
        plan_id=1,
        user_id=1,
        workout_id=1
    )
    
    assert len(plan.workouts) == 0
    mock_db_session.commit.assert_called_once()

def test_validate_workout_data(workout_service):
    """Test workout data validation"""
    # Test invalid duration
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name="Test Workout",
            duration=timedelta(minutes=-1)  # Invalid duration
        )
    
    # Test invalid difficulty
    with pytest.raises(ValidationError):
        workout_service.create_workout(
            user=test_user,
            name="Test Workout",
            difficulty="invalid"  # Invalid difficulty level
        )

def test_validate_workout_plan_data(workout_service):
    """Test workout plan data validation"""
    # Test invalid duration_weeks
    with pytest.raises(ValidationError):
        workout_service.validate_workout_plan_data(duration_weeks=0)
    
    # Test invalid difficulty
    with pytest.raises(ValidationError):
        workout_service.validate_workout_plan_data(difficulty="invalid")

def test_validate_exercise_data(workout_service, test_workout, mock_db_session):
    """Test exercise data validation"""
    mock_db_session.query.return_value.filter.return_value.first.return_value = test_workout
    
    # Test invalid sets
    with pytest.raises(ValidationError):
        workout_service.add_exercise_to_workout(
            workout_id=1,
            user_id=1,
            name="Squat",
            sets=0  # Invalid number of sets
        )
    
    # Test invalid reps
    with pytest.raises(ValidationError):
        workout_service.add_exercise_to_workout(
            workout_id=1,
            user_id=1,
            name="Squat",
            reps=0  # Invalid number of reps
        )
    
    # Test invalid weight
    with pytest.raises(ValidationError):
        workout_service.add_exercise_to_workout(
            workout_id=1,
            user_id=1,
            name="Squat",
            weight=-1  # Invalid weight
        ) 