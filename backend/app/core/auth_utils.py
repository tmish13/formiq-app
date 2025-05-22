from fastapi import Depends, HTTPException, status
from typing import Dict, Any
from redis import Redis
from app.core.token_utils import verify_token_payload
from app.core.redis_dep import get_redis_client
from app.core.auth_scheme import oauth2_scheme

async def get_current_user_payload(
    token: str = Depends(oauth2_scheme),
    redis_client: Redis = Depends(get_redis_client)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get the payload of the current user's access token.
    Raises HTTPException if token is invalid, expired, or blacklisted.
    """
    payload = verify_token_payload(token, redis_client, expected_token_type="access")
    if not payload:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        raise credentials_exception
    return payload 