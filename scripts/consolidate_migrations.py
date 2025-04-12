#!/usr/bin/env python3
"""
Script to consolidate and clean up database migrations.

This script will:
1. Back up existing migrations
2. Create a fresh migration history
3. Test migrations on a fresh database
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MIGRATIONS_DIR = Path('backend/alembic/versions')
BACKUP_DIR = Path('backend/alembic/versions_backup')
TEST_DB_URL = 'postgresql://postgres:postgres@localhost:5432/formiq_test'

def backup_migrations():
    """Back up existing migration files."""
    logger.info("Backing up existing migration files...")
    
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'backup_{timestamp}'
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # Copy all migration files except __init__.py
    count = 0
    for file in MIGRATIONS_DIR.glob('*.py'):
        if file.name != '__init__.py':
            shutil.copy2(file, backup_path)
            count += 1
    
    logger.info(f"Backed up {count} migration files to {backup_path}")
    return backup_path

def clean_migrations():
    """Remove all existing migration files except __init__.py."""
    logger.info("Cleaning existing migration files...")
    
    count = 0
    for file in MIGRATIONS_DIR.glob('*.py'):
        if file.name != '__init__.py':
            file.unlink()
            count += 1
    
    logger.info(f"Removed {count} migration files")

def create_fresh_migration():
    """Create a fresh migration from current models."""
    logger.info("Creating fresh migration from current models...")
    
    try:
        result = subprocess.run(
            ['alembic', 'revision', '--autogenerate', '-m', 'consolidated_schema'],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Successfully created fresh migration")
        logger.debug(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create migration: {e.stderr}")
        raise

def test_migration():
    """Test the migration on a fresh test database."""
    logger.info("Testing migration on fresh database...")
    
    try:
        # Set test database URL
        os.environ['DATABASE_URL'] = TEST_DB_URL
        
        # Drop and recreate test database
        subprocess.run(
            ['dropdb', '--if-exists', 'formiq_test'],
            check=True,
            capture_output=True
        )
        subprocess.run(
            ['createdb', 'formiq_test'],
            check=True,
            capture_output=True
        )
        
        # Run migration
        result = subprocess.run(
            ['alembic', 'upgrade', 'head'],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Migration test successful")
        logger.debug(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration test failed: {e.stderr}")
        raise
    finally:
        # Reset database URL
        os.environ.pop('DATABASE_URL', None)

def main():
    """Main function to consolidate migrations."""
    try:
        # Back up existing migrations
        backup_path = backup_migrations()
        
        # Clean existing migrations
        clean_migrations()
        
        # Create fresh migration
        create_fresh_migration()
        
        # Test migration
        test_migration()
        
        logger.info("""
        Migration consolidation complete!
        
        Next steps:
        1. Review the new migration file in alembic/versions/
        2. Test the migration on a staging environment
        3. Apply the migration to production
        
        Backup of old migrations is stored at:
        {}
        """.format(backup_path))
        
    except Exception as e:
        logger.error(f"Migration consolidation failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 