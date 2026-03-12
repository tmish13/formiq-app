"""
Circuit Breaker Implementation for External Services

Provides resilience patterns to handle external service failures gracefully:
- Circuit breaker to prevent cascading failures
- Exponential backoff for retries
- Timeout handling
- Failure tracking and recovery
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Any, Callable, Optional, Dict, TypeVar, Awaitable, Union
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)

# Import monitoring functions - use try/except to avoid circular imports
try:
    from app.core.monitoring import (
        track_circuit_breaker_state,
        track_circuit_breaker_failure, 
        track_circuit_breaker_success,
        track_circuit_breaker_blocked
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    # Create no-op functions if monitoring not available
    def track_circuit_breaker_state(service_name: str, state: str) -> None: pass
    def track_circuit_breaker_failure(service_name: str) -> None: pass
    def track_circuit_breaker_success(service_name: str) -> None: pass
    def track_circuit_breaker_blocked(service_name: str) -> None: pass

T = TypeVar('T')

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, circuit breaker is active
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5           # Number of failures before opening circuit
    recovery_timeout: float = 60.0       # Seconds before trying half-open from open
    success_threshold: int = 3           # Successes needed to close from half-open
    timeout: float = 30.0                # Request timeout in seconds
    max_retries: int = 3                 # Maximum retry attempts
    backoff_multiplier: float = 2.0      # Exponential backoff multiplier
    initial_backoff: float = 1.0         # Initial backoff delay in seconds

@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_state_change: float = field(default_factory=time.time)

class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and blocking requests."""
    
    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker is open for {service_name}. Try again in {retry_after:.1f} seconds")

class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.
    
    Automatically opens when failure threshold is reached, preventing
    further calls to failing services and allowing them time to recover.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
        
        logger.info(f"Initialized circuit breaker '{name}' with config: {self.config}")
    
    async def call(
        self, 
        func: Callable[..., Awaitable[T]], 
        *args, 
        fallback: Optional[Callable[[], T]] = None,
        **kwargs
    ) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Arguments for the function
            fallback: Optional fallback function if circuit is open
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result or fallback result
            
        Raises:
            CircuitBreakerOpen: If circuit is open and no fallback provided
        """
        async with self._lock:
            self.stats.total_requests += 1
            
            # Check if circuit should be opened due to failures
            if self._should_open_circuit():
                self._open_circuit()
            
            # Check if circuit should transition to half-open
            elif self._should_attempt_reset():
                self._half_open_circuit()
            
            # If circuit is open, either use fallback or raise exception
            if self.stats.state == CircuitState.OPEN:
                track_circuit_breaker_blocked(self.name)
                if fallback:
                    logger.warning(f"Circuit breaker '{self.name}' is open, using fallback")
                    return fallback()
                else:
                    retry_after = self._get_retry_after_time()
                    raise CircuitBreakerOpen(self.name, retry_after)
        
        # Execute the function with retry logic
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            try:
                # Apply timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
                
                # Record success
                await self._record_success()
                track_circuit_breaker_success(self.name)
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Circuit breaker '{self.name}' - attempt {attempt + 1} timed out")
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Circuit breaker '{self.name}' - attempt {attempt + 1} failed: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < self.config.max_retries:
                delay = self.config.initial_backoff * (self.config.backoff_multiplier ** attempt)
                logger.debug(f"Circuit breaker '{self.name}' - retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
        
        # All attempts failed
        await self._record_failure()
        track_circuit_breaker_failure(self.name)
        raise last_exception
    
    def call_sync(
        self, 
        func: Callable[..., T], 
        *args, 
        fallback: Optional[Callable[[], T]] = None,
        **kwargs
    ) -> T:
        """
        Execute synchronous function with circuit breaker protection.
        
        This is a convenience method for synchronous functions.
        """
        async def async_wrapper():
            return func(*args, **kwargs)
        
        return asyncio.run(self.call(async_wrapper, fallback=fallback))
    
    async def _record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = time.time()
            
            # If in half-open state, check if we should close the circuit
            if (self.stats.state == CircuitState.HALF_OPEN and 
                self.stats.success_count >= self.config.success_threshold):
                self._close_circuit()
    
    async def _record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = time.time()
            self.stats.success_count = 0  # Reset success count on failure
    
    def _should_open_circuit(self) -> bool:
        """Check if circuit should be opened due to failures."""
        return (self.stats.state == CircuitState.CLOSED and 
                self.stats.failure_count >= self.config.failure_threshold)
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset (move to half-open)."""
        if self.stats.state != CircuitState.OPEN:
            return False
        
        if not self.stats.last_failure_time:
            return False
        
        time_since_failure = time.time() - self.stats.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        self.stats.state = CircuitState.OPEN
        self.stats.last_state_change = time.time()
        track_circuit_breaker_state(self.name, "open")
        logger.warning(f"Circuit breaker '{self.name}' opened due to {self.stats.failure_count} failures")
    
    def _half_open_circuit(self) -> None:
        """Move circuit breaker to half-open state."""
        self.stats.state = CircuitState.HALF_OPEN
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self.stats.last_state_change = time.time()
        track_circuit_breaker_state(self.name, "half_open")
        logger.info(f"Circuit breaker '{self.name}' moved to half-open state")
    
    def _close_circuit(self) -> None:
        """Close the circuit breaker (normal operation)."""
        self.stats.state = CircuitState.CLOSED
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self.stats.last_state_change = time.time()
        track_circuit_breaker_state(self.name, "closed")
        logger.info(f"Circuit breaker '{self.name}' closed - service recovered")
    
    def _get_retry_after_time(self) -> float:
        """Get the time until circuit breaker will try again."""
        if not self.stats.last_failure_time:
            return 0.0
        
        elapsed = time.time() - self.stats.last_failure_time
        return max(0.0, self.config.recovery_timeout - elapsed)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_requests": self.stats.total_requests,
            "total_failures": self.stats.total_failures,
            "total_successes": self.stats.total_successes,
            "failure_rate": (self.stats.total_failures / self.stats.total_requests 
                           if self.stats.total_requests > 0 else 0.0),
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "retry_after": self._get_retry_after_time() if self.stats.state == CircuitState.OPEN else 0.0
        }

class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}
    
    def reset_breaker(self, name: str) -> bool:
        """Reset a specific circuit breaker to closed state."""
        if name in self._breakers:
            breaker = self._breakers[name]
            breaker._close_circuit()
            logger.info(f"Circuit breaker '{name}' manually reset")
            return True
        return False

# Global registry instance
circuit_registry = CircuitBreakerRegistry()

def circuit_breaker(
    name: str, 
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """
    Decorator for applying circuit breaker protection to functions.
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        fallback: Fallback function to call when circuit is open
    """
    def decorator(func: Callable) -> Callable:
        breaker = circuit_registry.get_breaker(name, config)
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.call(func, *args, fallback=fallback, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call_sync(func, *args, fallback=fallback, **kwargs)
            return sync_wrapper
    
    return decorator