from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.decl_api import DeclarativeBase
from app.core.config import Settings
from app.models.base import BaseModel
from app.core.exceptions import ServiceError

ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseService(Generic[ModelType]):
    """Base service with repository pattern and error handling."""
    
    def __init__(self, db: Session, settings: Settings, model: Type[ModelType]):
        self.db = db
        self.settings = settings
        self.model = model

    def get(self, id: Any) -> Optional[ModelType]:
        """Get a single record by ID."""
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            raise ServiceError(f"Failed to get {self.model.__name__}: {str(e)}")

    def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records with pagination."""
        try:
            return self.db.query(self.model).offset(skip).limit(limit).all()
        except Exception as e:
            raise ServiceError(f"Failed to get {self.model.__name__} list: {str(e)}")

    def create(self, *, obj_in: dict) -> ModelType:
        """Create a new record."""
        try:
            db_obj = self.model(**obj_in)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            self.db.rollback()
            raise ServiceError(f"Failed to create {self.model.__name__}: {str(e)}")

    def update(self, *, db_obj: ModelType, obj_in: dict) -> ModelType:
        """Update an existing record."""
        try:
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except Exception as e:
            self.db.rollback()
            raise ServiceError(f"Failed to update {self.model.__name__}: {str(e)}")

    def delete(self, *, id: int) -> ModelType:
        """Delete a record by ID."""
        try:
            obj = self.db.query(self.model).get(id)
            if not obj:
                raise ServiceError(f"{self.model.__name__} not found")
            self.db.delete(obj)
            self.db.commit()
            return obj
        except Exception as e:
            self.db.rollback()
            raise ServiceError(f"Failed to delete {self.model.__name__}: {str(e)}") 