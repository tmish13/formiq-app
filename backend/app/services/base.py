"""Base service implementation with dependency injection and transaction management."""
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from uuid import UUID
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.exceptions import (
    ValidationError,
    NotFoundException,
    AuthorizationError,
    DatabaseError
)
from app.core.logging import logger
from app.repositories.base import BaseRepository
from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
FilterSchemaType = TypeVar("FilterSchemaType")

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, FilterSchemaType]):
    """
    Base service class with common functionality.
    
    Features:
    - Dependency injection
    - Transaction management
    - Error handling
    - CRUD operations
    - Event handling
    - Validation
    """
    
    def __init__(
        self,
        repository: Type[BaseRepository],
        model: Type[ModelType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        filter_schema: Type[FilterSchemaType]
    ):
        """
        Initialize service with dependencies.
        
        Args:
            repository: Repository class for data access
            model: Model class for type checking
            create_schema: Schema for creation validation
            update_schema: Schema for update validation
            filter_schema: Schema for filter validation
        """
        self.repository = repository()
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.filter_schema = filter_schema

    async def _validate_create(self, data: Dict[str, Any]) -> CreateSchemaType:
        """Validate creation data."""
        try:
            return self.create_schema(**data)
        except Exception as e:
            logger.error("Validation error in create", exc_info=e)
            raise ValidationError(str(e))

    async def _validate_update(self, data: Dict[str, Any]) -> UpdateSchemaType:
        """Validate update data."""
        try:
            return self.update_schema(**data)
        except Exception as e:
            logger.error("Validation error in update", exc_info=e)
            raise ValidationError(str(e))

    async def _validate_filters(self, filters: Dict[str, Any]) -> FilterSchemaType:
        """Validate filter parameters."""
        try:
            return self.filter_schema(**filters)
        except Exception as e:
            logger.error("Validation error in filters", exc_info=e)
            raise ValidationError(str(e))

    async def _pre_create(self, db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-create hook for additional processing."""
        return data

    async def _post_create(self, db: Session, created: ModelType) -> ModelType:
        """Post-create hook for additional processing."""
        return created

    async def _pre_update(self, db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-update hook for additional processing."""
        return data

    async def _post_update(self, db: Session, updated: ModelType) -> ModelType:
        """Post-update hook for additional processing."""
        return updated

    async def _pre_delete(self, db: Session, id: UUID) -> None:
        """Pre-delete hook for additional processing."""
        pass

    async def _post_delete(self, db: Session, deleted: ModelType) -> None:
        """Post-delete hook for additional processing."""
        pass

    async def create(
        self,
        db: Session = Depends(get_db),
        *,
        data: Dict[str, Any]
    ) -> ModelType:
        """
        Create a new record with validation.
        
        Args:
            db: Database session
            data: Creation data
        """
        try:
            # Validate input
            validated_data = await self._validate_create(data)
            
            # Pre-create processing
            processed_data = await self._pre_create(db, validated_data.dict())
            
            # Create record
            created = self.repository.create(db, obj_in=processed_data)
            
            # Post-create processing
            return await self._post_create(db, created)
        except Exception as e:
            logger.error("Error in create service", exc_info=e)
            raise

    async def update(
        self,
        db: Session = Depends(get_db),
        *,
        id: UUID,
        data: Dict[str, Any]
    ) -> ModelType:
        """
        Update an existing record with validation.
        
        Args:
            db: Database session
            id: Record ID
            data: Update data
        """
        try:
            # Check existence
            current = self.repository.get(db, id)
            if not current:
                raise NotFoundException(f"{self.model.__name__} not found")
            
            # Validate input
            validated_data = await self._validate_update(data)
            
            # Pre-update processing
            processed_data = await self._pre_update(db, validated_data.dict())
            
            # Update record
            updated = self.repository.update(db, db_obj=current, obj_in=processed_data)
            
            # Post-update processing
            return await self._post_update(db, updated)
        except Exception as e:
            logger.error("Error in update service", exc_info=e)
            raise

    async def delete(
        self,
        db: Session = Depends(get_db),
        *,
        id: UUID
    ) -> ModelType:
        """
        Delete a record.
        
        Args:
            db: Database session
            id: Record ID
        """
        try:
            # Check existence
            current = self.repository.get(db, id)
            if not current:
                raise NotFoundException(f"{self.model.__name__} not found")
            
            # Pre-delete processing
            await self._pre_delete(db, id)
            
            # Delete record
            deleted = self.repository.delete(db, id=id)
            
            # Post-delete processing
            await self._post_delete(db, deleted)
            
            return deleted
        except Exception as e:
            logger.error("Error in delete service", exc_info=e)
            raise

    async def get(
        self,
        db: Session = Depends(get_db),
        *,
        id: UUID
    ) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            db: Database session
            id: Record ID
        """
        try:
            entity = self.repository.get(db, id)
            if not entity:
                raise NotFoundException(f"{self.model.__name__} not found")
            return entity
        except Exception as e:
            logger.error("Error in get service", exc_info=e)
            raise

    async def get_multi(
        self,
        db: Session = Depends(get_db),
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get multiple records with filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filter parameters
        """
        try:
            # Validate filters if provided
            if filters:
                validated_filters = await self._validate_filters(filters)
                filters = validated_filters.dict(exclude_unset=True)
            
            return self.repository.get_multi(
                db,
                skip=skip,
                limit=limit,
                filters=filters
            )
        except Exception as e:
            logger.error("Error in get_multi service", exc_info=e)
            raise

    async def count(
        self,
        db: Session = Depends(get_db),
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with filtering.
        
        Args:
            db: Database session
            filters: Optional filter parameters
        """
        try:
            # Validate filters if provided
            if filters:
                validated_filters = await self._validate_filters(filters)
                filters = validated_filters.dict(exclude_unset=True)
            
            return self.repository.count(db, filters=filters)
        except Exception as e:
            logger.error("Error in count service", exc_info=e)
            raise 