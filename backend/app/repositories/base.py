"""Base repository module."""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, Callable
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi.encoders import jsonable_encoder

from app.core.exceptions import AppException, NotFoundException
from app.core.logging import logger
from app.core.config import settings
from app.core.cache import cache_service
from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations and advanced features.
    
    Features:
    - Transaction management with context managers
    - Query optimization with eager loading
    - Soft delete support
    - Bulk operations
    - Advanced filtering and pagination
    - Error handling and logging
    - Caching support with Redis
    """
    
    def __init__(self, db: Session, model: Type[ModelType]):
        """Initialize repository."""
        self.db = db
        self.model = model
        self.cache_namespace = model.__tablename__
        self.cache_ttl = 3600  # 1 hour default TTL

    def _ensure_transaction(self, db: Session) -> None:
        """Ensure we're in a transaction."""
        if not db.in_transaction():
            db.begin()

    def _handle_error(self, error: Exception, operation: str) -> None:
        """Handle database errors with proper logging."""
        logger.error(f"Database error during {operation}", exc_info=error)
        if isinstance(error, SQLAlchemyError):
            raise AppException(
                status_code=500,
                detail=f"Database error during {operation}: {str(error)}"
            )
        raise error

    def _get_cache_key(self, id: UUID) -> str:
        """Generate cache key for an entity."""
        return f"{self.model.__name__}:{id}"

    def _invalidate_cache(self, id: UUID) -> None:
        """Invalidate cache for an entity."""
        cache_service.delete(self.cache_namespace, self._get_cache_key(id))

    def _cache_entity(self, entity: ModelType) -> None:
        """Cache an entity."""
        if entity:
            cache_service.set(
                self.cache_namespace,
                self._get_cache_key(entity.id),
                entity.dict(),
                self.cache_ttl
            )

    def _get_from_cache(self, id: UUID) -> Optional[Dict[str, Any]]:
        """Get entity from cache."""
        return cache_service.get(self.cache_namespace, self._get_cache_key(id))

    def get(self, id: UUID) -> Optional[ModelType]:
        """Get record by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, *, obj_in: dict) -> ModelType:
        """Create record."""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def update(self, *, db_obj: ModelType, obj_in: dict) -> ModelType:
        """Update record."""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, *, id: UUID) -> Optional[ModelType]:
        """Delete record."""
        obj = self.db.query(self.model).get(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
        return obj

    def exists(self, db: Session, id: UUID) -> bool:
        """Check if a record exists."""
        try:
            cache_key = self._get_cache_key(id)
            if cache_service.exists(cache_key):
                return True
            
            return db.query(self.model).filter(self.model.id == id).first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model.__name__}", error=str(e))
            raise AppException(
                status_code=500,
                detail=f"Error checking existence of {self.model.__name__}"
            )

    def count(self, db: Session) -> int:
        """Get total count of records."""
        try:
            return db.query(self.model).count()
        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model.__name__}", error=str(e))
            raise AppException(
                status_code=500,
                detail=f"Error counting {self.model.__name__}"
            )

    def clear_cache(self, id: UUID) -> bool:
        """Clear cache for a specific record."""
        try:
            cache_key = self._get_cache_key(id)
            return cache_service.delete(cache_key)
        except Exception as e:
            logger.error(f"Error clearing cache for {self.model.__name__}", error=str(e))
            return False

    def create_multi(self, db: Session, *, objs_in: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records in a single transaction."""
        try:
            self._ensure_transaction(db)
            db_objs = [self.model(**obj_in) for obj_in in objs_in]
            db.add_all(db_objs)
            db.commit()
            for obj in db_objs:
                db.refresh(obj)
                # Cache each new entity
                self._cache_entity(obj)
            return db_objs
        except Exception as e:
            db.rollback()
            self._handle_error(e, "create_multi")

    def execute_in_transaction(self, db: Session, operation: Callable[[], Any]) -> Any:
        """
        Execute an operation within a transaction.
        
        Args:
            db: Database session
            operation: Callable that performs the database operation
        """
        try:
            self._ensure_transaction(db)
            result = operation()
            db.commit()
            return result
        except Exception as e:
            db.rollback()
            self._handle_error(e, "execute_in_transaction")

    def upsert(self, db: Session, *, obj_in: Dict[str, Any], unique_fields: List[str]) -> ModelType:
        """
        Update if exists, create if not (upsert operation).
        
        Args:
            db: Database session
            obj_in: Object data
            unique_fields: Fields to check for existence
        """
        try:
            self._ensure_transaction(db)
            filters = {field: obj_in[field] for field in unique_fields if field in obj_in}
            instance = db.query(self.model).filter_by(**filters).first()
            
            if instance:
                return self.update(db, db_obj=instance, obj_in=obj_in)
            return self.create(db, obj_in=obj_in)
        except Exception as e:
            db.rollback()
            self._handle_error(e, "upsert")

    def clear_cache(self) -> None:
        """Clear all cached entities for this repository."""
        cache_service.clear_namespace(self.cache_namespace) 