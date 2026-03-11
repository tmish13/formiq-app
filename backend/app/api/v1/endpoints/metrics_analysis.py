"""API endpoints for metrics analysis and SLA monitoring."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.services.metrics_analysis_service import metrics_analysis_service
from app.api.deps import get_current_active_user
from app.models.user import User

router = APIRouter()


class SuccessRateResponse(BaseModel):
    """Response model for success rate metrics."""
    success_rate: float
    total_requests: int
    successful_requests: int
    failed_requests: int


class SLAComplianceResponse(BaseModel):
    """Response model for SLA compliance check."""
    overall_sla_compliant: bool
    success_rate_compliant: bool
    p95_latency_compliant: bool
    p99_latency_compliant: bool
    current_success_rate: float
    current_p95_latency_ms: float
    current_p99_latency_ms: float
    sla_targets: Dict[str, float]


class PrometheusQueriesResponse(BaseModel):
    """Response model for Prometheus queries."""
    queries: Dict[str, str]


@router.get("/success-rate", response_model=SuccessRateResponse)
async def get_api_success_rate(
    time_window_minutes: int = 5,
    current_user: User = Depends(get_current_active_user)
) -> SuccessRateResponse:
    """
    Get current API success rate metrics.
    
    Args:
        time_window_minutes: Time window for calculation (currently unused, uses cumulative)
        current_user: Authenticated user (admin access recommended)
        
    Returns:
        API success rate metrics
    """
    try:
        metrics = metrics_analysis_service.calculate_api_success_rate(time_window_minutes)
        return SuccessRateResponse(**metrics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating success rate: {e}")


@router.get("/sla-compliance", response_model=SLAComplianceResponse)
async def check_sla_compliance(
    current_user: User = Depends(get_current_active_user)
) -> SLAComplianceResponse:
    """
    Check current SLA compliance status.
    
    Returns:
        SLA compliance metrics including success rate and latency targets
    """
    try:
        compliance = metrics_analysis_service.check_sla_compliance()
        return SLAComplianceResponse(**compliance)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking SLA compliance: {e}")


@router.get("/endpoint-success-rates")
async def get_endpoint_success_rates(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Dict[str, float]]:
    """
    Get success rates broken down by API endpoint.
    
    Returns:
        Dictionary mapping endpoints to their success rate metrics
    """
    try:
        return metrics_analysis_service.get_endpoint_success_rates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating endpoint success rates: {e}")


@router.get("/latency-percentiles")
async def get_latency_percentiles(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, float]:
    """
    Get current latency percentile metrics.
    
    Returns:
        Latency percentiles (p50, p95, p99) in milliseconds
    """
    try:
        return metrics_analysis_service.calculate_latency_percentiles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating latency percentiles: {e}")


@router.get("/prometheus-queries", response_model=PrometheusQueriesResponse)
async def get_prometheus_queries(
    current_user: User = Depends(get_current_active_user)
) -> PrometheusQueriesResponse:
    """
    Get useful Prometheus queries for monitoring API success rates.
    
    Returns:
        Dictionary of Prometheus queries for different metrics
    """
    try:
        queries = metrics_analysis_service.generate_prometheus_queries()
        return PrometheusQueriesResponse(queries=queries)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Prometheus queries: {e}")


@router.get("/health-summary")
async def get_api_health_summary(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Get comprehensive API health summary.
    
    Returns:
        Combined metrics including success rate, latency, and SLA compliance
    """
    try:
        success_rate = metrics_analysis_service.calculate_api_success_rate()
        latency = metrics_analysis_service.calculate_latency_percentiles()
        sla_compliance = metrics_analysis_service.check_sla_compliance()
        endpoint_rates = metrics_analysis_service.get_endpoint_success_rates()
        
        return {
            "timestamp": "2025-12-01T00:00:00Z",  # Would use actual timestamp
            "success_rate": success_rate,
            "latency_percentiles": latency,
            "sla_compliance": sla_compliance,
            "endpoint_breakdown": endpoint_rates,
            "summary": {
                "status": "healthy" if sla_compliance.get('overall_sla_compliant', False) else "degraded",
                "total_endpoints": len(endpoint_rates),
                "healthy_endpoints": sum(1 for ep in endpoint_rates.values() if ep['success_rate'] >= 99.0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating health summary: {e}")