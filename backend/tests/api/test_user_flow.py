import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import io

from app.core.config import settings
from app.models.user import User # For test_user fixture type hint

# Fixtures like async_client, async_session, test_user, current_user_headers
# are assumed to be provided by conftest.py.

@pytest.mark.asyncio
async def test_complete_user_flow(async_client: AsyncClient, async_session: AsyncSession):
    '''Test complete user flow from registration to form analysis via API endpoints.'''
    
    # 1. User Registration
    unique_email = f'''flow_user_{uuid.uuid4()}@example.com'''
    register_payload = {
        "email": unique_email,
        "password": "FlowTest123!",
        "full_name": "Flow Test User",
        "confirm_password": "FlowTest123!" # Assuming confirm_password is required
    }
    register_response = await async_client.post(
        f'''{settings.API_V1_STR}/auth/register''', json=register_payload
    )
    assert register_response.status_code == 201, register_response.text
    user_data = register_response.json()
    assert "id" in user_data
    
    # 2. User Login
    login_payload = {"username": unique_email, "password": "FlowTest123!"}
    login_response = await async_client.post(
        f'''{settings.API_V1_STR}/auth/login''', data=login_payload
    )
    assert login_response.status_code == 200, login_response.text
    tokens = login_response.json()
    assert "access_token" in tokens
    headers = {"Authorization": f'''Bearer {tokens['access_token']}'''}
    
    # 3. Upload Video
    dummy_video_content = b'''dummy video content for flow test'''
    files = {"video_upload": ("flow_test_video.mp4", io.BytesIO(dummy_video_content), "video/mp4")}
    submit_data = {"exercise_name": "SQUAT", "notes": "Flow test video submit"}
    
    upload_response = await async_client.post(
        f'''{settings.API_V1_STR}/form-checks/submit''',
        headers=headers,
        files=files,
        data=submit_data 
    )
    assert upload_response.status_code == 202, upload_response.text
    form_check_data = upload_response.json()
    assert "id" in form_check_data
    form_check_id = form_check_data["id"]

    # 4. Get Form Check History
    history_response = await async_client.get(
        f'''{settings.API_V1_STR}/form-checks/history''', 
        headers=headers
    )
    assert history_response.status_code == 200, history_response.text
    history = history_response.json()
    assert len(history) >= 1 
    found_in_history = any(item["id"] == form_check_id for item in history)
    assert found_in_history, f'''Form check {form_check_id} not found in history.'''

@pytest.mark.asyncio
async def test_error_scenarios(async_client: AsyncClient, test_user: User):
    '''Test various API error scenarios in the user flow.'''
    
    # 1. Registration with existing email
    duplicate_payload = {
        "email": test_user.email,
        "password": "ErrorTest123!",
        "full_name": "Error Test User",
        "confirm_password": "ErrorTest123!"
    }
    duplicate_response = await async_client.post(
        f'''{settings.API_V1_STR}/auth/register''', json=duplicate_payload
    )
    assert duplicate_response.status_code == 400, duplicate_response.text
    
    # 2. Login with wrong password
    wrong_login_payload = {"username": test_user.email, "password": "WrongPass123!"}
    wrong_login_response = await async_client.post(
        f'''{settings.API_V1_STR}/auth/login''', data=wrong_login_payload
    )
    assert wrong_login_response.status_code == 401, wrong_login_response.text
    
    # 3. Access protected route without token
    no_auth_response = await async_client.get(f'''{settings.API_V1_STR}/auth/me''')
    assert no_auth_response.status_code == 401, no_auth_response.text
    
    # 4. Access with invalid token
    invalid_headers = {"Authorization": "Bearer invalid_token"}
    invalid_auth_response = await async_client.get(
        f'''{settings.API_V1_STR}/auth/me''', headers=invalid_headers
    )
    assert invalid_auth_response.status_code == 401, invalid_auth_response.text

@pytest.mark.asyncio
async def test_video_processing_flow(async_client: AsyncClient, current_user_headers: dict):
    '''Test video processing and analysis flow via API (simplified).'''
    
    video_submissions_data = [
        {"exercise_name": "SQUAT_API", "notes": "API flow video 1", "filename": "flow_video1.mp4"},
        {"exercise_name": "DEADLIFT_API", "notes": "API flow video 2", "filename": "flow_video2.mp4"}
    ]
    
    form_check_ids = []

    for sub_data in video_submissions_data:
        dummy_video_content = f'''dummy video for {sub_data['filename']}'''.encode('utf-8')
        files = {"video_upload": (sub_data['filename'], io.BytesIO(dummy_video_content), "video/mp4")}
        payload = {"exercise_name": sub_data["exercise_name"], "notes": sub_data["notes"]}
        
        response = await async_client.post(
            f'''{settings.API_V1_STR}/form-checks/submit''', 
            headers=current_user_headers,
            files=files,
            data=payload
        )
        assert response.status_code == 202, response.text
        form_check_ids.append(response.json()["id"])
    
    for form_check_id in form_check_ids:
        history_response = await async_client.get(
            f'''{settings.API_V1_STR}/form-checks/history''', 
            headers=current_user_headers
        )
        assert history_response.status_code == 200, history_response.text
        history_items = history_response.json()
        assert any(item["id"] == form_check_id for item in history_items)

@pytest.mark.asyncio
async def test_user_settings_flow(async_client: AsyncClient, current_user_headers: dict):
    '''Test user settings and preferences flow via API.'''
    
    settings_payload = {
        "notification_preferences": {"email": True, "push": False},
        "exercise_preferences": ["SQUAT", "DEADLIFT"], 
        "difficulty_level": "INTERMEDIATE" 
    }
    # This test assumes that PUT /api/v1/users/me can update these settings fields.
    # The actual UserUpdate schema might be different.
    update_settings_response = await async_client.put(
        f'''{settings.API_V1_STR}/users/me''', 
        headers=current_user_headers,
        json=settings_payload 
    )
    assert update_settings_response.status_code == 200, update_settings_response.text 

    get_user_response = await async_client.get(
        f'''{settings.API_V1_STR}/users/me''', headers=current_user_headers
    )
    assert get_user_response.status_code == 200, get_user_response.text
    user_details = get_user_response.json()
    # Add assertions here based on how settings are reflected in the User model/schema
    # For example, if 'preferences' is a dict in the user model:
    # assert user_details.get("preferences", {}).get("difficulty_level") == "INTERMEDIATE"

    profile_payload = {"full_name": "Updated Flow User Name"}
    update_profile_response = await async_client.put(
        f'''{settings.API_V1_STR}/users/me''', 
        headers=current_user_headers,
        json=profile_payload
    )
    assert update_profile_response.status_code == 200, update_profile_response.text
    updated_profile_data = update_profile_response.json()
    assert updated_profile_data["full_name"] == profile_payload["full_name"] 