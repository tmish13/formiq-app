"""Base repository implementation with advanced CRUD operations and transaction management."""
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict, Callable
from uuid import UUID
from datetime import datetime
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.exc import SQLAlchemyError
from app.models.base import BaseModel
from app.core.exceptions import DatabaseError, NotFoundException, ValidationError
from app.core.logging import logger
from app.core.cache import cache

ModelType = TypeVar("ModelType", bound=BaseModel)

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
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
        self.cache_namespace = f"{model.__tablename__}"
        self.cache_ttl = 3600  # 1 hour default TTL

    def _ensure_transaction(self, db: Session) -> None:
        """Ensure we're in a transaction."""
        if not db.in_transaction():
            db.begin()

    def _handle_error(self, error: Exception, operation: str) -> None:
        """Handle database errors with proper logging."""
        logger.error(f"Database error during {operation}", exc_info=error)
        if isinstance(error, SQLAlchemyError):
            raise DatabaseError(f"Database error during {operation}: {str(error)}")
        raise error

    def _get_cache_key(self, id: UUID) -> str:
        """Generate cache key for an entity."""
        return str(id)

    def _invalidate_cache(self, id: UUID) -> None:
        """Invalidate cache for an entity."""
        cache.delete(self.cache_namespace, self._get_cache_key(id))

    def _cache_entity(self, entity: ModelType) -> None:
        """Cache an entity."""
        if entity:
            cache.set(
                self.cache_namespace,
                self._get_cache_key(entity.id),
                entity.dict(),
                self.cache_ttl
            )

    def _get_from_cache(self, id: UUID) -> Optional[Dict[str, Any]]:
        """Get entity from cache."""
        return cache.get(self.cache_namespace, self._get_cache_key(id))

    def get(self, db: Session, id: UUID, select_fields: List[str] = None) -> Optional[ModelType]:
        """
        Get a single record by ID with optional field selection and caching.
        
        Args:
            db: Database session
            id: Record UUID
            select_fields: Optional list of fields to select
        """
        try:
            # Try to get from cache first
            cached_data = self._get_from_cache(id)
            if cached_data:
                return self.model(**cached_data)

            query = db.query(self.model)
            if select_fields:
                query = query.with_entities(*[getattr(self.model, field) for field in select_fields])
            
            entity = query.filter(self.model.id == id).first()
            
            # Cache the result if found
            if entity:
                self._cache_entity(entity)
            
            return entity
        except Exception as e:
            self._handle_error(e, "get")

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Dict[str, Any] = None,
        order_by: List[str] = None,
        select_fields: List[str] = None,
        include_relations: List[str] = None,
        use_cache: bool = True
    ) -> List[ModelType]:
        """
        Get multiple records with advanced filtering and eager loading.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value pairs for filtering
            order_by: List of fields to order by (prefix with - for desc)
            select_fields: Optional list of fields to select
            include_relations: Optional list of relationships to eager load
            use_cache: Whether to use caching
        """
        try:
            query = db.query(self.model)

            # Apply field selection if specified
            if select_fields:
                query = query.with_entities(*[getattr(self.model, field) for field in select_fields])

            # Apply eager loading for relationships
            if include_relations:
                for relation in include_relations:
                    query = query.options(selectinload(getattr(self.model, relation)))

            # Apply filters
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        filter_conditions.append(getattr(self.model, key).in_(value))
                    else:
                        filter_conditions.append(getattr(self.model, key) == value)
                query = query.filter(and_(*filter_conditions))

            # Apply ordering
            if order_by:
                for field in order_by:
                    if field.startswith('-'):
                        query = query.order_by(getattr(self.model, field[1:]).desc())
                    else:
                        query = query.order_by(getattr(self.model, field).asc())

            entities = query.offset(skip).limit(limit).all()
            
            # Cache results if enabled
            if use_cache:
                for entity in entities:
                    self._cache_entity(entity)
            
            return entities
        except Exception as e:
            self._handle_error(e, "get_multi")

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record with transaction management."""
        try:
            self._ensure_transaction(db)
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            # Cache the new entity
            self._cache_entity(db_obj)
            
            return db_obj
        except Exception as e:
            db.rollback()
            self._handle_error(e, "create")

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

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Dict[str, Any],
        exclude_fields: List[str] = None
    ) -> ModelType:
        """
        Update an existing record with transaction management.
        
        Args:
            db: Database session
            db_obj: Existing database object
            obj_in: Dictionary of updates
            exclude_fields: Optional list of fields to exclude from update
        """
        try:
            self._ensure_transaction(db)
            exclude_fields = exclude_fields or []
            for field, value in obj_in.items():
                if field not in exclude_fields:
                    setattr(db_obj, field, value)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            # Update cache
            self._cache_entity(db_obj)
            
            return db_obj
        except Exception as e:
            db.rollback()
            self._handle_error(e, "update")

    def delete(self, db: Session, *, id: UUID) -> ModelType:
        """Delete a record with transaction management."""
        try:
            self._ensure_transaction(db)
            obj = db.query(self.model).get(id)
            if not obj:
                raise NotFoundException(f"{self.model.__name__} not found")
            db.delete(obj)
            db.commit()
            
            # Invalidate cache
            self._invalidate_cache(id)
            
            return obj
        except Exception as e:
            db.rollback()
            self._handle_error(e, "delete")

    def count(self, db: Session, *, filters: Dict[str, Any] = None) -> int:
        """Count records with optional filtering."""
        try:
            query = db.query(func.count(self.model.id))
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        filter_conditions.append(getattr(self.model, key).in_(value))
                    else:
                        filter_conditions.append(getattr(self.model, key) == value)
                query = query.filter(and_(*filter_conditions))
            return query.scalar()
        except Exception as e:
            self._handle_error(e, "count")

    def exists(self, db: Session, *, filters: Dict[str, Any]) -> bool:
        """Check if records exist with given filters."""
        return self.count(db, filters=filters) > 0

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

    def clear_cache(self) -> None:
        """Clear all cached entities for this repository."""
        cache.clear_namespace(self.cache_namespace) 