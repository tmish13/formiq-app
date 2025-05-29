"""Base class for SQLAlchemy models."""
# from sqlalchemy.orm import declarative_base # Remove this
from app.core.database import Base # Import the unified Base

# Create Base class for models with modern naming convention
# Base = declarative_base() # Remove this line, Base is now imported 