"""Mock lifespan context manager for testing."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

@asynccontextmanager
async def mock_lifespan(app: FastAPI):
    """Mock lifespan for testing that bypasses all initialization."""
    # No startup logic for tests - we handle initialization manually in fixtures
    logging.info("Using mock lifespan context manager for tests")
    yield
    # No shutdown logic for tests - we handle cleanup manually in fixtures
    logging.info("Mock lifespan shutdown") 