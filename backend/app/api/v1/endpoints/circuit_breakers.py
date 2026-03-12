"""
Circuit Breaker Monitoring API Endpoints

Provides endpoints to monitor circuit breaker status and statistics
for external service resilience monitoring.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.core.circuit_breaker import circuit_registry
from app.core.deps import get_current_active_superuser
from app.models.user import User

router = APIRouter()

@router.get("/stats")
async def get_circuit_breaker_stats() -> Dict[str, Any]:
    """
    Get statistics for all circuit breakers.
    
    Returns circuit breaker states, failure counts, and health status
    for monitoring external service resilience.
    """
    stats = circuit_registry.get_all_stats()
    
    # Add summary information
    summary = {
        "total_breakers": len(stats),
        "open_breakers": len([s for s in stats.values() if s["state"] == "open"]),
        "half_open_breakers": len([s for s in stats.values() if s["state"] == "half_open"]),
        "overall_health": "healthy" if not any(s["state"] == "open" for s in stats.values()) else "degraded"
    }
    
    return {
        "summary": summary,
        "circuit_breakers": stats
    }

@router.post("/reset/{breaker_name}")
async def reset_circuit_breaker(
    breaker_name: str,
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Manually reset a circuit breaker to closed state.
    
    Requires admin privileges. Use with caution - only reset breakers
    when you're confident the underlying service has recovered.
    """
    success = circuit_registry.reset_breaker(breaker_name)
    
    if not success:
        return {
            "success": False,
            "message": f"Circuit breaker '{breaker_name}' not found",
            "available_breakers": list(circuit_registry._breakers.keys())
        }
    
    return {
        "success": True,
        "message": f"Circuit breaker '{breaker_name}' has been reset to closed state",
        "reset_by": current_user.email
    }

@router.get("/health")
async def get_external_services_health() -> Dict[str, Any]:
    """
    Get overall external services health status.
    
    Provides a quick health check for all external services
    based on circuit breaker states.
    """
    stats = circuit_registry.get_all_stats()
    
    services = {}
    for name, breaker_stats in stats.items():
        state = breaker_stats["state"]
        failure_rate = breaker_stats["failure_rate"]
        
        if state == "open":
            status = "unhealthy"
            message = f"Circuit breaker open - service unavailable (retry in {breaker_stats['retry_after']:.0f}s)"
        elif state == "half_open":
            status = "recovering"
            message = "Testing service recovery"
        elif failure_rate > 0.5:  # More than 50% failure rate
            status = "degraded"
            message = f"High failure rate ({failure_rate:.1%})"
        elif failure_rate > 0.1:  # More than 10% failure rate
            status = "warning"
            message = f"Elevated failure rate ({failure_rate:.1%})"
        else:
            status = "healthy"
            message = "Service operating normally"
        
        services[name] = {
            "status": status,
            "message": message,
            "state": state,
            "failure_rate": failure_rate,
            "total_requests": breaker_stats["total_requests"]
        }
    
    overall_status = "healthy"
    if any(s["status"] == "unhealthy" for s in services.values()):
        overall_status = "unhealthy"
    elif any(s["status"] in ["degraded", "recovering"] for s in services.values()):
        overall_status = "degraded"
    elif any(s["status"] == "warning" for s in services.values()):
        overall_status = "warning"
    
    return {
        "overall_status": overall_status,
        "services": services,
        "timestamp": circuit_registry.get_all_stats()
    }