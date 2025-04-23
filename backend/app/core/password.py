"""Password utilities module."""
from passlib.context import CryptContext
from app.core.validators import validate_password as validate_password_strength
import asyncio
import hashlib
import time
from app.core.config import settings
from app.core.logging import logger
import httpx

# Password hashing context with stronger settings
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Increased from default 10
    bcrypt__default_rounds=12
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plain password matches a hashed password.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        bool: True if passwords match, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
        
    Raises:
        ValueError: If password doesn't meet security requirements
    """
    # Validate password strength
    validate_password_strength(password)
    
    # Check if password has been exposed in data breaches (optional/async)
    # This is done asynchronously so we don't block
    asyncio.create_task(is_password_pwned(password))
    
    # Hash and return
    return pwd_context.hash(password)

async def is_password_pwned(password: str) -> bool:
    """
    Check if a password has been exposed in data breaches using the 'Have I Been Pwned' API.
    Uses k-anonymity to protect the password value.
    
    Args:
        password: Password to check
        
    Returns:
        bool: True if password found in breaches, False otherwise
    """
    if not settings.CHECK_PASSWORD_BREACH:
        return False
        
    try:
        # Hash the password with SHA-1
        password_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = password_hash[:5], password_hash[5:]
        
        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                headers={"User-Agent": "FormIQ-Security-Check"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Error checking password breach: Status {response.status_code}")
                return False
                
            # Check if password hash suffix is in results
            result_text = response.text
            lines = result_text.splitlines()
            for line in lines:
                if line.startswith(suffix):
                    # Password found in breach database
                    logger.warning("Password was found in breach database and should not be used")
                    return True
                    
        return False
    except Exception as e:
        logger.error(f"Error checking password breach: {str(e)}")
        return False 