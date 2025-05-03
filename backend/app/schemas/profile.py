"""Profile and settings schemas for validation."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, EmailStr, constr, ConfigDict
from datetime import datetime

class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[constr(min_length=2, max_length=100)] = Field(None, description="User's full name")
    username: Optional[constr(min_length=3, max_length=50)] = Field(None, description="Username")
    email: Optional[EmailStr] = Field(None, description="Email address")
    bio: Optional[constr(max_length=500)] = Field(None, description="User biography")
    avatar_url: Optional[str] = Field(None, description="URL to user's avatar image")
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """
        Validate username format.
        
        Args:
            v: The username value
            
        Returns:
            The validated username
        """
        if v is not None:
            if not v.isalnum() and not any(c in v for c in "_-"):
                raise ValueError("Username must contain only alphanumeric characters, underscores, or hyphens")
        return v

class UserSettings(BaseModel):
    """Schema for user settings."""
    notifications: Dict[str, bool] = Field(
        default_factory=lambda: {
            "email_updates": True,
            "exercise_reminders": True,
            "form_check_results": True,
            "achievement_alerts": True
        },
        description="Notification preferences"
    )
    privacy: Dict[str, bool] = Field(
        default_factory=lambda: {
            "profile_public": True,
            "show_progress": True,
            "share_achievements": True
        },
        description="Privacy settings"
    )
    theme: str = Field("light", description="UI theme preference")
    language: str = Field("en", description="Language preference")
    exercise_preferences: Dict[str, Any] = Field(
        default_factory=lambda: {
            "preferred_exercises": [],
            "difficulty_level": "intermediate",
            "workout_duration": 60,
            "equipment_available": []
        },
        description="Exercise and workout preferences"
    )
    
    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v):
        """
        Validate theme setting.
        
        Args:
            v: The theme value
            
        Returns:
            The validated theme
        """
        allowed_themes = ["light", "dark", "system"]
        if v not in allowed_themes:
            raise ValueError(f"Theme must be one of: {', '.join(allowed_themes)}")
        return v
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """
        Validate language setting.
        
        Args:
            v: The language value
            
        Returns:
            The validated language
        """
        allowed_languages = ["en", "es", "fr", "de", "it", "pt", "ru", "zh"]
        if v not in allowed_languages:
            raise ValueError(f"Language must be one of: {', '.join(allowed_languages)}")
        return v
    
    @field_validator("exercise_preferences")
    @classmethod
    def validate_exercise_preferences(cls, v):
        """
        Validate exercise preferences.
        
        Args:
            v: The exercise preferences dict
            
        Returns:
            The validated exercise preferences
        """
        allowed_difficulties = ["beginner", "intermediate", "advanced", "expert"]
        if v.get("difficulty_level") not in allowed_difficulties:
            raise ValueError(f"Difficulty level must be one of: {', '.join(allowed_difficulties)}")
        
        duration = v.get("workout_duration", 0)
        if not isinstance(duration, (int, float)) or duration < 0 or duration > 240:
            raise ValueError("Workout duration must be between 0 and 240 minutes")
        
        return v

class ProfileResponse(BaseModel):
    """Schema for profile responses."""
    id: str
    full_name: str
    username: str
    email: EmailStr
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    settings: UserSettings
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True) 