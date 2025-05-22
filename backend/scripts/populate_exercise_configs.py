#!/usr/bin/env python3
"""
Script to populate the exercise_configs table with default configurations.

This script:
1. Connects to the database
2. Retrieves all exercise templates
3. Creates default configurations for known exercise types

Usage:
    python populate_exercise_configs.py

"""
import os
import sys
import logging
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import get_db
from app.services.exercise_config_service import ExerciseConfigService
from app.core.config import settings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Populate exercise configurations')
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force update of existing configurations'
    )
    return parser.parse_args()

def main():
    """Main function to populate exercise configurations."""
    args = parse_args()
    
    try:
        # Get database session
        logger.info("Connecting to database")
        db = next(get_db())
        
        # Create default configs
        logger.info("Creating default exercise configurations")
        result = ExerciseConfigService.create_default_configs(db)
        
        if result:
            logger.info(f"Created {len(result)} exercise configurations")
            for exercise_type, config_id in result.items():
                logger.info(f"  - {exercise_type}: {config_id}")
        else:
            logger.info("No new configurations created")
        
        logger.info("Done")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
    
    finally:
        logger.info("Closing database connection")
        db.close()

if __name__ == '__main__':
    main() 