"""
Exercise configuration repository for database operations.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.exercise_config import ExerciseConfig
from app.models.exercise import ExerciseTemplate
from app.schemas.exercise_config import ExerciseConfigCreate, ExerciseConfigUpdate


class ExerciseConfigRepository:
    """
    Repository for exercise configuration CRUD operations.
    """

    @staticmethod
    def create(db: Session, config_data: ExerciseConfigCreate) -> ExerciseConfig:
        """
        Create a new exercise configuration.
        
        Args:
            db (Session): Database session
            config_data (ExerciseConfigCreate): Configuration data
            
        Returns:
            ExerciseConfig: Created configuration
        """
        config_dict = config_data.model_dump()
        db_config = ExerciseConfig(**config_dict)
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return db_config

    @staticmethod
    def get_by_id(db: Session, config_id: UUID) -> Optional[ExerciseConfig]:
        """
        Get an exercise configuration by ID.
        
        Args:
            db (Session): Database session
            config_id (UUID): Configuration ID
            
        Returns:
            Optional[ExerciseConfig]: Found configuration or None
        """
        return db.query(ExerciseConfig).filter(ExerciseConfig.id == config_id).first()

    @staticmethod
    def get_with_exercise(db: Session, config_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get an exercise configuration by ID with exercise details.
        
        Args:
            db (Session): Database session
            config_id (UUID): Configuration ID
            
        Returns:
            Optional[Dict[str, Any]]: Configuration with exercise details or None
        """
        result = (
            db.query(ExerciseConfig, ExerciseTemplate.name.label("exercise_name"))
            .join(ExerciseTemplate, ExerciseConfig.exercise_id == ExerciseTemplate.id)
            .filter(ExerciseConfig.id == config_id)
            .first()
        )
        
        if not result:
            return None
            
        config, exercise_name = result
        config_dict = {c.name: getattr(config, c.name) for c in config.__table__.columns}
        config_dict["exercise_name"] = exercise_name
        return config_dict

    @staticmethod
    def get_all(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        exercise_id: Optional[UUID] = None,
        active_only: bool = False
    ) -> List[ExerciseConfig]:
        """
        Get all exercise configurations, optionally filtered.
        
        Args:
            db (Session): Database session
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            exercise_id (Optional[UUID]): Filter by exercise
            active_only (bool): Filter by active status
            
        Returns:
            List[ExerciseConfig]: List of configurations
        """
        query = db.query(ExerciseConfig)
        
        if exercise_id:
            query = query.filter(ExerciseConfig.exercise_id == exercise_id)
        
        if active_only:
            query = query.filter(ExerciseConfig.is_active == True)
            
        return query.order_by(desc(ExerciseConfig.updated_at)).offset(skip).limit(limit).all()

    @staticmethod
    def get_all_with_exercise(
        db: Session, 
        skip: int = 0, 
        limit: int = 100, 
        exercise_id: Optional[UUID] = None,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all exercise configurations with exercise details.
        
        Args:
            db (Session): Database session
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            exercise_id (Optional[UUID]): Filter by exercise
            active_only (bool): Filter by active status
            
        Returns:
            List[Dict[str, Any]]: List of configurations with exercise details
        """
        query = (
            db.query(ExerciseConfig, ExerciseTemplate.name.label("exercise_name"))
            .join(ExerciseTemplate, ExerciseConfig.exercise_id == ExerciseTemplate.id)
        )
        
        if exercise_id:
            query = query.filter(ExerciseConfig.exercise_id == exercise_id)
        
        if active_only:
            query = query.filter(ExerciseConfig.is_active == True)
            
        results = query.order_by(desc(ExerciseConfig.updated_at)).offset(skip).limit(limit).all()
        
        config_list = []
        for config, exercise_name in results:
            config_dict = {c.name: getattr(config, c.name) for c in config.__table__.columns}
            config_dict["exercise_name"] = exercise_name
            config_list.append(config_dict)
            
        return config_list

    @staticmethod
    def get_active_config_for_exercise(db: Session, exercise_id: UUID) -> Optional[ExerciseConfig]:
        """
        Get the active configuration for an exercise.
        
        Args:
            db (Session): Database session
            exercise_id (UUID): Exercise ID
            
        Returns:
            Optional[ExerciseConfig]: Active configuration or None
        """
        return (
            db.query(ExerciseConfig)
            .filter(
                ExerciseConfig.exercise_id == exercise_id,
                ExerciseConfig.is_active == True
            )
            .order_by(desc(ExerciseConfig.version))
            .first()
        )

    @staticmethod
    def update(
        db: Session, 
        config_id: UUID, 
        config_data: ExerciseConfigUpdate
    ) -> Optional[ExerciseConfig]:
        """
        Update an exercise configuration.
        
        Args:
            db (Session): Database session
            config_id (UUID): Configuration ID
            config_data (ExerciseConfigUpdate): Update data
            
        Returns:
            Optional[ExerciseConfig]: Updated configuration or None
        """
        db_config = db.query(ExerciseConfig).filter(ExerciseConfig.id == config_id).first()
        if not db_config:
            return None
            
        update_data = config_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_config, key, value)
            
        db.commit()
        db.refresh(db_config)
        return db_config

    @staticmethod
    def delete(db: Session, config_id: UUID) -> bool:
        """
        Delete an exercise configuration.
        
        Args:
            db (Session): Database session
            config_id (UUID): Configuration ID
            
        Returns:
            bool: Success status
        """
        db_config = db.query(ExerciseConfig).filter(ExerciseConfig.id == config_id).first()
        if not db_config:
            return False
            
        db.delete(db_config)
        db.commit()
        return True

    @staticmethod
    def create_new_version(
        db: Session, 
        exercise_id: UUID, 
        config_data: ExerciseConfigCreate,
        deactivate_previous: bool = True
    ) -> ExerciseConfig:
        """
        Create a new version of an exercise configuration and optionally deactivate previous ones.
        
        Args:
            db (Session): Database session
            exercise_id (UUID): Exercise ID
            config_data (ExerciseConfigCreate): Configuration data
            deactivate_previous (bool): Whether to deactivate previous versions
            
        Returns:
            ExerciseConfig: Created configuration
        """
        if deactivate_previous:
            # Deactivate all previous versions
            db.query(ExerciseConfig).filter(
                ExerciseConfig.exercise_id == exercise_id,
                ExerciseConfig.is_active == True
            ).update({"is_active": False})
            
        # Get the latest version number
        latest_version = db.query(ExerciseConfig).filter(
            ExerciseConfig.exercise_id == exercise_id
        ).order_by(desc(ExerciseConfig.version)).first()
        
        new_version = 1 if not latest_version else latest_version.version + 1
        
        # Create new config with updated version
        config_dict = config_data.model_dump()
        config_dict["version"] = new_version
        config_dict["is_active"] = True
        
        db_config = ExerciseConfig(**config_dict)
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return db_config 