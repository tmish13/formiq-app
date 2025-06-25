#!/usr/bin/env python3
"""
Script to populate exercise configurations with reference pose data.

This script:
1. Finds all existing exercise configurations 
2. Generates reference pose data for supported exercises
3. Updates the exercise configs with the reference pose data
4. Provides a report of what was updated
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.db_deps import get_async_db as get_async_db_session
from app.services.exercise_config_service import ExerciseConfigService
from app.services.reference_pose_service import ReferencePoseService
from app.models.exercise import ExerciseTemplate
from app.models.exercise_config import ExerciseConfig
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReferencePosePopulator:
    """Service to populate exercise configs with reference pose data."""
    
    def __init__(self):
        """Initialize the populator."""
        self.settings = get_settings()
        self.reference_service = ReferencePoseService(self.settings)
        
        # Mapping of exercise names/types to reference pose generators
        self.exercise_mapping = {
            'squat': 'squat',
            'back squat': 'squat', 
            'front squat': 'squat',
            'goblet squat': 'squat',
            'air squat': 'squat',
            'low bar squat': 'squat',
            'high bar squat': 'squat',
            # Add more exercises as reference generators are implemented
        }
        
        self.stats = {
            'total_configs': 0,
            'configs_updated': 0,
            'configs_skipped': 0,
            'configs_failed': 0,
            'errors': []
        }
    
    async def populate_all_reference_poses(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Populate reference pose data for all exercise configurations.
        
        Args:
            force_update: Whether to update configs that already have reference pose data
            
        Returns:
            Dictionary with population statistics
        """
        logger.info("Starting reference pose population process")
        
        async with get_async_db_session() as session:
            try:
                # Create exercise config service instance
                exercise_config_service = ExerciseConfigService(
                    db=session, 
                    settings=self.settings
                )
                
                # Get all active exercise configs with their exercise templates
                stmt = select(ExerciseConfig).options(
                    selectinload(ExerciseConfig.exercise)
                ).where(ExerciseConfig.is_active == True)
                
                result = await session.execute(stmt)
                configs = result.scalars().all()
                
                self.stats['total_configs'] = len(configs)
                logger.info(f"Found {len(configs)} active exercise configurations")
                
                # Process each config
                for config in configs:
                    await self._populate_single_config(
                        session, 
                        exercise_config_service, 
                        config,
                        force_update
                    )
                
                # Commit all changes
                await session.commit()
                
            except Exception as e:
                logger.error(f"Error during population process: {e}", exc_info=True)
                await session.rollback()
                self.stats['errors'].append(f"Global error: {str(e)}")
                raise
        
        # Log final statistics
        self._log_final_stats()
        return self.stats
    
    async def _populate_single_config(
        self, 
        session,
        exercise_config_service: ExerciseConfigService,
        config: ExerciseConfig,
        force_update: bool
    ) -> None:
        """
        Populate reference pose data for a single exercise configuration.
        
        Args:
            session: Database session
            exercise_config_service: Service instance
            config: Exercise configuration to update
            force_update: Whether to update existing reference pose data
        """
        try:
            config_name = config.name
            exercise_name = config.exercise.name if config.exercise else "Unknown"
            
            logger.info(f"Processing config: {config_name} (Exercise: {exercise_name})")
            
            # Check if reference pose data already exists
            if config.reference_pose_data and not force_update:
                logger.info(f"  ⏭️ Skipping - reference pose data already exists")
                self.stats['configs_skipped'] += 1
                return
            
            # Determine the exercise type for reference pose generation
            exercise_type = self._determine_exercise_type(exercise_name)
            
            if not exercise_type:
                logger.warning(f"  ❌ No reference pose generator for exercise: {exercise_name}")
                self.stats['configs_skipped'] += 1
                return
            
            # Generate reference pose data
            logger.info(f"  🎯 Generating reference pose data for: {exercise_type}")
            reference_data = self.reference_service.generate_reference_pose(exercise_type)
            
            if not reference_data:
                logger.error(f"  ❌ Failed to generate reference pose for: {exercise_type}")
                self.stats['configs_failed'] += 1
                self.stats['errors'].append(f"Failed to generate pose for {config_name}")
                return
            
            # Add metadata about the population
            reference_data['population_metadata'] = {
                'populated_at': str(config.updated_at or config.created_at),
                'config_id': str(config.id),
                'exercise_name': exercise_name,
                'auto_generated': True,
                'source': 'reference_pose_populator_script'
            }
            
            # Update the configuration
            config.reference_pose_data = reference_data
            
            # Mark the session as dirty to ensure update
            session.add(config)
            
            logger.info(f"  ✅ Successfully populated reference pose data")
            self.stats['configs_updated'] += 1
            
        except Exception as e:
            logger.error(f"  ❌ Error processing config {config.name}: {e}", exc_info=True)
            self.stats['configs_failed'] += 1
            self.stats['errors'].append(f"Config {config.name}: {str(e)}")
    
    def _determine_exercise_type(self, exercise_name: str) -> str:
        """
        Determine the exercise type for reference pose generation.
        
        Args:
            exercise_name: Name of the exercise
            
        Returns:
            Exercise type string or None if not supported
        """
        exercise_name_lower = exercise_name.lower()
        
        for pattern, exercise_type in self.exercise_mapping.items():
            if pattern in exercise_name_lower:
                return exercise_type
        
        return None
    
    def _log_final_stats(self) -> None:
        """Log the final population statistics."""
        logger.info("\n" + "=" * 60)
        logger.info("🎉 REFERENCE POSE POPULATION COMPLETE")
        logger.info("=" * 60)
        
        logger.info(f"📊 Statistics:")
        logger.info(f"   Total configurations processed: {self.stats['total_configs']}")
        logger.info(f"   Configurations updated: {self.stats['configs_updated']}")
        logger.info(f"   Configurations skipped: {self.stats['configs_skipped']}")
        logger.info(f"   Configurations failed: {self.stats['configs_failed']}")
        
        if self.stats['errors']:
            logger.warning(f"\n⚠️ Errors encountered ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                logger.warning(f"   - {error}")
        
        logger.info("\n🎯 Next Steps:")
        logger.info("1. Verify reference pose data in database")
        logger.info("2. Test API endpoints with populated data")
        logger.info("3. Validate visual overlay functionality")


async def main():
    """Main function to run the reference pose population."""
    print("🚀 Starting Reference Pose Population Script")
    print("=" * 60)
    
    try:
        # Check for command line arguments
        force_update = "--force" in sys.argv
        if force_update:
            print("⚠️ Force update mode: Will overwrite existing reference pose data")
        
        # Create populator and run
        populator = ReferencePosePopulator()
        stats = await populator.populate_all_reference_poses(force_update=force_update)
        
        # Print summary
        success_rate = (stats['configs_updated'] / stats['total_configs'] * 100) if stats['total_configs'] > 0 else 0
        print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        return stats['configs_failed'] == 0  # Return True if no failures
        
    except Exception as e:
        logger.error(f"Script failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)