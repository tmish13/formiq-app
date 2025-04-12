"""Unit tests for the auth service."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from app.services.auth import AuthService
from app.models.user import User
from app.core.exceptions import AuthenticationException, ValidationException
from app.schemas.token import Token
from app.services.user_service import UserService
from app.services.session_service import SessionService

@pytest.fixture
def mock_db():
    return Mock(spec=Session)

@pytest.fixture
def mock_user_service():
    return Mock(spec=UserService)

@pytest.fixture
def mock_session_service():
    return Mock(spec=SessionService)

@pytest.fixture
def auth_service(mock_db, mock_user_service, mock_session_service):
    return AuthService(mock_db, mock_user_service, mock_session_service)

@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    user.is_active = True
    user.verify_password.return_value = True
    mock_user_service.get_by_email.return_value = user

    # Execute
    result_user, error = await auth_service.authenticate_user("test@example.com", "password123")

    # Assert
    assert result_user == user
    assert error is None
    mock_user_service.get_by_email.assert_called_once_with("test@example.com")
    user.verify_password.assert_called_once_with("password123")

@pytest.mark.asyncio
async def test_authenticate_user_not_found(auth_service, mock_user_service):
    # Setup
    mock_user_service.get_by_email.return_value = None

    # Execute
    result_user, error = await auth_service.authenticate_user("test@example.com", "password123")

    # Assert
    assert result_user is None
    assert error == "Incorrect email or password"
    mock_user_service.get_by_email.assert_called_once_with("test@example.com")

@pytest.mark.asyncio
async def test_authenticate_user_inactive(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    user.is_active = False
    mock_user_service.get_by_email.return_value = user

    # Execute
    result_user, error = await auth_service.authenticate_user("test@example.com", "password123")

    # Assert
    assert result_user is None
    assert error == "User account is inactive"
    mock_user_service.get_by_email.assert_called_once_with("test@example.com")

@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    user.is_active = True
    user.verify_password.return_value = False
    mock_user_service.get_by_email.return_value = user

    # Execute
    result_user, error = await auth_service.authenticate_user("test@example.com", "wrongpassword")

    # Assert
    assert result_user is None
    assert error == "Incorrect email or password"
    mock_user_service.get_by_email.assert_called_once_with("test@example.com")
    user.verify_password.assert_called_once_with("wrongpassword")

@pytest.mark.asyncio
async def test_create_tokens_success(auth_service, mock_session_service):
    # Setup
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    session = Mock()
    session.id = "session123"
    mock_session_service.create_session.return_value = session

    with patch("app.services.auth.create_access_token") as mock_create_access_token, \
         patch("app.services.auth.create_refresh_token") as mock_create_refresh_token:
        mock_create_access_token.return_value = "access_token123"
        mock_create_refresh_token.return_value = "refresh_token123"

        # Execute
        result = await auth_service.create_tokens(user)

        # Assert
        assert isinstance(result, Token)
        assert result.access_token == "access_token123"
        assert result.refresh_token == "refresh_token123"
        assert result.token_type == "bearer"
        assert result.session_id == "session123"
        mock_session_service.create_session.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_refresh_access_token_success(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    user.is_active = True
    user.email = "test@example.com"
    mock_user_service.get_by_email.return_value = user

    with patch("app.services.auth.verify_refresh_token") as mock_verify_token, \
         patch("app.services.auth.create_access_token") as mock_create_access_token, \
         patch("app.services.auth.create_refresh_token") as mock_create_refresh_token:
        mock_verify_token.return_value = {"sub": "test@example.com"}
        mock_create_access_token.return_value = "new_access_token123"
        mock_create_refresh_token.return_value = "new_refresh_token123"

        # Execute
        result = await auth_service.refresh_access_token("valid_refresh_token")

        # Assert
        assert isinstance(result, Token)
        assert result.access_token == "new_access_token123"
        assert result.refresh_token == "new_refresh_token123"
        mock_verify_token.assert_called_once_with("valid_refresh_token")
        mock_user_service.get_by_email.assert_called_once_with("test@example.com")

@pytest.mark.asyncio
async def test_refresh_access_token_invalid(auth_service):
    with patch("app.services.auth.verify_refresh_token") as mock_verify_token:
        mock_verify_token.side_effect = Exception("Invalid token")

        # Execute and Assert
        with pytest.raises(AuthenticationException) as exc_info:
            await auth_service.refresh_access_token("invalid_refresh_token")
        assert str(exc_info.value) == "Invalid refresh token"

@pytest.mark.asyncio
async def test_reset_password_success(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    mock_user_service.get_by_email.return_value = user

    with patch("app.services.auth.create_password_reset_token") as mock_create_token:
        mock_create_token.return_value = "reset_token123"

        # Execute
        await auth_service.reset_password("test@example.com")

        # Assert
        mock_user_service.get_by_email.assert_called_once_with("test@example.com")
        mock_user_service.send_password_reset_email.assert_called_once_with(user, "reset_token123")

@pytest.mark.asyncio
async def test_confirm_password_reset_success(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    mock_user_service.get_by_email.return_value = user

    with patch("app.services.auth.verify_password_reset_token") as mock_verify_token:
        mock_verify_token.return_value = "test@example.com"

        # Execute
        await auth_service.confirm_password_reset("valid_token", "new_password123")

        # Assert
        mock_verify_token.assert_called_once_with("valid_token")
        mock_user_service.get_by_email.assert_called_once_with("test@example.com")
        mock_user_service.update_password.assert_called_once_with(user, "new_password123")

@pytest.mark.asyncio
async def test_confirm_password_reset_invalid_token(auth_service):
    with patch("app.services.auth.verify_password_reset_token") as mock_verify_token:
        mock_verify_token.side_effect = Exception("Invalid token")

        # Execute and Assert
        with pytest.raises(ValidationException) as exc_info:
            await auth_service.confirm_password_reset("invalid_token", "new_password123")
        assert str(exc_info.value) == "Invalid or expired reset token"

@pytest.mark.asyncio
async def test_verify_email_success(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    user.is_verified = False
    mock_user_service.get_by_email.return_value = user

    with patch("app.services.auth.verify_password_reset_token") as mock_verify_token:
        mock_verify_token.return_value = "test@example.com"

        # Execute
        await auth_service.verify_email("valid_token")

        # Assert
        mock_verify_token.assert_called_once_with("valid_token")
        mock_user_service.get_by_email.assert_called_once_with("test@example.com")
        mock_user_service.verify_email.assert_called_once_with(user)

@pytest.mark.asyncio
async def test_verify_email_already_verified(auth_service, mock_user_service):
    # Setup
    user = Mock(spec=User)
    user.is_verified = True
    mock_user_service.get_by_email.return_value = user

    with patch("app.services.auth.verify_password_reset_token") as mock_verify_token:
        mock_verify_token.return_value = "test@example.com"

        # Execute and Assert
        with pytest.raises(ValidationException) as exc_info:
            await auth_service.verify_email("valid_token")
        assert str(exc_info.value) == "Email already verified"

@pytest.mark.asyncio
async def test_logout_success(auth_service, mock_session_service):
    # Execute
    await auth_service.logout("session123")

    # Assert
    mock_session_service.invalidate_session.assert_called_once_with("session123")

@pytest.mark.asyncio
async def test_logout_all_success(auth_service, mock_session_service):
    # Execute
    await auth_service.logout_all(1)

    # Assert
    mock_session_service.invalidate_all_sessions.assert_called_once_with(1) 