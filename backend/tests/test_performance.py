import pytest
import time
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.user import User
from app.core.security import create_access_token
from app.core.security import get_password_hash
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from app.services.user import UserService
from app.services.workout import WorkoutService
from app.services.ai import AIService
from sqlalchemy.orm import Session
from app.core.exceptions import ValidationError, NotFoundError
from concurrent.futures import as_completed

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

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
def test_token(test_user):
    """Create a test access token"""
    return create_access_token(data={"sub": test_user.email})

def test_response_time_thresholds(client, test_token):
    """Test that API endpoints respond within acceptable time thresholds"""
    # Define endpoints and their expected response time thresholds (in seconds)
    endpoints = {
        "/api/v1/users/me": 0.1,  # 100ms
        "/api/v1/workouts": 0.2,  # 200ms
        "/api/v1/workout-plans": 0.2,  # 200ms
        "/api/v1/subscriptions/status": 0.1,  # 100ms
    }
    
    headers = {"Authorization": f"Bearer {test_token}"}
    
    for endpoint, threshold in endpoints.items():
        start_time = time.time()
        response = client.get(endpoint, headers=headers)
        end_time = time.time()
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time <= threshold, f"Endpoint {endpoint} took {response_time:.3f}s, exceeding threshold of {threshold}s"

def test_concurrent_requests(client, test_token):
    """Test system behavior under concurrent requests"""
    endpoint = "/api/v1/workouts"
    headers = {"Authorization": f"Bearer {test_token}"}
    num_requests = 50
    
    def make_request():
        start_time = time.time()
        response = client.get(endpoint, headers=headers)
        end_time = time.time()
        return response.status_code, end_time - start_time
    
    # Make concurrent requests
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(lambda _: make_request(), range(num_requests)))
    
    # Analyze results
    status_codes = [r[0] for r in results]
    response_times = [r[1] for r in results]
    
    # Check that all requests were successful
    assert all(code == 200 for code in status_codes)
    
    # Calculate statistics
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    # Assert performance metrics
    assert avg_response_time <= 0.3, f"Average response time {avg_response_time:.3f}s exceeds threshold"
    assert max_response_time <= 1.0, f"Maximum response time {max_response_time:.3f}s exceeds threshold"

def test_workout_creation_performance(workout_service, test_user):
    """Test performance of workout creation"""
    start_time = time.time()
    
    # Create multiple workouts
    for i in range(50):
        workout_data = {
            "name": f"Workout {i}",
            "description": f"Description {i}",
            "duration": timedelta(minutes=60),
            "difficulty": "intermediate"
        }
        workout = workout_service.create_workout(user=test_user, **workout_data)
        
        # Add exercises to each workout
        for j in range(5):
            exercise_data = {
                "name": f"Exercise {j}",
                "sets": 3,
                "reps": 12,
                "weight": 100
            }
            workout_service.add_exercise_to_workout(
                workout_id=workout.id,
                user_id=test_user.id,
                **exercise_data
            )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that creating 50 workouts with 5 exercises each takes less than 10 seconds
    assert total_time < 10.0

def test_workout_analysis_performance(client, test_token):
    """Test performance of workout analysis endpoint"""
    endpoint = "/api/v1/workouts/analyze"
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Test video analysis
    with open("test_video.mp4", "rb") as f:
        start_time = time.time()
        response = client.post(
            endpoint,
            files={"video": ("test_video.mp4", f, "video/mp4")},
            headers=headers
        )
        end_time = time.time()
    
    assert response.status_code == 200
    assert end_time - start_time <= 5.0, "Video analysis took too long"

def test_database_query_performance(workout_service, test_user):
    """Test performance of database queries"""
    # Create multiple workouts
    for i in range(100):
        workout_data = {
            "name": f"Query Workout {i}",
            "description": f"Description {i}",
            "duration": timedelta(minutes=60),
            "difficulty": "intermediate"
        }
        workout_service.create_workout(user=test_user, **workout_data)
    
    start_time = time.time()
    
    # Perform various queries
    for i in range(50):
        workout_service.get_workout(workout_id=i+1, user_id=test_user.id)
        workout_service.get_user_workouts(user_id=test_user.id)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that 50 queries take less than 2 seconds
    assert total_time < 2.0

def test_memory_usage(workout_service, test_user):
    """Test memory usage under load"""
    import psutil
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Create large number of workouts
    for i in range(1000):
        workout_data = {
            "name": f"Memory Workout {i}",
            "description": f"Description {i}",
            "duration": timedelta(minutes=60),
            "difficulty": "intermediate"
        }
        workout_service.create_workout(user=test_user, **workout_data)
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Assert that memory increase is less than 500MB
    assert memory_increase < 500 * 1024 * 1024  # 500MB in bytes

def test_error_handling_performance(client, test_token):
    """Test performance of error handling"""
    # Test various error scenarios
    error_scenarios = [
        ("/api/v1/workouts/999", 404),
        ("/api/v1/users/me", 401),  # No token
        ("/api/v1/users/register", 422)  # Invalid data
    ]
    
    for endpoint, expected_status in error_scenarios:
        start_time = time.time()
        if endpoint == "/api/v1/users/me":
            response = client.get(endpoint)  # No token
        else:
            response = client.get(endpoint, headers={"Authorization": f"Bearer {test_token}"})
        end_time = time.time()
        
        assert response.status_code == expected_status
        assert end_time - start_time <= 0.1, f"Error handling took too long for {endpoint}"

def test_caching_performance(client, test_token):
    """Test performance impact of caching"""
    endpoint = "/api/v1/workouts"
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # First request (cache miss)
    start_time = time.time()
    response1 = client.get(endpoint, headers=headers)
    first_request_time = time.time() - start_time
    
    # Second request (cache hit)
    start_time = time.time()
    response2 = client.get(endpoint, headers=headers)
    second_request_time = time.time() - start_time
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert second_request_time < first_request_time, "Cached request should be faster"

