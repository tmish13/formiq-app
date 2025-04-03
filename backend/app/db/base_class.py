"""Base class for SQLAlchemy models."""
from sqlalchemy.orm import declarative_base

# Create Base class for models with modern naming convention
Base = declarative_base() 