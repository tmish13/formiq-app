from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert "api" in data["services"]

def test_health_check_detailed(client: TestClient):
    """Test the detailed health check endpoint."""
    response = client.get("/api/v1/health?detailed=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "services" in data
    
    # Check database details
    assert "database" in data["services"]
    assert "status" in data["services"]["database"]
    assert "latency_ms" in data["services"]["database"]
    assert "connections" in data["services"]["database"]
    
    # Check Redis details
    assert "redis" in data["services"]
    assert "status" in data["services"]["redis"]
    assert "latency_ms" in data["services"]["redis"]
    assert "used_memory" in data["services"]["redis"]
    
    # Check API details
    assert "api" in data["services"]
    assert "status" in data["services"]["api"]
    assert "memory_usage" in data["services"]["api"]
    assert "cpu_percent" in data["services"]["api"] 