"""Base service module."""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app.core.exceptions import AppException, NotFoundException
from app.core.logging import logger
from app.repositories.base import BaseRepository
from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class for all services."""

    def __init__(self, repository: Type[BaseRepository]):
        """Initialize service with repository."""
        self.repository = repository()

    def get(self, db: Session, id: UUID) -> Optional[ModelType]:
        """Get a record by ID."""
        obj = self.repository.get(db, id)
        if not obj:
            raise NotFoundException(f"{self.repository.model.__name__} not found")
        return obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records."""
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        obj_in_data = jsonable_encoder(obj_in)
        obj_in_data["created_at"] = datetime.utcnow()
        obj_in_data["updated_at"] = datetime.utcnow()
        return self.repository.create(db, obj_in=obj_in_data)

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Update a record."""
        obj_data = jsonable_encoder(db_obj)
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        return self.repository.update(db, db_obj=db_obj, obj_in=update_data)

    def delete(self, db: Session, *, id: UUID) -> ModelType:
        """Delete a record."""
        obj = self.repository.delete(db, id=id)
        if not obj:
            raise NotFoundException(f"{self.repository.model.__name__} not found")
        return obj

    def exists(self, db: Session, id: UUID) -> bool:
        """Check if a record exists."""
        return self.repository.exists(db, id) 