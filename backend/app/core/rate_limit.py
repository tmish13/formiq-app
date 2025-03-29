"""Rate limiting functionality for API endpoints."""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
import time
from app.core.logging import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """Rate limiter implementation using in-memory storage."""
    
    def __init__(self, requests_per_minute: int = 60):
        """Initialize rate limiter with requests per minute limit."""
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}  # Store request timestamps per IP
        self._cleanup_interval = 5 * 60  # Cleanup every 5 minutes
        self._last_cleanup = time.time()

    def _cleanup_old_requests(self) -> None:
        """Remove request records older than 1 minute."""
        current_time = time.time()
        if current_time - self._last_cleanup >= self._cleanup_interval:
            cutoff_time = current_time - 60
            for ip in list(self.requests.keys()):
                self.requests[ip] = [ts for ts in self.requests[ip] if ts > cutoff_time]
                if not self.requests[ip]:
                    del self.requests[ip]
            self._last_cleanup = current_time

    def is_rate_limited(self, request: Request) -> Tuple[bool, Optional[float]]:
        """Check if the request should be rate limited.
        
        Returns:
            Tuple[bool, Optional[float]]: (is_limited, retry_after)
            - is_limited: True if request should be rate limited
            - retry_after: Seconds until next request is allowed (if rate limited)
        """
        self._cleanup_old_requests()
        
        client_ip = request.client.host
        current_time = time.time()
        
        # Initialize request list for new IPs
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        
        # Remove requests older than 1 minute
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] 
            if ts > current_time - 60
        ]
        
        # Check if rate limit is exceeded
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            oldest_request = min(self.requests[client_ip])
            retry_after = 60 - (current_time - oldest_request)
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return True, max(0, retry_after)
        
        # Add current request
        self.requests[client_ip].append(current_time)
        return False, None

    def check_rate_limit(self, request: Request) -> None:
        """Check rate limit and raise HTTPException if exceeded."""
        is_limited, retry_after = self.is_rate_limited(request)
        if is_limited:
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(int(retry_after or 60))}
            )

    async def __call__(self, request: Request) -> None:
        """Middleware callable to check rate limit."""
        self.check_rate_limit(request) 