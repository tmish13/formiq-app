"""Simple test for token blacklist."""
import logging
import uuid
import time
from datetime import datetime, timedelta
from jose import jwt

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Simple token blacklist implementation
class TokenBlacklist:
    """Token blacklist implementation."""
    
    def __init__(self):
        """Initialize token blacklist."""
        self.tokens = set()
        self.expiry = {}
        logger.debug("TokenBlacklist initialized")
    
    def add(self, token: str, expires_in: int = None) -> None:
        """Add a token to the blacklist."""
        logger.debug(f"Adding token to blacklist: {token[:10]}...")
        self.tokens.add(token)
        logger.debug(f"After adding, tokens: {self.tokens}")
        
        # If expires_in is not provided, use a default
        if expires_in is None:
            expires_in = 3600  # 1 hour
        
        # Set expiry
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.expiry[token] = expires_at.timestamp()
        logger.debug(f"Token expiry set to: {expires_at}")
    
    def is_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted."""
        logger.debug(f"Checking if token is blacklisted: {token[:10]}...")
        logger.debug(f"Current tokens: {self.tokens}")
        
        # Clean expired tokens
        now = datetime.utcnow().timestamp()
        expired_tokens = [t for t, exp in self.expiry.items() if exp < now]
        for t in expired_tokens:
            logger.debug(f"Removing expired token: {t[:10]}...")
            self.tokens.discard(t)
            self.expiry.pop(t, None)
        
        # Check if token is in blacklist
        result = token in self.tokens
        logger.debug(f"Token blacklisted: {result}")
        return result

def create_test_token(user_id: str = None) -> str:
    """Create a test JWT token."""
    if user_id is None:
        user_id = str(uuid.uuid4())
    
    # Create a token that expires in 1 day
    expire = datetime.utcnow() + timedelta(days=1)
    to_encode = {"exp": expire, "sub": user_id}
    
    # Use a test secret
    secret = "test_secret_key_for_simple_blacklist_test"
    
    # Create and return token
    return jwt.encode(to_encode, secret, algorithm="HS256")

def run_simple_test():
    """Run a simple test for the token blacklist."""
    logger.debug("Starting simple blacklist test")
    
    # Create a token blacklist
    blacklist = TokenBlacklist()
    
    # Create a test token
    token = create_test_token()
    logger.debug(f"Created test token: {token}")
    
    # Initial state: token should not be blacklisted
    initial_result = blacklist.is_blacklisted(token)
    assert initial_result is False, "Token should not be initially blacklisted"
    logger.debug("Token is not initially blacklisted")
    
    # Add token to blacklist
    blacklist.add(token)
    logger.debug("Token added to blacklist")
    
    # Token should now be blacklisted
    blacklisted_result = blacklist.is_blacklisted(token)
    assert blacklisted_result is True, "Token should be blacklisted after adding"
    logger.debug("Token is now blacklisted")
    
    # Test expiration
    expired_token = create_test_token()
    blacklist.add(expired_token, expires_in=1)  # Expire after 1 second
    logger.debug("Added token with 1 second expiry")
    
    # Initially blacklisted
    assert blacklist.is_blacklisted(expired_token) is True
    logger.debug("Expired token is initially blacklisted")
    
    # Wait for expiration
    logger.debug("Waiting for token to expire...")
    time.sleep(2)
    
    # Should no longer be blacklisted
    expiration_result = blacklist.is_blacklisted(expired_token)
    assert expiration_result is False, "Token should be removed after expiration"
    logger.debug("Expired token is no longer blacklisted")
    
    logger.debug("Simple blacklist test passed")
    return True

if __name__ == "__main__":
    success = run_simple_test()
    if success:
        print("All tests passed!")
    else:
        print("Tests failed!") 