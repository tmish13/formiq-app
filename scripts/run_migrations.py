import os
import sys
from alembic.config import Config
from alembic import command

def run_migrations():
    """Run database migrations."""
    # Get the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # Add the project root to the Python path
    sys.path.insert(0, project_root)
    
    # Create Alembic configuration
    alembic_cfg = Config(os.path.join(project_root, "alembic.ini"))
    
    # Run the migration
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    run_migrations() 