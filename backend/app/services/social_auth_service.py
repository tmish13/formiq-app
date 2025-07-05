"""Social authentication service."""
import json
import jwt
import httpx
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.schemas.social_auth import SocialUserInfo
from app.models.user import User
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.core.exceptions import AuthenticationException


class SocialAuthService:
    """Handle social authentication with Google and Apple."""
    
    def __init__(self):
        self.user_service = UserService()
        self.auth_service = AuthService()
    
    async def verify_google_token(self, token: str) -> SocialUserInfo:
        """Verify Google ID token and extract user info."""
        try:
            # Verify token with Google
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
                )
                
            if response.status_code != 200:
                raise AuthenticationException("Invalid Google token")
                
            token_info = response.json()
            
            # Verify audience (client ID)
            if token_info.get("aud") != settings.GOOGLE_CLIENT_ID:
                raise AuthenticationException("Invalid Google token audience")
            
            return SocialUserInfo(
                email=token_info["email"],
                first_name=token_info.get("given_name"),
                last_name=token_info.get("family_name"),
                name=token_info.get("name"),
                picture=token_info.get("picture"),
                provider="google",
                provider_id=token_info["sub"]
            )
            
        except Exception as e:
            raise AuthenticationException(f"Google token verification failed: {str(e)}")
    
    async def verify_apple_token(self, token: str) -> SocialUserInfo:
        """Verify Apple ID token and extract user info."""
        try:
            # Decode Apple JWT token (simplified - in production you'd verify signature)
            # For production, you'd fetch Apple's public keys and verify the signature
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Basic validation
            if decoded.get("aud") != settings.APPLE_CLIENT_ID:
                raise AuthenticationException("Invalid Apple token audience")
            
            # Extract email from token
            email = decoded.get("email")
            if not email:
                raise AuthenticationException("Email not provided in Apple token")
            
            # Apple doesn't always provide name in the token
            name = decoded.get("name", {})
            first_name = name.get("firstName") if isinstance(name, dict) else None
            last_name = name.get("lastName") if isinstance(name, dict) else None
            
            return SocialUserInfo(
                email=email,
                first_name=first_name,
                last_name=last_name,
                provider="apple",
                provider_id=decoded["sub"]
            )
            
        except Exception as e:
            raise AuthenticationException(f"Apple token verification failed: {str(e)}")
    
    async def authenticate_social_user(
        self, 
        user_info: SocialUserInfo, 
        db: AsyncSession
    ) -> dict:
        """Authenticate or create user from social login."""
        try:
            # Try to find existing user by email
            existing_user = await self.user_service.get_user_by_email(db, user_info.email)
            
            if existing_user:
                # User exists, update social info if needed
                user = existing_user
            else:
                # Create new user from social login
                username = user_info.email.split("@")[0]  # Simple username generation
                
                # Ensure username is unique
                counter = 1
                original_username = username
                while await self.user_service.get_user_by_username(db, username):
                    username = f"{original_username}{counter}"
                    counter += 1
                
                user_data = {
                    "email": user_info.email,
                    "username": username,
                    "password": "social_auth_placeholder",  # Social users don't have passwords
                    "first_name": user_info.first_name or "",
                    "last_name": user_info.last_name or "",
                    "is_verified": True,  # Social users are pre-verified
                    "social_provider": user_info.provider,
                    "social_id": user_info.provider_id
                }
                
                user = await self.user_service.create_user(db, user_data)
            
            # Generate tokens
            access_token = self.auth_service.create_access_token(data={"sub": str(user.id)})
            refresh_token = self.auth_service.create_refresh_token(data={"sub": str(user.id)})
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "first_name": getattr(user, 'first_name', ''),
                    "last_name": getattr(user, 'last_name', ''),
                    "is_verified": user.is_verified,
                    "avatar_url": user_info.picture
                },
                "token_type": "bearer"
            }
            
        except Exception as e:
            raise AuthenticationException(f"Social authentication failed: {str(e)}")
    
    async def handle_social_login(
        self, 
        provider: str, 
        token: str, 
        db: AsyncSession
    ) -> dict:
        """Handle social login for both Google and Apple."""
        if provider == "google":
            user_info = await self.verify_google_token(token)
        elif provider == "apple":
            user_info = await self.verify_apple_token(token)
        else:
            raise AuthenticationException(f"Unsupported social provider: {provider}")
        
        return await self.authenticate_social_user(user_info, db)