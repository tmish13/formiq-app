# backend/tests/integration/services/test_auth_service_integration.py

import pytest
pytestmark = pytest.mark.integration
from sqlalchemy.orm import Session # Assuming Session is used by db_session fixture
from fastapi import HTTPException # For the rate limiting test
from datetime import datetime, timedelta # Added for subscription test

from app.services.auth_service import AuthService
from app.services.user_service import UserService # AuthService depends on UserService
from app.schemas.user import UserCreate, UserUpdate # UserUpdate might be needed by user_service
from app.core.exceptions import AuthenticationError, AuthorizationError # Added AuthorizationError
from app.core.config import settings # For MAX_LOGIN_ATTEMPTS
from app.models.user import User as UserModel # If needed for assertions
from app.models.enums import SubscriptionTier # Added for subscription test
from app.core.security import create_access_token as app_create_access_token # Alias to avoid conflict

# Assuming a db_session fixture is available (e.g., from conftest.py or defined here)
# This fixture should provide a real database session for integration testing.
@pytest.fixture
def db_session_for_auth_integration(tmp_path) -> Session:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.base import Base 

    db_file = tmp_path / "test_auth_integration.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)

@pytest.fixture
def user_service_for_auth_integ(db_session_for_auth_integration: Session) -> UserService: # Renamed fixture
    return UserService(db_session_for_auth_integration)

@pytest.fixture
def auth_service_for_integ(db_session_for_auth_integration: Session) -> AuthService: # Renamed fixture
    # Assuming AuthService takes db session. If it depends on UserService, it should be passed.
    # The original tests from test_auth.py seem to call AuthService.static_method(db, ...)
    # This suggests AuthService methods might be static or class methods taking db as first arg.
    # Or, an instance is created: auth_service = AuthService(db)
    # For now, instantiate it, assuming it takes a db session.
    return AuthService(db=db_session_for_auth_integration)

# Fixture from test_auth.py, adapted for async and integration context
@pytest.fixture
async def integ_test_user(user_service_for_auth_integ: UserService) -> UserModel:
    user_data = UserCreate(
        email="integ_user@example.com",
        username="integ_test_user",
        password="StrongPassword123!",
        full_name="Integration Test User",
        subscription_tier=SubscriptionTier.FREE, # Ensure UserModel has this field
        is_email_verified=True # Ensure UserModel has this field
    )
    user = await user_service_for_auth_integ.create_user(user_data)
    return user

@pytest.mark.asyncio
async def test_user_authentication_integration(auth_service_for_integ: AuthService, user_service_for_auth_integ: UserService, integ_test_user: UserModel):
    """Test user authentication flow (integration)."""
    # integ_test_user is already created by fixture with password "StrongPassword123!"
    
    # Test successful authentication
    authenticated_user_model = await auth_service_for_integ.authenticate_user_for_token(
        email=integ_test_user.email,
        password="StrongPassword123!" # Use the correct password
    )
    assert authenticated_user_model is not None
    assert authenticated_user_model.email == integ_test_user.email
    
    # Test failed authentication (wrong password)
    with pytest.raises(AuthenticationError): # Expecting AuthenticationError from service
        await auth_service_for_integ.authenticate_user_for_token(
            email=integ_test_user.email,
            password="WrongPassword!"
        )
    
    # Test failed authentication (non-existent user)
    with pytest.raises(AuthenticationError): # Expecting AuthenticationError from service
        await auth_service_for_integ.authenticate_user_for_token(
            email="nonexistent@example.com",
            password="anypassword"
        )

@pytest.mark.asyncio
async def test_token_validation_integration(auth_service_for_integ: AuthService, user_service_for_auth_integ: UserService):
    """Test token validation and refresh (integration)."""
    user_data = UserCreate(
        email="token_integ@example.com",
        password="StrongPass123!",
        full_name="Token Integ User",
        username="tokeninteguser"
    )
    user = await user_service_for_auth_integ.create_user(user_data)
    
    # Get tokens
    tokens = await auth_service_for_integ.authenticate_user(
        email="token_integ@example.com",
        password="StrongPass123!"
    )
    
    # Validate access token (validate_token might return user_id or user object depending on impl)
    # The original test implies validate_token returns user_id
    # Assuming validate_token is a method of AuthService
    # If it decodes and verifies, it might take the token string.
    # The method signature might be different in the actual AuthService.
    # For this example, let's assume `validate_token` is now part of `auth_service_integration`
    # and it takes a token string and returns the user identifier (e.g. email or ID).
    # This part of the test needs to align with the actual AuthService.validate_token method.
    # For now, let's assume it checks the token and might not return user_id directly, 
    # but rather raise an exception if invalid.
    # A more common pattern is `get_current_user` that uses the token.
    # If `validate_token` returns user_id:
    # validated_user_identifier = await auth_service_integration.validate_token(tokens["access_token"])
    # assert str(validated_user_identifier) == str(user.id) # or user.email depending on what sub claim is

    # Let's simulate a protected action that would internally validate the token
    # This test might be better if it tries to use the token with an endpoint/service method that requires auth.
    # For now, if auth_service has a direct validate_token method:
    try:
        # Assume validate_token might return the subject of the token or raise error
        payload = await auth_service_for_integ.decode_token(tokens["access_token"]) 
        assert payload["sub"] == user.email # Assuming email is in sub
    except Exception as e:
        pytest.fail(f"Token validation failed: {e}")
    
    # Test invalid token
    with pytest.raises(AuthenticationError): # Or specific JWTError
        await auth_service_for_integ.decode_token("invalid_token_string")

