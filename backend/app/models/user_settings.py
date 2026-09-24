"""User settings model for storing configuration preferences."""
import uuid
from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, SQLiteUUID


class UserSettings(BaseModel):
    """
    User settings model for storing user preferences.
    
    Stores configuration for:
    - Notification preferences
    - Privacy settings
    - UI theme preferences
    - Language settings
    - Exercise preferences
    
    Relationships:
    - One-to-one with User
    
    Attributes:
        user_id (UUID): Foreign key to user
        notifications (JSON): Notification preferences
        privacy (JSON): Privacy settings
        theme (str): UI theme preference (light, dark, system)
        language (str): Language preference
        exercise_preferences (JSON): Exercise and workout preferences
    """
    __tablename__ = "user_settings"

    id = Column(SQLiteUUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(SQLiteUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Settings fields stored as JSON
    notifications = Column(JSON, default=lambda: {
        "email_updates": True,
        "exercise_reminders": True,
        "form_check_results": True,
        "achievement_alerts": True
    })
    
    privacy = Column(JSON, default=lambda: {
        "profile_public": True,
        "show_progress": True,
        "share_achievements": True
    })
    
    theme = Column(String, default="light")
    language = Column(String, default="en")
    
    exercise_preferences = Column(JSON, default=lambda: {
        "preferred_exercises": [],
        "difficulty_level": "intermediate",
        "workout_duration": 60,
        "equipment_available": []
    })

    # Relationship back to user
    user = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings for user {self.user_id}>" 