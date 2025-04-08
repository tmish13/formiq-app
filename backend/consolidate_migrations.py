#!/usr/bin/env python
"""
Consolidate database migrations script.

This script:
1. Deletes conflicting migration files
2. Creates a new single migration file
3. Updates the database to use the new migration
"""
import os
import sys
import glob
import shutil
import subprocess
from pathlib import Path
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path constants
BACKEND_DIR = Path(__file__).parent
ALEMBIC_DIR = BACKEND_DIR / "alembic"
VERSIONS_DIR = ALEMBIC_DIR / "versions"
BACKUP_DIR = ALEMBIC_DIR / "versions_backup"

def backup_migrations():
    """
    Back up existing migration files to a timestamped directory.
    
    Returns:
        Path: Path to the backup directory
    """
    logger.info("Backing up existing migration files...")
    
    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Create timestamped backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    backup_path.mkdir()
    
    # Copy all migration files to backup directory
    count = 0
    for file_path in VERSIONS_DIR.glob("*.py"):
        if file_path.name != "__init__.py":
            shutil.copy(file_path, backup_path)
            count += 1
    
    logger.info(f"Backed up {count} migration files to {backup_path}")
    return backup_path

def delete_conflicting_migrations():
    """
    Delete conflicting migration files with the same revision ID.
    
    Returns:
        int: Number of files deleted
    """
    logger.info("Deleting conflicting migration files...")
    
    # Find files with the same revision IDs
    revision_files = {}
    for file_path in VERSIONS_DIR.glob("*.py"):
        if file_path.name == "__init__.py":
            continue
            
        revision_id = file_path.name.split("_")[0]
        if revision_id in revision_files:
            revision_files[revision_id].append(file_path)
        else:
            revision_files[revision_id] = [file_path]
    
    # Delete duplicate revisions, keeping only the most recent file
    deleted_count = 0
    for revision_id, files in revision_files.items():
        if len(files) > 1:
            # Sort by modification time, newest first
            sorted_files = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
            
            # Keep the newest file, delete the rest
            for file_to_delete in sorted_files[1:]:
                logger.info(f"Deleting duplicate migration: {file_to_delete.name}")
                file_to_delete.unlink()
                deleted_count += 1
    
    logger.info(f"Deleted {deleted_count} conflicting migration files")
    return deleted_count

def renumber_migrations():
    """
    Renumber migrations to ensure sequential ordering.
    
    Returns:
        dict: Mapping of old revision IDs to new revision IDs
    """
    logger.info("Renumbering migration files...")
    
    # Get all migration files except __init__.py
    migration_files = [f for f in VERSIONS_DIR.glob("*.py") if f.name != "__init__.py"]
    
    # Sort by modification time
    migration_files.sort(key=lambda x: os.path.getmtime(x))
    
    # Create revision mapping
    revision_map = {}
    
    for i, file_path in enumerate(migration_files, start=1):
        # Parse current revision ID
        old_name = file_path.name
        old_revision = old_name.split("_")[0]
        rest_of_name = "_".join(old_name.split("_")[1:])
        
        # Generate new revision ID
        new_revision = f"{i:03d}"
        new_name = f"{new_revision}_{rest_of_name}"
        
        # Rename file
        new_path = file_path.with_name(new_name)
        shutil.move(file_path, new_path)
        
        # Update content to reflect new revision ID
        with open(new_path, "r") as f:
            content = f.read()
        
        # Replace revision and dependencies
        content = content.replace(f'revision = "{old_revision}"', f'revision = "{new_revision}"')
        
        # Update revision dependencies if needed
        if i > 1:
            prev_revision = f"{i-1:03d}"
            content = content.replace('down_revision = None', f'down_revision = "{prev_revision}"')
            for old_dep, new_dep in revision_map.items():
                content = content.replace(f'down_revision = "{old_dep}"', f'down_revision = "{new_dep}"')
        
        with open(new_path, "w") as f:
            f.write(content)
        
        revision_map[old_revision] = new_revision
        logger.info(f"Renamed migration: {old_name} -> {new_name}")
    
    logger.info(f"Renumbered {len(migration_files)} migration files")
    return revision_map

def rebase_database():
    """
    Rebase the database to use the new migration history.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Rebasing database to new migration history...")
    
    try:
        # Find the latest migration revision
        migration_files = [f for f in VERSIONS_DIR.glob("*.py") if f.name != "__init__.py"]
        if not migration_files:
            logger.error("No migration files found")
            return False
            
        # Sort by revision number
        migration_files.sort(key=lambda x: x.name)
        latest_file = migration_files[-1]
        latest_revision = latest_file.name.split("_")[0]
        
        # Stamp the database with the latest revision
        result = subprocess.run(
            ["alembic", "stamp", latest_revision],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"Database rebased to revision {latest_revision}")
        logger.info(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to rebase database: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error rebasing database: {str(e)}")
        return False

def main():
    """Main execution function."""
    logger.info("Starting migration consolidation...")
    
    # Make sure we're in the backend directory
    os.chdir(BACKEND_DIR)
    
    try:
        # Backup existing migrations
        backup_path = backup_migrations()
        
        # Delete conflicting migrations
        delete_conflicting_migrations()
        
        # Renumber migrations
        revision_map = renumber_migrations()
        
        # Rebase database
        if rebase_database():
            logger.info("Migration consolidation completed successfully")
            logger.info(f"Previous migrations backed up to {backup_path}")
        else:
            logger.error("Failed to rebase database")
            logger.info("You may need to manually update the database")
        
    except Exception as e:
        logger.error(f"Migration consolidation failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 