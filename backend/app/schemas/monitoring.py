from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

class SystemEventBase(BaseModel):
    event_type: str = Field(..., description="Type of system event (e.g., 'error', 'warning', 'info').")
    message: str = Field(..., description="Detailed message describing the event.")
    source_service: Optional[str] = Field(None, description="The service that generated the event.")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of when the event occurred.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary key-value metadata for the event.")

class SystemEventCreate(SystemEventBase):
    pass

class SystemEvent(SystemEventBase):
    id: UUID = Field(..., description="Unique identifier for the system event.")
    
    model_config = ConfigDict(from_attributes=True)

class ServiceHealth(BaseModel):
    service_name: str = Field(..., description="Name of the service.")
    status: ServiceStatus = Field(..., description="Current health status of the service.")
    details: Optional[str] = Field(None, description="Additional details about the service health.")
    last_checked: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the last health check.")
    dependencies: Optional[List[str]] = Field(None, description="List of services this service depends on.")

class MonitoringDataResponse(BaseModel):
    overall_status: ServiceStatus = Field(..., description="Overall system health status.")
    services: List[ServiceHealth] = Field(..., description="List of individual service health statuses.")
    system_events_summary: Optional[Dict[str, int]] = Field(None, description="Summary of recent system events by type.")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Key performance indicators or other metrics.")

class SystemEventFilter(BaseModel):
    event_type: Optional[str] = Field(None, description="Filter by event type.")
    source_service: Optional[str] = Field(None, description="Filter by source service.")
    start_time: Optional[datetime] = Field(None, description="Filter events after this timestamp.")
    end_time: Optional[datetime] = Field(None, description="Filter events before this timestamp.")
    keyword: Optional[str] = Field(None, description="Search for a keyword in the event message.")


# Cache Monitoring Schemas

class CacheStatsResponse(BaseModel):
    """Response schema for cache statistics."""
    status: str = Field(..., description="Response status")
    data: Dict[str, Any] = Field(..., description="Cache statistics data")
    timestamp: str = Field(..., description="Timestamp of statistics")
    message: str = Field(..., description="Response message")


class CacheHealthResponse(BaseModel):
    """Response schema for cache health check."""
    status: str = Field(..., description="Health status (healthy/unhealthy/degraded)")
    service: str = Field(..., description="Service name")
    details: Dict[str, Any] = Field(..., description="Health check details")
    healthy: bool = Field(..., description="Boolean health indicator")
    message: str = Field(..., description="Health status message")


class CachePerformanceSummaryResponse(BaseModel):
    """Response schema for cache performance summary."""
    status: str = Field(..., description="Response status")
    data: Dict[str, Any] = Field(..., description="Performance summary data")
    period_hours: int = Field(..., description="Time period analyzed in hours")
    message: str = Field(..., description="Summary message")


class CacheOptimizationRecommendationResponse(BaseModel):
    """Response schema for cache optimization recommendations."""
    category: str = Field(..., description="Recommendation category")
    priority: str = Field(..., description="Priority level (high/medium/low)")
    title: str = Field(..., description="Recommendation title")
    description: str = Field(..., description="Detailed description")
    action: str = Field(..., description="Recommended action")
    estimated_impact: str = Field(..., description="Expected impact")


class CacheEfficiencyScoreResponse(BaseModel):
    """Response schema for cache efficiency scoring."""
    status: str = Field(..., description="Response status")
    overall_score: float = Field(..., description="Overall efficiency score (0-100)")
    grade: str = Field(..., description="Letter grade (A-F)")
    breakdown: Dict[str, float] = Field(..., description="Score breakdown by category")
    current_metrics: Dict[str, Any] = Field(..., description="Current cache metrics")
    message: str = Field(..., description="Efficiency summary message") 