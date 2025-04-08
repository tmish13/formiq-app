#!/usr/bin/env python
"""
Reset and regenerate the Alembic migration history.

This script:
1. Deletes all existing migration files
2. Creates a new base migration
3. Stamps the database with the new migration ID
"""
import os
import sys
import glob
import shutil
import subprocess
from pathlib import Path
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path constants
ALEMBIC_VERSIONS_DIR = Path('alembic/versions')
BACKUP_DIR = Path('alembic/versions_backup')

def backup_migrations():
    """Back up existing migration files."""
    logger.info("Backing up existing migration files...")
    
    # Create backup directory if it doesn't exist
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True)
    
    # Create timestamp for the backup folder
    timestamp = uuid.uuid4().hex[:8]
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    backup_path.mkdir(parents=True)
    
    # Copy all migration files to backup directory
    migration_files = list(ALEMBIC_VERSIONS_DIR.glob('*.py'))
    if not migration_files:
        logger.warning("No migration files found to back up")
        return
        
    for file in migration_files:
        if file.name != '__init__.py':
            shutil.copy(file, backup_path)
    
    logger.info(f"Backed up {len(migration_files)-1} migration files to {backup_path}")
    return backup_path

def delete_migrations():
    """Delete all migration files except __init__.py."""
    logger.info("Deleting existing migration files...")
    
    # Delete all .py files in the versions directory except __init__.py
    deleted_count = 0
    for file in ALEMBIC_VERSIONS_DIR.glob('*.py'):
        if file.name != '__init__.py':
            file.unlink()
            deleted_count += 1
    
    logger.info(f"Deleted {deleted_count} migration files")

def create_new_migration():
    """Create a new initial migration file."""
    logger.info("Creating new initial migration...")
    
    try:
        # Run alembic revision command
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "initial_schema"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Created new migration: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create migration: {e.stderr}")
        sys.exit(1)

def stamp_database():
    """Stamp the database with the current migration ID."""
    logger.info("Stamping database with new migration ID...")
    
    try:
        # Get the latest migration ID
        migration_files = sorted(glob.glob(str(ALEMBIC_VERSIONS_DIR / "*.py")))
        if not migration_files or len(migration_files) <= 1:  # Only __init__.py
            logger.error("No migration files found to stamp database with")
            return
            
        # Extract revision ID from filename (assuming format like 1a2b3c4d_xyz.py)
        latest_file = [f for f in migration_files if "__init__" not in f][-1]
        revision_id = os.path.basename(latest_file).split('_')[0]
        
        # Stamp the database
        result = subprocess.run(
            ["alembic", "stamp", revision_id],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Database stamped with revision {revision_id}: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, IndexError) as e:
        if isinstance(e, subprocess.CalledProcessError):
            error_msg = e.stderr
        else:
            error_msg = "Failed to extract revision ID from migration files"
        logger.error(f"Failed to stamp database: {error_msg}")
        sys.exit(1)

def create_database_schema():
    """Create the database schema using SQLAlchemy models."""
    logger.info("Creating database schema from models...")
    
    try:
        from app.db.base import Base
        from app.core.database import sync_engine
        
        # Create all tables
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database schema created successfully")
    except Exception as e:
        logger.error(f"Failed to create database schema: {e}")
        sys.exit(1)

def main():
    """Main execution function."""
    logger.info("Starting migration reset process...")
    
    # Ensure we're in the correct directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        # Backup existing migrations
        backup_path = backup_migrations()
        
        # Delete existing migrations
        delete_migrations()
        
        # Create database schema directly
        create_database_schema()
        
        # Create new migration
        create_new_migration()
        
        # Stamp database with the new migration
        stamp_database()
        
        logger.info("Migration reset completed successfully")
        logger.info(f"Previous migrations backed up to {backup_path}")
    except Exception as e:
        logger.error(f"Migration reset failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 