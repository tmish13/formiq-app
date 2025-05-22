"""
User test utilities.
"""
import random
import string
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.db.crud import create_user
from app.models.user import User


def random_lower_string(length: int = 32) -> str:
    """Generate a random lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_email() -> str:
    """Generate a random email."""
    return f"{random_lower_string(8)}@{random_lower_string(6)}.com"


def create_random_user(db: Session, override_params: Optional[Dict[str, Any]] = None) -> User:
    """
    Create a random user and save to database.
    
    Args:
        db: Database session
        override_params: Optional parameters to override defaults
    
    Returns:
        User: The created user object
    """
    params = {
        "email": random_email(),
        "password": random_lower_string(),
        "full_name": random_lower_string(),
        "is_verified": False,
        "is_active": True,
        "is_superuser": False,
    }
    
    if override_params:
        params.update(override_params)
    
    # Hash the password
    hashed_password = get_password_hash(params["password"])
    
    # Create user
    db_user = create_user(
        db=db,
        email=params["email"],
        hashed_password=hashed_password,
        full_name=params["full_name"],
        is_verified=params["is_verified"],
        is_active=params["is_active"],
        is_superuser=params["is_superuser"],
    )
    
    return db_user