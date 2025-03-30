import os
import sys
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.base import Base

def init_db():
    """Initialize the database."""
    # Get the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # Add the project root to the Python path
    sys.path.insert(0, project_root)
    
    # Create database engine
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db() 