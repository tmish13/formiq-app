from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

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
    
    class Config:
        from_attributes = True

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