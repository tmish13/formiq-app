from datetime import datetime
from typing import Any, Dict, Optional
from jose import jwt, JWTError
from redis import Redis
from app.core.config import settings
from app.core.logging import get_logger

# --- Token Decoding Helper ---
def _decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger = get_logger(__name__)
        logger.warning(f"JWT decoding error: {e}", exc_info=True)
        return None

# --- Token Verification & Payload Retrieval ---
def verify_token_payload(
    token: str,
    redis_client: Redis,
    expected_token_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    from app.core.security import is_token_blacklisted  # Avoid circular import
    logger = get_logger(__name__)
    if is_token_blacklisted(token, redis_client):
        logger.debug(f"Token is blacklisted: {token[:20]}...")
        return None
    payload = _decode_jwt_payload(token)
    if not payload:
        return None
    if expected_token_type and payload.get("type") != expected_token_type:
        logger.debug(f"Token type mismatch. Expected '{expected_token_type}', got '{payload.get('type')}'")
        return None
    return payload 