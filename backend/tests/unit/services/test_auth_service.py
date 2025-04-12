"""Tests for authentication service."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from app.services.auth import AuthService
from app.core.security import create_access_token, verify_password
from tests.base import BaseTest

class TestAuthService(BaseTest):
    """Test suite for AuthService."""
    
    @pytest.fixture
    def auth_service(self):
        """Create an AuthService instance."""
        return AuthService()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service):
        """Test successful user authentication."""
        # Create test user
        user = await self.create_test_user(
            email="test@example.com",
            password="testpass123"
        )
        
        # Authenticate user
        authenticated_user = await auth_service.authenticate_user(
            email="test@example.com",
            password="testpass123"
        )
        
        # Verify results
        assert authenticated_user is not None
        assert authenticated_user["email"] == user["email"]
        assert authenticated_user["id"] == user["id"]
    
    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_service):
        """Test authentication with invalid credentials."""
        # Create test user
        await self.create_test_user(
            email="test@example.com",
            password="testpass123"
        )
        
        # Try to authenticate with wrong password
        authenticated_user = await auth_service.authenticate_user(
            email="test@example.com",
            password="wrongpassword"
        )
        
        # Verify results
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service):
        """Test authentication with non-existent user."""
        # Try to authenticate with non-existent email
        authenticated_user = await auth_service.authenticate_user(
            email="nonexistent@example.com",
            password="testpass123"
        )
        
        # Verify results
        assert authenticated_user is None
    
    @pytest.mark.asyncio
    async def test_create_access_token(self, auth_service):
        """Test creating access token."""
        # Create test user
        user = await self.create_test_user()
        
        # Create access token
        token = await auth_service.create_access_token(user["id"])
        
        # Verify token
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    @pytest.mark.asyncio
    async def test_verify_token_success(self, auth_service):
        """Test successful token verification."""
        # Create test user
        user = await self.create_test_user()
        
        # Create access token
        token = await auth_service.create_access_token(user["id"])
        
        # Verify token
        verified_user = await auth_service.verify_token(token)
        
        # Verify results
        assert verified_user is not None
        assert verified_user["id"] == user["id"]
    
    @pytest.mark.asyncio
    async def test_verify_token_invalid(self, auth_service):
        """Test verification with invalid token."""
        # Try to verify invalid token
        with pytest.raises(Exception):
            await auth_service.verify_token("invalid_token")
    
    @pytest.mark.asyncio
    async def test_verify_token_expired(self, auth_service):
        """Test verification with expired token."""
        # Create test user
        user = await self.create_test_user()
        
        # Create expired token
        with patch("app.core.security.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() - timedelta(days=1)
            token = create_access_token(user["id"])
        
        # Try to verify expired token
        with pytest.raises(Exception):
            await auth_service.verify_token(token)
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service):
        """Test successful user registration."""
        # Register new user
        new_user = await auth_service.register_user(
            email="newuser@example.com",
            password="newpass123",
            full_name="New User"
        )
        
        # Verify results
        assert new_user is not None
        assert new_user["email"] == "newuser@example.com"
        assert new_user["full_name"] == "New User"
        assert "id" in new_user
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, auth_service):
        """Test registration with duplicate email."""
        # Create existing user
        await self.create_test_user(email="existing@example.com")
        
        # Try to register with same email
        with pytest.raises(Exception, match="Email already registered"):
            await auth_service.register_user(
                email="existing@example.com",
                password="newpass123",
                full_name="New User"
            )
    
    @pytest.mark.asyncio
    async def test_reset_password_success(self, auth_service):
        """Test successful password reset."""
        # Create test user
        user = await self.create_test_user()
        
        # Reset password
        await auth_service.reset_password(
            user_id=user["id"],
            new_password="newpass123"
        )
        
        # Verify password was changed
        updated_user = await self.db.execute(
            "SELECT * FROM users WHERE id = :id",
            {"id": user["id"]}
        )
        updated_user = updated_user.first()
        
        assert verify_password("newpass123", updated_user["hashed_password"])
    
    @pytest.mark.asyncio
    async def test_reset_password_user_not_found(self, auth_service):
        """Test password reset for non-existent user."""
        # Try to reset password for non-existent user
        with pytest.raises(Exception, match="User not found"):
            await auth_service.reset_password(
                user_id=999,
                new_password="newpass123"
            ) 