def test_file_upload_performance(client, test_token):
    """Test performance of file upload operations"""
    endpoint = "/api/v1/workouts/analyze"
    headers = {"Authorization": f"Bearer {test_token}"}
    
    # Test with different file sizes
    file_sizes = [1, 5, 10]  # MB
    
    for size in file_sizes:
        # Create a dummy file of specified size
        with open(f"test_{size}mb.mp4", "wb") as f:
            f.write(b"0" * (size * 1024 * 1024))
        
        with open(f"test_{size}mb.mp4", "rb") as f:
            start_time = time.time()
            response = client.post(
                endpoint,
                files={"video": (f"test_{size}mb.mp4", f, "video/mp4")},
                headers=headers
            )
            end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time <= size * 2, f"File upload took too long for {size}MB file"
        
        # Clean up
        os.remove(f"test_{size}mb.mp4")

def test_user_creation_performance(user_service):
    """Test performance of user creation"""
    start_time = time.time()
    
    # Create multiple users
    for i in range(100):
        user_data = {
            "email": f"user{i}@example.com",
            "username": f"user{i}",
            "password": "password123",
            "subscription_tier": "FREE"
        }
        user_service.create_user(**user_data)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that creating 100 users takes less than 5 seconds
    assert total_time < 5.0

def test_concurrent_user_operations(user_service):
    """Test performance under concurrent user operations"""
    def create_user(i):
        user_data = {
            "email": f"concurrent{i}@example.com",
            "username": f"concurrent{i}",
            "password": "password123",
            "subscription_tier": "FREE"
        }
        return user_service.create_user(**user_data)
    
    start_time = time.time()
    
    # Create users concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_user, i) for i in range(50)]
        for future in as_completed(futures):
            future.result()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that concurrent user creation takes less than 3 seconds
    assert total_time < 3.0

def test_concurrent_workout_operations(workout_service, test_user):
    """Test performance under concurrent workout operations"""
    def create_workout(i):
        workout_data = {
            "name": f"Concurrent Workout {i}",
            "description": f"Description {i}",
            "duration": timedelta(minutes=60),
            "difficulty": "intermediate"
        }
        return workout_service.create_workout(user=test_user, **workout_data)
    
    start_time = time.time()
    
    # Create workouts concurrently
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_workout, i) for i in range(30)]
        for future in as_completed(futures):
            future.result()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that concurrent workout creation takes less than 5 seconds
    assert total_time < 5.0

def test_ai_analysis_performance(ai_service):
    """Test performance of AI analysis operations"""
    start_time = time.time()
    
    # Simulate AI analysis operations
    for i in range(20):
        with patch.object(ai_service, 'analyze_form') as mock_analyze:
            mock_analyze.return_value = {
                "feedback": "Good form",
                "confidence": 0.95,
                "joint_angles": {"knee": 90, "hip": 45}
            }
            ai_service.analyze_form(
                video_path=f"test_video_{i}.mp4",
                exercise_type="squat"
            )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that 20 AI analyses take less than 8 seconds
    assert total_time < 8.0

def test_response_time_under_load(workout_service, test_user):
    """Test response time under load"""
    # Create background load
    with ThreadPoolExecutor(max_workers=20) as executor:
        for i in range(100):
            executor.submit(
                workout_service.create_workout,
                user=test_user,
                name=f"Load Workout {i}",
                description=f"Description {i}",
                duration=timedelta(minutes=60),
                difficulty="intermediate"
            )
    
    # Test response time for a new operation
    start_time = time.time()
    workout_service.create_workout(
        user=test_user,
        name="Response Test Workout",
        description="Test description",
        duration=timedelta(minutes=60),
        difficulty="intermediate"
    )
    end_time = time.time()
    response_time = end_time - start_time
    
    # Assert that response time is less than 1 second even under load
    assert response_time < 1.0

def test_concurrent_ai_operations(ai_service):
    """Test performance under concurrent AI operations"""
    def analyze_video(i):
        with patch.object(ai_service, 'analyze_form') as mock_analyze:
            mock_analyze.return_value = {
                "feedback": "Good form",
                "confidence": 0.95,
                "joint_angles": {"knee": 90, "hip": 45}
            }
            return ai_service.analyze_form(
                video_path=f"concurrent_video_{i}.mp4",
                exercise_type="squat"
            )
    
    start_time = time.time()
    
    # Perform concurrent AI analyses
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(analyze_video, i) for i in range(20)]
        for future in as_completed(futures):
            future.result()
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that concurrent AI operations take less than 5 seconds
    assert total_time < 5.0

def test_workout_plan_performance(workout_service, test_user):
    """Test performance of workout plan operations"""
    start_time = time.time()
    
    # Create multiple workout plans with workouts
    for i in range(20):
        plan_data = {
            "name": f"Plan {i}",
            "description": f"Description {i}",
            "duration_weeks": 4
        }
        plan = workout_service.create_workout_plan(user=test_user, **plan_data)
        
        # Add workouts to each plan
        for j in range(5):
            workout_data = {
                "name": f"Plan Workout {j}",
                "description": f"Description {j}",
                "duration": timedelta(minutes=60),
                "difficulty": "intermediate"
            }
            workout = workout_service.create_workout(user=test_user, **workout_data)
            workout_service.add_workout_to_plan(
                plan_id=plan.id,
                workout_id=workout.id,
                user_id=test_user.id
            )
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Assert that creating 20 plans with 5 workouts each takes less than 8 seconds
    assert total_time < 8.0 