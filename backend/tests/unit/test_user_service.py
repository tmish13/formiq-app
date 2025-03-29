import pytest
from unittest.mock import Mock, patch
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.exceptions import NotFoundError, ValidationError

@pytest.fixture
def user_service():
    """Create a UserService instance with mocked repository."""
    mock_repo = Mock()
    return UserService(mock_repo)

@pytest.mark.asyncio
async def test_create_user(user_service):
    """Test user creation."""
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )
    
    mock_user = User(
        id=1,
        email=user_data.email,
        full_name=user_data.full_name
    )
    
    user_service.repository.create.return_value = mock_user
    
    result = await user_service.create(user_data)
    
    assert result.email == user_data.email
    assert result.full_name == user_data.full_name
    user_service.repository.create.assert_called_once()

@pytest.mark.asyncio
async def test_get_user(user_service):
    """Test user retrieval."""
    user_id = 1
    mock_user = User(
        id=user_id,
        email="test@example.com",
        full_name="Test User"
    )
    
    user_service.repository.get.return_value = mock_user
    
    result = await user_service.get(user_id)
    
    assert result.id == user_id
    assert result.email == mock_user.email
    user_service.repository.get.assert_called_once_with(user_id)

@pytest.mark.asyncio
async def test_get_user_not_found(user_service):
    """Test user retrieval when user doesn't exist."""
    user_id = 1
    user_service.repository.get.return_value = None
    
    with pytest.raises(NotFoundError):
        await user_service.get(user_id)

@pytest.mark.asyncio
async def test_update_user(user_service):
    """Test user update."""
    user_id = 1
    update_data = UserUpdate(full_name="Updated Name")
    
    mock_user = User(
        id=user_id,
        email="test@example.com",
        full_name="Updated Name"
    )
    
    user_service.repository.get.return_value = mock_user
    user_service.repository.update.return_value = mock_user
    
    result = await user_service.update(user_id, update_data)
    
    assert result.full_name == update_data.full_name
    user_service.repository.update.assert_called_once()

@pytest.mark.asyncio
async def test_delete_user(user_service):
    """Test user deletion."""
    user_id = 1
    mock_user = User(
        id=user_id,
        email="test@example.com",
        full_name="Test User"
    )
    
    user_service.repository.get.return_value = mock_user
    user_service.repository.delete.return_value = True
    
    result = await user_service.delete(user_id)
    
    assert result is True
    user_service.repository.delete.assert_called_once_with(user_id) 