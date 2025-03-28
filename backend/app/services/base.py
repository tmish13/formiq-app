from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from app.core.database import Base
from app.core.logger import logger
from app.core.exceptions import AppException, NotFoundException, ValidationException
from app.core.cache import cache_service

ModelType = TypeVar("ModelType", bound=Base)

class BaseService(Generic[ModelType]):
    """Base service class with common CRUD operations and caching."""
    
    def __init__(self, model: Type[ModelType], cache_prefix: str):
        self.model = model
        self.cache_prefix = cache_prefix
    
    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Get a single record by ID with caching."""
        cache_key = f"{self.cache_prefix}:{id}"
        
        # Try to get from cache first
        cached_data = cache_service.get(cache_key)
        if cached_data:
            return self.model(**cached_data)
        
        try:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
            if db_obj:
                # Cache the result
                cache_service.set(cache_key, db_obj.__dict__, expire=3600)
            return db_obj
        except Exception as e:
            logger.error(f"error_getting_{self.model.__name__.lower()}", error=str(e))
            raise AppException(f"Error getting {self.model.__name__}", "DATABASE_ERROR")
    
    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """Get multiple records with pagination and caching."""
        cache_key = f"{self.cache_prefix}:list:{skip}:{limit}"
        
        # Try to get from cache first
        cached_data = cache_service.get(cache_key)
        if cached_data:
            return [self.model(**item) for item in cached_data]
        
        try:
            db_objs = db.query(self.model).offset(skip).limit(limit).all()
            # Cache the result
            cache_service.set(cache_key, [obj.__dict__ for obj in db_objs], expire=3600)
            return db_objs
        except Exception as e:
            logger.error(f"error_getting_{self.model.__name__.lower()}_list", error=str(e))
            raise AppException(f"Error getting {self.model.__name__} list", "DATABASE_ERROR")
    
    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record with validation and caching."""
        try:
            # Validate input data
            self._validate_create_data(obj_in)
            
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            # Cache the new object
            cache_key = f"{self.cache_prefix}:{db_obj.id}"
            cache_service.set(cache_key, db_obj.__dict__, expire=3600)
            
            # Invalidate list cache
            cache_service.delete(f"{self.cache_prefix}:list:*")
            
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"error_creating_{self.model.__name__.lower()}", error=str(e))
            raise AppException(f"Error creating {self.model.__name__}", "DATABASE_ERROR")
    
    def update(
        self, db: Session, *, db_obj: ModelType, obj_in: Dict[str, Any]
    ) -> ModelType:
        """Update an existing record with validation and caching."""
        try:
            # Validate input data
            self._validate_update_data(obj_in)
            
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            
            # Update cache
            cache_key = f"{self.cache_prefix}:{db_obj.id}"
            cache_service.set(cache_key, db_obj.__dict__, expire=3600)
            
            # Invalidate list cache
            cache_service.delete(f"{self.cache_prefix}:list:*")
            
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"error_updating_{self.model.__name__.lower()}", error=str(e))
            raise AppException(f"Error updating {self.model.__name__}", "DATABASE_ERROR")
    
    def delete(self, db: Session, *, id: int) -> ModelType:
        """Delete a record with cache invalidation."""
        try:
            obj = db.query(self.model).get(id)
            if not obj:
                raise NotFoundException(f"{self.model.__name__} not found")
            
            db.delete(obj)
            db.commit()
            
            # Delete from cache
            cache_service.delete(f"{self.cache_prefix}:{id}")
            
            # Invalidate list cache
            cache_service.delete(f"{self.cache_prefix}:list:*")
            
            return obj
        except Exception as e:
            db.rollback()
            logger.error(f"error_deleting_{self.model.__name__.lower()}", error=str(e))
            raise AppException(f"Error deleting {self.model.__name__}", "DATABASE_ERROR")
    
    def exists(self, db: Session, id: int) -> bool:
        """Check if a record exists."""
        try:
            return db.query(self.model).filter(self.model.id == id).first() is not None
        except Exception as e:
            logger.error(f"error_checking_{self.model.__name__.lower()}_exists", error=str(e))
            raise AppException(f"Error checking {self.model.__name__} existence", "DATABASE_ERROR")
    
    def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """Validate data for creation."""
        # Override in subclasses
        pass
    
    def _validate_update_data(self, data: Dict[str, Any]) -> None:
        """Validate data for update."""
        # Override in subclasses
        pass 