@pytest.mark.asyncio
async def test_rate_limiting_integration(auth_service_for_integ: AuthService, user_service_for_auth_integ: UserService):
    """Test rate limiting functionality for login (integration)."""
    # Create a user that doesn't exist or use an email not in DB for failed attempts
    # The original test used "ratelimit@example.com". Ensure this user does not successfully authenticate.
    
    # Test rate limiting for login attempts
    # Ensure settings.MAX_LOGIN_ATTEMPTS is defined and accessible.
    # The AuthService might handle rate limiting internally based on IP or email.
    # This test assumes the service tracks failed attempts for an email.
    max_attempts = settings.MAX_LOGIN_ATTEMPTS if hasattr(settings, 'MAX_LOGIN_ATTEMPTS') else 5

    for i in range(max_attempts):
        with pytest.raises(AuthenticationError): # Expect auth error for wrong password
            print(f"Rate limit test attempt {i+1}")
            await auth_service_for_integ.authenticate_user(
                email="ratelimit_integ@example.com",
                password="WrongPassForEachAttempt"
            )
    
    # Next attempt should raise rate limit error (HTTPException 429)
    with pytest.raises(HTTPException) as exc_info:
        await auth_service_for_integ.authenticate_user(
            email="ratelimit_integ@example.com",
            password="AnotherWrongPass"
        )
    assert exc_info.value.status_code == 429 

# Tests merged from test_auth.py (AuthService direct method calls)
@pytest.mark.asyncio
async def test_get_current_user_integration(auth_service_for_integ: AuthService, integ_test_user: UserModel):
    """Test AuthService.get_current_user method (integration)."""
    token = app_create_access_token(subject=integ_test_user.email) # Use app's token creation
    
    current_user = await auth_service_for_integ.get_current_active_user(token=token)
    assert current_user is not None
    assert current_user.email == integ_test_user.email

    # Test with invalid token
    with pytest.raises(HTTPException) as exc_info: # Assuming get_current_active_user raises HTTPException for bad token
        await auth_service_for_integ.get_current_active_user(token="invalid.jwt.token")
    assert exc_info.value.status_code == 401 # Unauthorized

    # Test with token for a non-existent user ID / subject (if get_user_by_subject is part of it)
    # This depends on how get_current_active_user fetches the user.
    # If it only decodes and trusts sub, this test case might need more.
    # If it fetches user from DB based on sub:
    non_existent_user_token = app_create_access_token(subject="nonexistent@example.com")
    with pytest.raises(HTTPException) as exc_info: # Expect 404 or 401 depending on implementation
        await auth_service_for_integ.get_current_active_user(token=non_existent_user_token)
    # Common to return 401 if user from token sub not found, to not reveal existence.
    assert exc_info.value.status_code == 401 # Or 404 if service raises NotFoundException converted to HTTP 404

@pytest.mark.asyncio
async def test_get_current_user_token_without_sub_integration(auth_service_for_integ: AuthService):
    """Test get_current_user with token missing subject (integration)."""
    # Create a token that intentionally lacks a subject or has an invalid one
    # This requires knowing how app_create_access_token handles None or empty subject
    # For now, assume it might raise an error or create a token that verify_token would reject.
    # A more direct way: craft a token with jose.jwt that has no 'sub'
    from jose import jwt as jose_jwt
    from app.core.config import settings as app_settings



    no_sub_payload = {"exp": datetime.utcnow() + timedelta(minutes=5), "iat": datetime.utcnow()}
    no_sub_token = jose_jwt.encode(no_sub_payload, app_settings.JWT_SECRET_KEY, algorithm=app_settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service_for_integ.get_current_active_user(token=no_sub_token)
    assert exc_info.value.status_code == 401 # Expect 401 due to missing subject claim

@pytest.mark.asyncio
async def test_subscription_validation_integration(auth_service_for_integ: AuthService, user_service_for_auth_integ: UserService, integ_test_user: UserModel):
    """Test subscription validation in AuthService (integration)."""
    # Update user to have expired subscription
    # integ_test_user is managed by a session, need to update via service or re-fetch for current state
    user_update_data = UserUpdate(subscription_end_date=(datetime.utcnow() - timedelta(days=1)))
    await user_service_for_auth_integ.update_user(user_id=integ_test_user.id, user_in=user_update_data)
    
    token = app_create_access_token(subject=integ_test_user.email)
    
    # Test access with expired subscription (assuming get_current_user checks this if required_subscription is passed)
    # This requires get_current_active_user to have a `required_subscription_tier` param or similar
    # The original test_auth.py implies AuthService.get_current_user(db, token, required_subscription="pro")
    # Let's assume the method is now: auth_service.get_current_active_user(token, required_tier)
    with pytest.raises(AuthorizationError) as exc_info: # Or HTTPException(403)
        await auth_service_for_integ.get_current_active_user(token=token, required_tier=SubscriptionTier.PRO)
    # Check specific message if AuthorizationError has one, or status_code if HTTPException
    # assert "Subscription required" in str(exc_info.value) # Example

@pytest.mark.asyncio
async def test_email_verification_check_integration(auth_service_for_integ: AuthService, user_service_for_auth_integ: UserService, integ_test_user: UserModel):
    """Test email verification check in AuthService (integration)."""
    # Update user to have unverified email
    user_update_data = UserUpdate(is_email_verified=False)
    await user_service_for_auth_integ.update_user(user_id=integ_test_user.id, user_in=user_update_data)
    
    token = app_create_access_token(subject=integ_test_user.email)
    
    # Test access with unverified email (assuming get_current_user checks this if require_verification is True)
    # Original: AuthService.get_current_user(db, token, require_verification=True)
    # Assume: auth_service.get_current_active_user(token, require_email_verified=True)
    with pytest.raises(AuthorizationError) as exc_info: # Or HTTPException(403)
        await auth_service_for_integ.get_current_active_user(token=token, require_email_verified=True)
    # assert "Email not verified" in str(exc_info.value) # Example 